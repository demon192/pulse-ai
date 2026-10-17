"""Manager action-item lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.core.clock import utc_now
from app.models.enums import (
    ActionStatus,
    ActionType,
    NotificationType,
    Priority,
    RequestStatus,
)
from app.notifications.service import NotificationService, attention_key, make_dedup_key
from app.repositories.database import Database
from app.rules.dependencies import DependencyGraph
from app.rules.prioritization import rank_actions
from app.schemas.analysis import ActionPriority
from app.schemas.domain import ActionItem, DecisionRecord, User
from app.services import audit, authz

# Action types a manager is expected to decide on rather than merely track.
NOTIFY_ON_CREATE = {
    ActionType.APPROVAL: NotificationType.APPROVAL_REQUESTED,
    ActionType.BLOCKER: NotificationType.BLOCKER_REPORTED,
    ActionType.QUESTION: NotificationType.SUPPORT_REQUEST_CREATED,
    ActionType.SUPPORT_REQUEST: NotificationType.SUPPORT_REQUEST_CREATED,
    ActionType.ONE_ON_ONE: NotificationType.SUPPORT_REQUEST_CREATED,
    ActionType.HANDOVER_APPROVAL: NotificationType.HANDOVER_REVIEW_REQUIRED,
}


def new_action_id() -> str:
    return f"act-{uuid.uuid4().hex[:12]}"


def create_action(
    database: Database,
    notifications: NotificationService,
    *,
    action_type: ActionType,
    title: str,
    description: str,
    owner_id: str,
    created_by: str,
    project_id: str | None = None,
    task_id: str | None = None,
    source_request_id: str | None = None,
    source_handover_id: str | None = None,
    priority: Priority = Priority.MEDIUM,
    due_date: datetime | None = None,
    suggested_action: str | None = None,
    notify: bool = True,
    now: datetime | None = None,
) -> ActionItem:
    """Create a tracked action item and, when relevant, notify its owner."""
    now = now or utc_now()
    action = ActionItem(
        id=new_action_id(),
        project_id=project_id,
        task_id=task_id,
        source_request_id=source_request_id,
        source_handover_id=source_handover_id,
        type=action_type,
        title=title,
        description=description,
        owner_id=owner_id,
        created_by=created_by,
        created_at=now,
        updated_at=now,
        due_date=due_date,
        status=ActionStatus.OPEN,
        priority=priority,
    )
    database.actions.save(action)

    if notify and action_type in NOTIFY_ON_CREATE:
        notifications.emit(
            recipient_id=owner_id,
            notification_type=NOTIFY_ON_CREATE[action_type],
            title=title,
            message=description,
            reason=f"A {action_type.value.replace('_', ' ')} is waiting on you.",
            suggested_action=suggested_action or "Open the action and record a decision.",
            priority=priority,
            related_entity_type="action_item",
            related_entity_id=action.id,
            dedup_key=attention_key("action_item", action.id, owner_id),
            allow_escalation=True,
            now=now,
        )
    return action


def update_action(
    database: Database,
    notifications: NotificationService,
    *,
    action: ActionItem,
    actor: User,
    status: ActionStatus | None = None,
    priority: Priority | None = None,
    owner_id: str | None = None,
    due_date: datetime | None = None,
    resolution_notes: str | None = None,
) -> ActionItem:
    """Apply a manager edit, mirroring status back to the source request."""
    if not authz.can_resolve_action(database, actor, action):
        raise authz.AuthorizationError("You are not authorized to change this action.")

    updates: dict[str, object] = {"updated_at": utc_now()}
    if status is not None:
        updates["status"] = status
    if priority is not None:
        updates["priority"] = priority
    if due_date is not None:
        updates["due_date"] = due_date
    if resolution_notes is not None:
        updates["resolution_notes"] = resolution_notes

    if owner_id is not None and owner_id != action.owner_id:
        # Delegation is only allowed to a user who can act on the project.
        delegate = database.users.require(owner_id)
        if action.project_id and not authz.can_access_project(
            database, delegate, action.project_id
        ):
            raise authz.AuthorizationError(
                f"{delegate.name} is not authorized on project {action.project_id}."
            )
        updates["owner_id"] = owner_id

    updated = action.model_copy(update=updates)
    database.actions.save(updated)
    audit.record(
        database,
        actor_id=actor.id,
        action="action.update",
        entity_type="action_item",
        entity_id=action.id,
        details={
            "status": updated.status.value,
            "owner_id": updated.owner_id,
            "priority": updated.priority.value,
        },
    )

    if owner_id is not None and owner_id != action.owner_id:
        notifications.emit(
            recipient_id=owner_id,
            notification_type=NotificationType.APPROVAL_REQUESTED,
            title=f"Delegated to you: {updated.title}",
            message=updated.description,
            reason=f"{actor.name} delegated this action to you.",
            suggested_action="Review the action and record a decision.",
            priority=updated.priority,
            related_entity_type="action_item",
            related_entity_id=updated.id,
            dedup_key=attention_key("action_item", updated.id, owner_id),
        )

    if not updated.is_open:
        _propagate_resolution(database, notifications, action=updated, actor=actor)
    return updated


def resolve_action(
    database: Database,
    notifications: NotificationService,
    *,
    action: ActionItem,
    actor: User,
    resolution_notes: str,
    decision: str | None = None,
    decision_rationale: str | None = None,
) -> ActionItem:
    """Resolve an action, optionally recording a durable decision."""
    if not authz.can_resolve_action(database, actor, action):
        raise authz.AuthorizationError("You are not authorized to resolve this action.")

    decision_record_id: str | None = None
    if decision and action.project_id:
        record = DecisionRecord(
            id=f"dec-{uuid.uuid4().hex[:12]}",
            project_id=action.project_id,
            task_id=action.task_id,
            title=action.title,
            decision=decision,
            rationale=decision_rationale,
            decided_by=actor.id,
            decided_at=utc_now(),
        )
        database.decisions.save(record)
        decision_record_id = record.id

    resolved = action.model_copy(
        update={
            "status": ActionStatus.RESOLVED,
            "resolution_notes": resolution_notes,
            "decision_record_id": decision_record_id,
            "updated_at": utc_now(),
        }
    )
    database.actions.save(resolved)
    audit.record(
        database,
        actor_id=actor.id,
        action="action.resolve",
        entity_type="action_item",
        entity_id=action.id,
        details={"decision_record_id": decision_record_id or ""},
    )
    _propagate_resolution(database, notifications, action=resolved, actor=actor)
    return resolved


def _propagate_resolution(
    database: Database,
    notifications: NotificationService,
    *,
    action: ActionItem,
    actor: User,
) -> None:
    """Close out notifications and tell the requesting engineer."""
    notifications.resolve_by_entity("action_item", action.id)

    if not action.source_request_id:
        return
    request = database.requests.get(action.source_request_id)
    if request is None or not request.is_open:
        return

    # Mirror the manager's decision onto the engineer's request so the engineer
    # sees the outcome without having to chase it.
    updated = request.model_copy(
        update={
            "status": RequestStatus.RESOLVED
            if action.status is ActionStatus.RESOLVED
            else RequestStatus.CANCELLED,
            "resolution_notes": action.resolution_notes,
            "updated_at": utc_now(),
        }
    )
    database.requests.save(updated)
    notifications.resolve_by_entity("support_request", request.id)
    notifications.emit(
        recipient_id=request.engineer_id,
        notification_type=NotificationType.REQUEST_RESOLVED,
        title=f"Resolved: {request.title}",
        message=action.resolution_notes or "The manager recorded a decision.",
        reason=f"{actor.name} resolved the action tracking your request.",
        suggested_action="Open the request to read the decision.",
        priority=request.priority,
        related_entity_type="support_request",
        related_entity_id=request.id,
        dedup_key=make_dedup_key(
            event="request_resolved",
            entity_type="support_request",
            entity_id=request.id,
            recipient_id=request.engineer_id,
        ),
    )


def prioritised_inbox(
    database: Database,
    *,
    actions: list[ActionItem],
    graph: DependencyGraph,
    milestones: list,
    now: datetime | None = None,
) -> list[ActionPriority]:
    open_actions = [action for action in actions if action.is_open]
    return rank_actions(open_actions, graph=graph, milestones=milestones, now=now)
