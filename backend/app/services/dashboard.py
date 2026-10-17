"""Dashboard assembly for both roles.

No model call happens here. The manager's daily briefing is served from the
persisted AI cache if it is fresh, and generated only when explicitly requested.
"""

from __future__ import annotations

from app.ai.service import AIService
from app.core.clock import days_until
from app.models.enums import (
    ActionType,
    ApprovalStatus,
    HandoverStatus,
    RequestStatus,
    TaskStatus,
)
from app.notifications.service import NotificationService
from app.schemas.analysis import ProjectHealthReport
from app.schemas.api import (
    AIEnvelope,
    AIMeta,
    EngineerDashboard,
    EngineerSummary,
    ManagerDashboard,
    ManagerSummary,
)
from app.services import views
from app.services.actions import prioritised_inbox
from app.services.context import WorkContext

UPCOMING_DEADLINE_DAYS = 7.0
MAX_INBOX_ITEMS = 25


def _name_maps(context: WorkContext) -> tuple[dict[str, str], dict[str, str]]:
    user_names = {user.id: user.name for user in context.users_by_id.values()}
    project_names = {
        project.id: project.name for project in context.db.projects.list_all()
    }
    return user_names, project_names


def build_manager_dashboard(
    context: WorkContext,
    notifications: NotificationService,
    ai_service: AIService,
) -> ManagerDashboard:
    user_names, project_names = _name_maps(context)
    reports: list[ProjectHealthReport] = context.health_reports

    inbox_priorities = prioritised_inbox(
        context.db,
        actions=[action for action in context.actions if action.owner_id == context.user.id],
        graph=context.graph,
        milestones=context.milestones,
        now=context.now,
    )
    action_index = {action.id: action for action in context.actions}
    inbox = [
        views.action_inbox_item(
            action_index[priority.action_id],
            priority_detail=priority,
            database=context.db,
            user_names=user_names,
            project_names=project_names,
        )
        for priority in inbox_priorities[:MAX_INBOX_ITEMS]
        if priority.action_id in action_index
    ]

    open_requests = [
        views.request_view(
            request,
            database=context.db,
            user_names=user_names,
            project_names=project_names,
        )
        for request in sorted(
            (item for item in context.requests if item.is_open),
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]

    upcoming_milestones = sorted(
        (
            milestone
            for report in reports
            for milestone in report.milestones
            if milestone.days_remaining >= 0
        ),
        key=lambda milestone: milestone.days_remaining,
    )[:6]

    top_risks = sorted(
        (risk for report in reports for risk in report.risks),
        key=lambda risk: -risk.severity,
    )[:8]

    handovers_awaiting = [
        views.handover_view(handover, database=context.db, viewer=context.user, now=context.now)
        for handover in context.db.handovers.list_all()
        if handover.manager_approval_status is ApprovalStatus.PENDING
        and handover.handover_status
        in (HandoverStatus.PENDING_MANAGER_REVIEW, HandoverStatus.DECLINED)
        and any(
            project_id in context.project_ids for project_id in handover.affected_project_ids
        )
    ]

    tasks_needing_attention = sum(
        1
        for task in context.tasks
        if task.is_open
        and (
            task.status is TaskStatus.BLOCKED
            or (task.due_date is not None and (days_until(task.due_date, now=context.now) or 0) < 0)
        )
    )
    overdue_actions = sum(
        1
        for action in context.actions
        if action.is_open
        and action.owner_id == context.user.id
        and action.due_date is not None
        and (days_until(action.due_date, now=context.now) or 0) < 0
    )

    summary = ManagerSummary(
        projects_total=len(reports),
        projects_at_risk=sum(1 for report in reports if report.health_score < 75),
        tasks_needing_attention=tasks_needing_attention,
        pending_approvals=sum(
            1
            for action in context.actions
            if action.is_open
            and action.owner_id == context.user.id
            and action.type in (ActionType.APPROVAL, ActionType.HANDOVER_APPROVAL)
        ),
        open_support_requests=sum(1 for request in context.requests if request.is_open),
        overdue_actions=overdue_actions,
        upcoming_milestones=len(upcoming_milestones),
        coverage_gaps=sum(1 for gap in context.coverage_gaps() if not gap.has_approved_handover),
        unread_notifications=notifications.unread_count(context.user.id),
    )

    return ManagerDashboard(
        generated_at=context.now,
        summary=summary,
        project_health=reports,
        action_inbox=inbox,
        open_requests=open_requests,
        upcoming_milestones=upcoming_milestones,
        top_risks=top_risks,
        coverage=context.coverage_gaps(),
        handovers_awaiting_review=handovers_awaiting,
        recent_activity=notifications.for_recipient(context.user.id)[:10],
        daily_briefing=_cached_briefing(context, ai_service, reports),
    )


def _cached_briefing(
    context: WorkContext, ai_service: AIService, reports: list[ProjectHealthReport]
) -> AIEnvelope | None:
    """Return a stored briefing for the most at-risk project, if one is cached."""
    if not reports:
        return None
    subject = reports[0].project_id
    cached = context.db.ai_cache.get(f"project_briefing:{subject}")
    if cached is None:
        return None
    return AIEnvelope(
        meta=AIMeta(
            source="cache",
            model=None,
            generated_at=cached.generated_at,
            degraded=cached.generated_by != "gemini",
            notes=[f"Cached briefing for project {subject}."],
        ),
        data=cached.payload,
    )


def build_engineer_dashboard(
    context: WorkContext, notifications: NotificationService
) -> EngineerDashboard:
    user_names, project_names = _name_maps(context)
    my_tasks = [
        task for task in context.db.tasks.list_all() if task.owner_id == context.user.id
    ]
    my_task_views = [
        views.task_view(
            task,
            graph=context.graph,
            user_names=user_names,
            project_names=project_names,
            now=context.now,
        )
        for task in sorted(
            my_tasks,
            key=lambda task: (task.status is TaskStatus.COMPLETED, task.due_date or task.created_at),
        )
    ]
    blockers = [view for view in my_task_views if view.task.status is TaskStatus.BLOCKED]
    upcoming = [
        view
        for view in my_task_views
        if view.task.is_open
        and view.days_until_due is not None
        and view.days_until_due <= UPCOMING_DEADLINE_DAYS
    ]

    my_requests = [
        views.request_view(
            request,
            database=context.db,
            user_names=user_names,
            project_names=project_names,
        )
        for request in sorted(
            context.db.requests.find(lambda item: item.engineer_id == context.user.id),
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]
    awaiting = [
        view
        for view in my_requests
        if view.request.status in (RequestStatus.OPEN, RequestStatus.ACKNOWLEDGED)
    ]

    my_handovers = [
        views.handover_view(handover, database=context.db, viewer=context.user, now=context.now)
        for handover in context.db.handovers.find(
            lambda item: item.unavailable_user_id == context.user.id
        )
    ]
    assigned = [
        views.handover_view(handover, database=context.db, viewer=context.user, now=context.now)
        for handover in context.db.handovers.find(
            lambda item: item.selected_backup_id == context.user.id
        )
    ]

    summary = EngineerSummary(
        open_tasks=sum(1 for task in my_tasks if task.is_open),
        blocked_tasks=len(blockers),
        overdue_tasks=sum(1 for view in my_task_views if view.is_overdue),
        open_requests=sum(1 for view in my_requests if view.request.is_open),
        awaiting_response=len(awaiting),
        unread_notifications=notifications.unread_count(context.user.id),
    )

    return EngineerDashboard(
        generated_at=context.now,
        summary=summary,
        my_tasks=my_task_views,
        my_blockers=blockers,
        my_requests=my_requests,
        awaiting_response=awaiting,
        upcoming_deadlines=upcoming,
        availability_status=context.user.availability_status,
        my_handovers=my_handovers,
        assigned_to_me=assigned,
        recent_notifications=notifications.for_recipient(context.user.id)[:10],
    )
