"""Event sweep that turns current state into notifications.

Run on dashboard load. Every emission is keyed so a sweep is idempotent: the
same condition never produces a second notification, and a worsening condition
escalates an existing one rather than adding noise.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import days_until, utc_now
from app.models.enums import NotificationType, Priority, TaskStatus
from app.notifications.service import NotificationService, attention_key
from app.repositories.database import Database
from app.rules.dependencies import DependencyGraph
from app.schemas.domain import Project

# An action is "due soon" inside this window.
ACTION_DUE_SOON_DAYS = 2.0


def run_sweep(
    database: Database,
    notifications: NotificationService,
    *,
    project_ids: set[str],
    now: datetime | None = None,
) -> int:
    """Emit notifications for the current state of the given projects."""
    now = now or utc_now()
    created = 0
    tasks = [task for task in database.tasks.list_all() if task.project_id in project_ids]
    graph = DependencyGraph(database.tasks.list_all())
    projects = {
        project.id: project
        for project in database.projects.list_all()
        if project.id in project_ids
    }

    created += _overdue_tasks(database, notifications, tasks=tasks, projects=projects, now=now)
    created += _blocked_dependencies(
        database, notifications, tasks=tasks, graph=graph, projects=projects, now=now
    )
    created += _actions_due_soon(database, notifications, project_ids=project_ids, now=now)
    return created


def _overdue_tasks(
    database: Database,
    notifications: NotificationService,
    *,
    tasks: list,
    projects: dict[str, Project],
    now: datetime,
) -> int:
    created = 0
    for task in tasks:
        if not task.is_open or task.due_date is None:
            continue
        overdue_days = -(days_until(task.due_date, now=now) or 0.0)
        if overdue_days <= 0:
            continue

        # Severity grows with time, which drives escalation rather than repeats.
        priority = (
            Priority.CRITICAL
            if overdue_days >= 5
            else Priority.HIGH
            if overdue_days >= 2
            else Priority.MEDIUM
        )
        downstream = graph_downstream_count(task, tasks)
        message = (
            f"'{task.title}' passed its due date {overdue_days:.0f} day(s) ago"
            + (f" and {downstream} task(s) depend on it." if downstream else ".")
        )
        recipients = {task.owner_id} if task.owner_id else set()
        project = projects.get(task.project_id)
        if project:
            recipients.add(project.manager_id)

        for recipient_id in recipients:
            if recipient_id is None:
                continue
            emitted = notifications.emit(
                recipient_id=recipient_id,
                notification_type=NotificationType.TASK_OVERDUE,
                title=f"Overdue task: {task.title}",
                message=message,
                reason="The recorded due date has passed and the task is still open.",
                suggested_action="Agree a revised date or escalate the blocker.",
                priority=priority,
                related_entity_type="task",
                related_entity_id=task.id,
                dedup_key=attention_key("task", task.id, recipient_id),
                allow_escalation=True,
                now=now,
            )
            if emitted is not None:
                created += 1
    return created


def graph_downstream_count(task, tasks: list) -> int:
    return sum(1 for other in tasks if task.id in other.dependency_ids and other.is_open)


def _blocked_dependencies(
    database: Database,
    notifications: NotificationService,
    *,
    tasks: list,
    graph: DependencyGraph,
    projects: dict[str, Project],
    now: datetime,
) -> int:
    """A blocked task that other work waits on is a delivery event, not a status."""
    created = 0
    for task in tasks:
        if task.status is not TaskStatus.BLOCKED:
            continue
        downstream = graph.downstream(task.id)
        if not downstream:
            continue
        project = projects.get(task.project_id)
        if project is None:
            continue
        critical = sum(
            1
            for item in downstream
            if item.priority in (Priority.HIGH, Priority.CRITICAL)
        )
        emitted = notifications.emit(
            recipient_id=project.manager_id,
            notification_type=NotificationType.DEPENDENCY_BLOCKED,
            title=f"Blocked dependency: {task.title}",
            message=(
                f"'{task.title}' is blocked and {len(downstream)} task(s) depend on it"
                + (f", {critical} of them high or critical priority." if critical else ".")
            ),
            reason=task.blocked_reason or "The task is recorded as blocked.",
            suggested_action="Clear the blocker or re-sequence the dependent work.",
            priority=Priority.HIGH if critical else Priority.MEDIUM,
            related_entity_type="task",
            related_entity_id=task.id,
            dedup_key=attention_key("task", task.id, project.manager_id),
            allow_escalation=True,
            now=now,
        )
        if emitted is not None:
            created += 1
    return created


def _actions_due_soon(
    database: Database,
    notifications: NotificationService,
    *,
    project_ids: set[str],
    now: datetime,
) -> int:
    created = 0
    for action in database.actions.list_all():
        if not action.is_open or action.due_date is None:
            continue
        if action.project_id is not None and action.project_id not in project_ids:
            continue
        remaining = days_until(action.due_date, now=now) or 0.0
        if remaining > ACTION_DUE_SOON_DAYS:
            continue
        overdue = remaining < 0
        emitted = notifications.emit(
            recipient_id=action.owner_id,
            notification_type=NotificationType.ACTION_DUE_SOON,
            title=("Overdue action: " if overdue else "Action due soon: ") + action.title,
            message=(
                f"'{action.title}' was due {abs(remaining):.1f} day(s) ago."
                if overdue
                else f"'{action.title}' is due in {remaining:.1f} day(s)."
            ),
            reason="The action has a deadline inside the attention window.",
            suggested_action="Resolve or delegate the action.",
            priority=Priority.CRITICAL if overdue else Priority.HIGH,
            related_entity_type="action_item",
            related_entity_id=action.id,
            dedup_key=attention_key("action_item", action.id, action.owner_id),
            allow_escalation=True,
            now=now,
        )
        if emitted is not None:
            created += 1
    return created
