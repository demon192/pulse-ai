"""Manager action inbox."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import Context, CurrentUser, Db, Notifications
from app.models.enums import ActionStatus, Priority, Role
from app.rules.prioritization import score_action
from app.schemas.api import (
    ActionCreate,
    ActionInboxItem,
    ActionPatch,
    ActionResolve,
)
from app.services import actions as action_service
from app.services import authz, views

router = APIRouter(prefix="/actions", tags=["action inbox"])


def _item(context: Context, action) -> ActionInboxItem:
    return views.action_inbox_item(
        action,
        priority_detail=score_action(
            action, graph=context.graph, milestones=context.milestones, now=context.now
        ),
        database=context.db,
        user_names={user.id: user.name for user in context.db.users.list_all()},
        project_names={p.id: p.name for p in context.db.projects.list_all()},
    )


@router.get("", response_model=list[ActionInboxItem])
def list_actions(
    context: Context,
    status_filter: ActionStatus | None = Query(default=None, alias="status"),
    project_id: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    bucket: str | None = Query(default=None),
    include_closed: bool = Query(default=False),
) -> list[ActionInboxItem]:
    items = context.actions
    if status_filter is not None:
        items = [item for item in items if item.status is status_filter]
    elif not include_closed:
        items = [item for item in items if item.is_open]
    if project_id is not None:
        items = [item for item in items if item.project_id == project_id]
    if owner_id is not None:
        items = [item for item in items if item.owner_id == owner_id]
    if priority is not None:
        items = [item for item in items if item.priority is priority]

    scored = [_item(context, action) for action in items]
    if bucket is not None:
        scored = [item for item in scored if item.priority_detail.bucket == bucket]
    scored.sort(key=lambda item: -item.priority_detail.score)
    return scored


@router.post("", response_model=ActionInboxItem, status_code=status.HTTP_201_CREATED)
def create_action(
    payload: ActionCreate,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> ActionInboxItem:
    """Create a follow-up the manager wants tracked."""
    if user.role is not Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a manager can create an action item.",
        )
    if payload.project_id is not None:
        authz.require_project_access(database, user, payload.project_id)
    database.users.require(payload.owner_id)

    action = action_service.create_action(
        database,
        notifications,
        action_type=payload.type,
        title=payload.title,
        description=payload.description,
        owner_id=payload.owner_id,
        created_by=user.id,
        project_id=payload.project_id,
        task_id=payload.task_id,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    return _item(context, action)


@router.get("/{action_id}", response_model=ActionInboxItem)
def get_action(action_id: str, context: Context) -> ActionInboxItem:
    action = context.db.actions.require(action_id)
    if not authz.can_view_action(context.db, context.user, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this action.",
        )
    return _item(context, action)


@router.patch("/{action_id}", response_model=ActionInboxItem)
def patch_action(
    action_id: str,
    payload: ActionPatch,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> ActionInboxItem:
    action = database.actions.require(action_id)
    updated = action_service.update_action(
        database,
        notifications,
        action=action,
        actor=user,
        status=payload.status,
        priority=payload.priority,
        owner_id=payload.owner_id,
        due_date=payload.due_date,
        resolution_notes=payload.resolution_notes,
    )
    return _item(context, updated)


@router.post("/{action_id}/resolve", response_model=ActionInboxItem)
def resolve_action(
    action_id: str,
    payload: ActionResolve,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> ActionInboxItem:
    action = database.actions.require(action_id)
    updated = action_service.resolve_action(
        database,
        notifications,
        action=action,
        actor=user,
        resolution_notes=payload.resolution_notes,
        decision=payload.decision,
        decision_rationale=payload.decision_rationale,
    )
    if updated.project_id:
        database.ai_cache.delete(f"project_briefing:{updated.project_id}")
    return _item(context, updated)
