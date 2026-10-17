"""Support request lifecycle.

A request is the engineer's record. It stays visible until it is resolved or
cancelled, independently of whether anyone has read the notification about it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.core.clock import utc_now
from app.models.enums import (
    ActionStatus,
    ActionType,
    NotificationType,
    Priority,
    RequestCategory,
    RequestStatus,
    Role,
)
from app.notifications.service import NotificationService, make_dedup_key
from app.repositories.database import Database
from app.schemas.domain import ActionItem, RequestResponse, SupportRequest, User
from app.services import actions as action_service
from app.services import audit, authz

# Which action type tracks each request category. Progress updates are recorded
# but deliberately do not create work for the manager.
CATEGORY_TO_ACTION_TYPE: dict[RequestCategory, ActionType | None] = {
    RequestCategory.APPROVAL: ActionType.APPROVAL,
    RequestCategory.DECISION: ActionType.QUESTION,
    RequestCategory.BLOCKER: ActionType.BLOCKER,
    RequestCategory.ONE_ON_ONE: ActionType.ONE_ON_ONE,
    RequestCategory.OTHER: ActionType.SUPPORT_REQUEST,
    RequestCategory.PROGRESS_UPDATE: None,
}

# Status transitions the API will accept, per role.
ENGINEER_TRANSITIONS = {RequestStatus.CANCELLED}
MANAGER_TRANSITIONS = {
    RequestStatus.ACKNOWLEDGED,
    RequestStatus.IN_PROGRESS,
    RequestStatus.RESOLVED,
    RequestStatus.CANCELLED,
}


def new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def _default_owner(database: Database, project_id: str) -> str | None:
    project = database.projects.get(project_id)
    return project.manager_id if project else None


def create_request(
    database: Database,
    notifications: NotificationService,
    *,
    engineer: User,
    project_id: str,
    category: RequestCategory,
    title: str,
    description: str,
    task_id: str | None = None,
    priority: Priority = Priority.MEDIUM,
    due_date: datetime | None = None,
    now: datetime | None = None,
) -> tuple[SupportRequest, ActionItem | None]:
    """Create a request and the action item that tracks it for the manager."""
    now = now or utc_now()
    authz.require_project_access(database, engineer, project_id)

    if task_id is not None:
        task = database.tasks.require(task_id)
        if task.project_id != project_id:
            raise ValueError("The task does not belong to the given project.")

    owner_id = _default_owner(database, project_id)
    if owner_id is None:
        raise ValueError("The project has no manager to route this request to.")

    request = SupportRequest(
        id=new_request_id(),
        engineer_id=engineer.id,
        project_id=project_id,
        task_id=task_id,
        category=category,
        title=title,
        description=description,
        priority=priority,
        status=RequestStatus.OPEN,
        assigned_owner_id=owner_id,
        created_at=now,
        updated_at=now,
        due_date=due_date,
        is_demo_data=False,
    )
    database.requests.save(request)

    # Keep the task's back-reference in sync so the handover brief can find it.
    if task_id is not None:
        task = database.tasks.require(task_id)
        if request.id not in task.related_request_ids:
            database.tasks.save(
                task.model_copy(
                    update={
                        "related_request_ids": [*task.related_request_ids, request.id],
                        "updated_at": now,
                    }
                )
            )

    action = None
    action_type = CATEGORY_TO_ACTION_TYPE.get(category)
    if action_type is not None:
        action = action_service.create_action(
            database,
            notifications,
            action_type=action_type,
            title=title,
            description=description,
            owner_id=owner_id,
            created_by=engineer.id,
            project_id=project_id,
            task_id=task_id,
            source_request_id=request.id,
            priority=priority,
            due_date=due_date,
            suggested_action=_suggested_action(category),
            now=now,
        )

    audit.record(
        database,
        actor_id=engineer.id,
        action="request.create",
        entity_type="support_request",
        entity_id=request.id,
        details={"category": category.value, "action_item_id": action.id if action else ""},
    )
    return request, action


def _suggested_action(category: RequestCategory) -> str:
    return {
        RequestCategory.APPROVAL: "Review the request and approve, reject or delegate it.",
        RequestCategory.DECISION: "Record the decision so the work can continue.",
        RequestCategory.BLOCKER: "Confirm the blocker and decide who clears it.",
        RequestCategory.ONE_ON_ONE: "Offer a time or delegate the conversation.",
        RequestCategory.OTHER: "Acknowledge the request and set an owner.",
        RequestCategory.PROGRESS_UPDATE: "No action needed.",
    }[category]


def respond(
    database: Database,
    notifications: NotificationService,
    *,
    request: SupportRequest,
    actor: User,
    body: str,
    status: RequestStatus | None = None,
) -> SupportRequest:
    """Record a manager response and notify the engineer."""
    if not authz.can_respond_to_request(database, actor, request):
        raise authz.AuthorizationError(
            "You are not authorized to respond to this request."
        )

    now = utc_now()
    next_status = status or (
        RequestStatus.ACKNOWLEDGED
        if request.status is RequestStatus.OPEN
        else request.status
    )
    updated = request.model_copy(
        update={
            "responses": [
                *request.responses,
                RequestResponse(author_id=actor.id, body=body, created_at=now),
            ],
            "status": next_status,
            "updated_at": now,
        }
    )
    database.requests.save(updated)

    # Acknowledge the tracking action so the inbox reflects reality.
    for action in _linked_actions(database, request.id):
        if action.status is ActionStatus.OPEN:
            database.actions.save(
                action.model_copy(
                    update={"status": ActionStatus.ACKNOWLEDGED, "updated_at": now}
                )
            )

    notifications.emit(
        recipient_id=request.engineer_id,
        notification_type=NotificationType.REQUEST_RESPONDED,
        title=f"Response on: {request.title}",
        message=body,
        reason=f"{actor.name} responded to your request.",
        suggested_action="Open the request to read the response.",
        priority=request.priority,
        related_entity_type="support_request",
        related_entity_id=request.id,
        dedup_key=make_dedup_key(
            event="request_responded",
            entity_type="support_request",
            entity_id=request.id,
            recipient_id=request.engineer_id,
            discriminator=str(len(updated.responses)),
        ),
        now=now,
    )
    audit.record(
        database,
        actor_id=actor.id,
        action="request.respond",
        entity_type="support_request",
        entity_id=request.id,
        details={"status": updated.status.value},
    )
    return updated


def update_request(
    database: Database,
    notifications: NotificationService,
    *,
    request: SupportRequest,
    actor: User,
    status: RequestStatus | None = None,
    priority: Priority | None = None,
    assigned_owner_id: str | None = None,
    resolution_notes: str | None = None,
    engineer_context_note: str | None = None,
) -> SupportRequest:
    """Apply an allowed change, enforcing who may make which transition."""
    authz.require_request_access(database, actor, request)
    now = utc_now()
    updates: dict[str, object] = {"updated_at": now}

    if status is not None and status is not request.status:
        allowed = (
            MANAGER_TRANSITIONS
            if authz.can_respond_to_request(database, actor, request)
            else ENGINEER_TRANSITIONS
            if request.engineer_id == actor.id
            else set()
        )
        if status not in allowed:
            raise authz.AuthorizationError(
                f"You are not authorized to move this request to '{status.value}'."
            )
        updates["status"] = status

    if priority is not None:
        if not authz.can_respond_to_request(database, actor, request):
            raise authz.AuthorizationError("Only the request owner can change priority.")
        updates["priority"] = priority

    if assigned_owner_id is not None:
        if actor.role is not Role.MANAGER:
            raise authz.AuthorizationError("Only a manager can reassign a request.")
        delegate = database.users.require(assigned_owner_id)
        if not authz.can_access_project(database, delegate, request.project_id):
            raise authz.AuthorizationError(
                f"{delegate.name} is not authorized on this project."
            )
        updates["assigned_owner_id"] = assigned_owner_id

    if resolution_notes is not None:
        if not authz.can_respond_to_request(database, actor, request):
            raise authz.AuthorizationError("Only the request owner can add resolution notes.")
        updates["resolution_notes"] = resolution_notes

    if engineer_context_note is not None:
        # The engineer may always add context or correct an AI summary.
        if request.engineer_id != actor.id:
            raise authz.AuthorizationError(
                "Only the requesting engineer can add a context note."
            )
        updates["engineer_context_note"] = engineer_context_note

    updated = request.model_copy(update=updates)
    database.requests.save(updated)

    if request.is_open and not updated.is_open:
        _close_linked_actions(database, notifications, request=updated, actor=actor)
        notifications.resolve_by_entity("support_request", updated.id)
        notifications.emit(
            recipient_id=updated.engineer_id,
            notification_type=NotificationType.REQUEST_RESOLVED,
            title=f"{updated.status.value.title()}: {updated.title}",
            message=updated.resolution_notes or "The request was closed.",
            reason=f"{actor.name} closed your request.",
            suggested_action="Open the request to read the outcome.",
            priority=updated.priority,
            related_entity_type="support_request",
            related_entity_id=updated.id,
            dedup_key=make_dedup_key(
                event="request_closed",
                entity_type="support_request",
                entity_id=updated.id,
                recipient_id=updated.engineer_id,
            ),
            now=now,
        )

    audit.record(
        database,
        actor_id=actor.id,
        action="request.update",
        entity_type="support_request",
        entity_id=request.id,
        details={"status": updated.status.value},
    )
    return updated


def _linked_actions(database: Database, request_id: str) -> list[ActionItem]:
    return database.actions.find(
        lambda action: action.source_request_id == request_id
    )


def _close_linked_actions(
    database: Database,
    notifications: NotificationService,
    *,
    request: SupportRequest,
    actor: User,
) -> None:
    terminal = (
        ActionStatus.RESOLVED
        if request.status is RequestStatus.RESOLVED
        else ActionStatus.CANCELLED
    )
    for action in _linked_actions(database, request.id):
        if action.is_open:
            database.actions.save(
                action.model_copy(
                    update={
                        "status": terminal,
                        "resolution_notes": request.resolution_notes,
                        "updated_at": utc_now(),
                    }
                )
            )
            notifications.resolve_by_entity("action_item", action.id)


def open_requests_for_engineer(database: Database, engineer_id: str) -> list[SupportRequest]:
    requests = database.requests.find(
        lambda item: item.engineer_id == engineer_id and item.is_open
    )
    requests.sort(key=lambda item: item.created_at, reverse=True)
    return requests
