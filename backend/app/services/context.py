"""Per-request working set.

Loading the authorised slice of the workspace once, building the dependency
graph once, and reusing both keeps the dashboards cheap and keeps every rule
evaluating against a single consistent snapshot.
"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property

from app.core.clock import days_until, utc_now
from app.models.enums import ApprovalStatus, AvailabilityStatus, Priority, TaskStatus
from app.repositories.database import Database
from app.rules.dependencies import DependencyGraph
from app.rules.risk import build_project_health
from app.schemas.analysis import CoverageGap, ProjectHealthReport
from app.schemas.domain import (
    ActionItem,
    Milestone,
    Project,
    SupportRequest,
    Task,
    User,
)
from app.services import authz


class WorkContext:
    """The authorised view of the workspace for one user at one moment."""

    def __init__(self, database: Database, user: User, now: datetime | None = None) -> None:
        self.db = database
        self.user = user
        self.now = now or utc_now()

    # -- scope ----------------------------------------------------------
    @cached_property
    def project_ids(self) -> set[str]:
        return authz.accessible_project_ids(self.db, self.user)

    @cached_property
    def projects(self) -> list[Project]:
        return authz.accessible_projects(self.db, self.user)

    @cached_property
    def tasks(self) -> list[Task]:
        return [
            task
            for task in self.db.tasks.list_all()
            if task.project_id in self.project_ids
        ]

    @cached_property
    def graph(self) -> DependencyGraph:
        # Built over every task so cross-project dependencies still resolve.
        return DependencyGraph(self.db.tasks.list_all())

    @cached_property
    def milestones(self) -> list[Milestone]:
        return [
            milestone
            for milestone in self.db.milestones.list_all()
            if milestone.project_id in self.project_ids
        ]

    @cached_property
    def requests(self) -> list[SupportRequest]:
        return authz.visible_requests(self.db, self.user)

    @cached_property
    def actions(self) -> list[ActionItem]:
        return authz.visible_actions(self.db, self.user)

    @cached_property
    def users_by_id(self) -> dict[str, User]:
        return {user.id: user for user in self.db.users.list_all()}

    def user_name(self, user_id: str | None) -> str:
        if not user_id:
            return "Unassigned"
        user = self.users_by_id.get(user_id)
        return user.name if user else user_id

    # -- derived views ----------------------------------------------------
    def tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self.tasks if task.project_id == project_id]

    def project_health(self, project_id: str) -> ProjectHealthReport:
        project = self.db.projects.require(project_id)
        return build_project_health(
            project=project,
            tasks=self.tasks_for_project(project_id),
            graph=self.graph,
            milestones=self.milestones,
            requests=self.requests,
            actions=self.actions,
            now=self.now,
        )

    @cached_property
    def health_reports(self) -> list[ProjectHealthReport]:
        reports = [self.project_health(project.id) for project in self.projects]
        reports.sort(key=lambda report: report.health_score)
        return reports

    def open_tasks_for_user(self, user_id: str) -> list[Task]:
        return [
            task
            for task in self.db.tasks.list_all()
            if task.owner_id == user_id and task.is_open
        ]

    def overdue_tasks(self) -> list[Task]:
        return [
            task
            for task in self.tasks
            if task.is_open
            and task.due_date is not None
            and (days_until(task.due_date, now=self.now) or 0.0) < 0
        ]

    def blocked_tasks(self) -> list[Task]:
        return [task for task in self.tasks if task.status is TaskStatus.BLOCKED]

    # -- coverage ---------------------------------------------------------
    def coverage_gaps(self) -> list[CoverageGap]:
        """Unavailable engineers whose open work has no approved handover."""
        gaps: list[CoverageGap] = []
        handovers = self.db.handovers.list_all()
        for user in self.db.users.list_all():
            if user.availability_status in (
                AvailabilityStatus.AVAILABLE,
                AvailabilityStatus.LIMITED,
            ):
                continue
            open_tasks = [
                task
                for task in self.open_tasks_for_user(user.id)
                if task.project_id in self.project_ids
            ]
            if not open_tasks:
                continue
            matching = [
                handover
                for handover in handovers
                if handover.unavailable_user_id == user.id
            ]
            approved = next(
                (
                    handover
                    for handover in matching
                    if handover.manager_approval_status is ApprovalStatus.APPROVED
                ),
                None,
            )
            critical = any(
                task.priority in (Priority.HIGH, Priority.CRITICAL) for task in open_tasks
            )
            gaps.append(
                CoverageGap(
                    user_id=user.id,
                    user_name=user.name,
                    availability_status=user.availability_status.value,
                    open_task_count=len(open_tasks),
                    has_approved_handover=approved is not None,
                    handover_id=(approved or (matching[0] if matching else None)).id
                    if (approved or matching)
                    else None,
                    priority=Priority.HIGH if critical and approved is None else Priority.MEDIUM,
                )
            )
        gaps.sort(key=lambda gap: (gap.has_approved_handover, -gap.open_task_count))
        return gaps
