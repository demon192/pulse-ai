"""Projects and tasks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import Context, CurrentUser, Db, Notifications
from app.core.clock import utc_now
from app.models.enums import NotificationType, Priority, TaskStatus
from app.notifications.service import attention_key
from app.schemas.api import (
    AIEnvelope,
    AIMeta,
    ProjectDetail,
    ProjectSummary,
    TaskDetail,
    TaskPatch,
    TaskView,
)
from app.schemas.domain import TaskUpdate
from app.services import authz, views

router = APIRouter(tags=["projects"])


def _name_maps(context: Context) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {user.id: user.name for user in context.db.users.list_all()},
        {project.id: project.name for project in context.db.projects.list_all()},
    )


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects(context: Context) -> list[ProjectSummary]:
    user_names, _ = _name_maps(context)
    return [
        ProjectSummary(
            project=project,
            manager_name=user_names.get(project.manager_id, project.manager_id),
            health=context.project_health(project.id),
        )
        for project in context.projects
    ]


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, context: Context) -> ProjectDetail:
    authz.require_project_access(context.db, context.user, project_id)
    project = context.db.projects.require(project_id)
    user_names, project_names = _name_maps(context)

    tasks = [
        views.task_view(
            task,
            graph=context.graph,
            user_names=user_names,
            project_names=project_names,
            now=context.now,
        )
        for task in sorted(
            context.tasks_for_project(project_id),
            key=lambda task: (task.status is TaskStatus.COMPLETED, task.due_date or task.created_at),
        )
    ]
    milestones = sorted(
        (m for m in context.milestones if m.project_id == project_id),
        key=lambda m: m.target_date,
    )
    team = [
        views.to_public(context.db.users.require(member_id))
        for member_id in project.team_member_ids
        if context.db.users.get(member_id)
    ]
    cached = context.db.ai_cache.get(f"project_briefing:{project_id}")
    briefing = (
        AIEnvelope(
            meta=AIMeta(
                source="cache",
                generated_at=cached.generated_at,
                degraded=cached.generated_by != "gemini",
                notes=["Served from the persisted summary cache."],
            ),
            data=cached.payload,
        )
        if cached
        else None
    )

    return ProjectDetail(
        project=project,
        manager_name=user_names.get(project.manager_id, project.manager_id),
        health=context.project_health(project_id),
        milestones=milestones,
        tasks=tasks,
        team=team,
        documents=context.db.documents.find(lambda doc: doc.project_id == project_id),
        decisions=sorted(
            context.db.decisions.find(lambda item: item.project_id == project_id),
            key=lambda item: item.decided_at,
            reverse=True,
        ),
        cached_briefing=briefing,
    )


@router.get("/projects/{project_id}/tasks", response_model=list[TaskView])
def list_project_tasks(project_id: str, context: Context) -> list[TaskView]:
    authz.require_project_access(context.db, context.user, project_id)
    user_names, project_names = _name_maps(context)
    return [
        views.task_view(
            task,
            graph=context.graph,
            user_names=user_names,
            project_names=project_names,
            now=context.now,
        )
        for task in context.tasks_for_project(project_id)
    ]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, context: Context) -> TaskDetail:
    task = context.db.tasks.require(task_id)
    if not authz.can_view_task(context.db, context.user, task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this task.",
        )
    user_names, project_names = _name_maps(context)
    updates = sorted(
        context.db.task_updates.find(lambda item: item.task_id == task_id),
        key=lambda item: item.created_at,
        reverse=True,
    )
    requests = [
        request
        for request in context.db.requests.find(lambda item: item.task_id == task_id)
        if authz.can_view_request(context.db, context.user, request)
    ]
    return TaskDetail(
        task=views.task_view(
            task,
            graph=context.graph,
            user_names=user_names,
            project_names=project_names,
            now=context.now,
        ),
        updates=updates,
        requests=requests,
        documents=context.db.documents.find(
            lambda doc: task_id in doc.task_ids or doc.id in task.related_document_ids
        ),
        dependencies=context.graph.direct_dependencies(task_id),
        dependents=context.graph.direct_dependents(task_id),
    )


@router.patch("/tasks/{task_id}", response_model=TaskDetail)
def patch_task(
    task_id: str,
    payload: TaskPatch,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> TaskDetail:
    task = database.tasks.require(task_id)
    if not authz.can_edit_task(database, user, task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the task owner or the project manager can update this task.",
        )

    now = utc_now()
    updates: dict[str, object] = {"updated_at": now}
    for field in ("status", "next_step", "remaining_effort", "priority"):
        value = getattr(payload, field)
        if value is not None:
            updates[field] = value
    if payload.blocked_reason is not None:
        updates["blocked_reason"] = payload.blocked_reason

    became_blocked = (
        payload.status is TaskStatus.BLOCKED and task.status is not TaskStatus.BLOCKED
    )
    updated = task.model_copy(update=updates)
    database.tasks.save(updated)

    if payload.progress_note:
        database.task_updates.save(
            TaskUpdate(
                id=f"upd-{uuid.uuid4().hex[:12]}",
                task_id=task_id,
                author_id=user.id,
                body=payload.progress_note,
                created_at=now,
                is_demo_data=False,
            )
        )

    if became_blocked:
        project = database.projects.require(task.project_id)
        notifications.emit(
            recipient_id=project.manager_id,
            notification_type=NotificationType.BLOCKER_REPORTED,
            title=f"Blocker reported: {updated.title}",
            message=updated.blocked_reason or "No reason recorded.",
            reason=f"{user.name} marked the task as blocked.",
            suggested_action="Review the blocker and decide who clears it.",
            priority=Priority.HIGH
            if updated.priority in (Priority.HIGH, Priority.CRITICAL)
            else Priority.MEDIUM,
            related_entity_type="task",
            related_entity_id=task_id,
            dedup_key=attention_key("task", task_id, project.manager_id),
            now=now,
        )

    # The project briefing is now stale.
    database.ai_cache.delete(f"project_briefing:{task.project_id}")
    return get_task(task_id, context)
