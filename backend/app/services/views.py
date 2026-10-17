"""Projections from domain records to API view models."""

from __future__ import annotations

from datetime import datetime

from app.core.clock import days_until
from app.models.enums import ApprovalStatus
from app.repositories.database import Database
from app.rules.dependencies import DependencyGraph
from app.rules.risk import summarise_milestone
from app.schemas.api import (
    ActionInboxItem,
    HandoverView,
    SupportRequestView,
    TaskView,
)
from app.schemas.domain import (
    ActionItem,
    HandoverRecord,
    SupportRequest,
    Task,
    User,
    UserPublic,
)
from app.services import audit, authz


def to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=user.name,
        role=user.role,
        title=user.title,
        availability_status=user.availability_status,
    )


def task_view(
    task: Task,
    *,
    graph: DependencyGraph,
    user_names: dict[str, str],
    project_names: dict[str, str],
    now: datetime,
) -> TaskView:
    remaining = days_until(task.due_date, now=now)
    return TaskView(
        task=task,
        owner_name=user_names.get(task.owner_id or "", "Unassigned"),
        project_name=project_names.get(task.project_id, task.project_id),
        blocking_dependencies=[item.title for item in graph.blocking_dependencies(task.id)],
        downstream_task_ids=[item.id for item in graph.downstream(task.id)],
        is_overdue=bool(task.is_open and remaining is not None and remaining < 0),
        days_until_due=round(remaining, 2) if remaining is not None else None,
    )


def request_view(
    request: SupportRequest,
    *,
    database: Database,
    user_names: dict[str, str],
    project_names: dict[str, str],
) -> SupportRequestView:
    task = database.tasks.get(request.task_id) if request.task_id else None
    action = database.actions.find_one(
        lambda item: item.source_request_id == request.id
    )
    return SupportRequestView(
        request=request,
        engineer_name=user_names.get(request.engineer_id, request.engineer_id),
        project_name=project_names.get(request.project_id, request.project_id),
        task_title=task.title if task else None,
        owner_name=user_names.get(request.assigned_owner_id or "") or None,
        action_item_id=action.id if action else None,
    )


def action_inbox_item(
    action: ActionItem,
    *,
    priority_detail,
    database: Database,
    user_names: dict[str, str],
    project_names: dict[str, str],
) -> ActionInboxItem:
    task = database.tasks.get(action.task_id) if action.task_id else None
    source_request = (
        database.requests.get(action.source_request_id)
        if action.source_request_id
        else None
    )
    return ActionInboxItem(
        action=action,
        priority_detail=priority_detail,
        project_name=project_names.get(action.project_id or "") or None,
        task_title=task.title if task else None,
        requester_name=user_names.get(action.created_by, action.created_by),
        source_request=source_request,
        source_handover_id=action.source_handover_id,
    )


def handover_view(
    handover: HandoverRecord,
    *,
    database: Database,
    viewer: User,
    now: datetime,
    include_audit: bool = False,
) -> HandoverView:
    user_names = {user.id: user.name for user in database.users.list_all()}
    tasks = [
        task
        for task in (database.tasks.get(task_id) for task_id in handover.affected_task_ids)
        if task is not None
    ]
    downstream = [
        task
        for task in (
            database.tasks.get(task_id) for task_id in handover.downstream_task_ids
        )
        if task is not None
    ]
    task_index = {task.id: task for task in database.tasks.list_all()}
    milestones = [
        summarise_milestone(milestone, task_index, now)
        for milestone in (
            database.milestones.get(milestone_id)
            for milestone_id in handover.affected_milestone_ids
        )
        if milestone is not None
    ]
    pending_actions = [
        action
        for action in (
            database.actions.get(action_id)
            for action_id in handover.pending_approval_action_ids
        )
        if action is not None
    ]
    documents = [
        document
        for document in (
            database.documents.get(document_id)
            for document_id in handover.relevant_document_ids
        )
        if document is not None
    ]
    return HandoverView(
        handover=handover,
        unavailable_user_name=user_names.get(
            handover.unavailable_user_id, handover.unavailable_user_id
        ),
        selected_backup_name=user_names.get(handover.selected_backup_id or "") or None,
        approved_by_name=user_names.get(handover.approved_by or "") or None,
        affected_tasks=tasks,
        downstream_tasks=downstream,
        affected_milestones=milestones,
        pending_actions=pending_actions,
        documents=documents,
        audit_trail=audit.for_entity(database, "handover", handover.id)
        if include_audit
        else [],
        can_approve=authz.can_approve_handover(database, viewer, handover),
        can_accept=(
            handover.selected_backup_id == viewer.id
            and handover.manager_approval_status is ApprovalStatus.APPROVED
            and handover.backup_accepted_at is None
        ),
    )
