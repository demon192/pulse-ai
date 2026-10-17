"""Authorization rules, enforced in the backend.

The frontend hides what a role cannot use, but every decision below is also
made server-side on each request. Hiding a button is not access control.
"""

from __future__ import annotations

from app.models.enums import Role
from app.repositories.database import Database
from app.schemas.domain import (
    ActionItem,
    HandoverRecord,
    Project,
    SupportRequest,
    Task,
    User,
)


class AuthorizationError(PermissionError):
    """Raised when the caller may not see or change a record."""

    def __init__(self, detail: str = "You are not authorized to access this record.") -> None:
        super().__init__(detail)
        self.detail = detail


def accessible_project_ids(database: Database, user: User) -> set[str]:
    """Projects this user may read.

    Managers get the projects they manage plus anything explicitly granted.
    Engineers get only what is explicitly granted.
    """
    granted = set(user.authorized_project_ids)
    if user.role is Role.MANAGER:
        granted.update(
            project.id
            for project in database.projects.list_all()
            if project.manager_id == user.id
        )
    return granted


def can_access_project(database: Database, user: User, project_id: str) -> bool:
    return project_id in accessible_project_ids(database, user)


def require_project_access(database: Database, user: User, project_id: str) -> None:
    if not can_access_project(database, user, project_id):
        raise AuthorizationError("You are not authorized to access this project.")


def accessible_projects(database: Database, user: User) -> list[Project]:
    allowed = accessible_project_ids(database, user)
    projects = [project for project in database.projects.list_all() if project.id in allowed]
    projects.sort(key=lambda project: project.name)
    return projects


def is_manager_of_project(database: Database, user: User, project_id: str) -> bool:
    if user.role is not Role.MANAGER:
        return False
    project = database.projects.get(project_id)
    return project is not None and project.manager_id == user.id


def can_view_request(database: Database, user: User, request: SupportRequest) -> bool:
    """A support request is visible to its author, its assigned owner, and the
    manager of its project. Other engineers never see it."""
    if request.engineer_id == user.id:
        return True
    if request.assigned_owner_id == user.id:
        return True
    if user.role is Role.MANAGER:
        return can_access_project(database, user, request.project_id)
    return False


def require_request_access(database: Database, user: User, request: SupportRequest) -> None:
    if not can_view_request(database, user, request):
        raise AuthorizationError("You are not authorized to access this request.")


def can_respond_to_request(database: Database, user: User, request: SupportRequest) -> bool:
    """Only the assigned owner or an authorised manager may respond."""
    if request.assigned_owner_id == user.id:
        return True
    return user.role is Role.MANAGER and can_access_project(
        database, user, request.project_id
    )


def can_view_action(database: Database, user: User, action: ActionItem) -> bool:
    if action.owner_id == user.id or action.created_by == user.id:
        return True
    if action.source_request_id:
        request = database.requests.get(action.source_request_id)
        if request is not None and request.engineer_id == user.id:
            return True
    if user.role is Role.MANAGER and action.project_id:
        return can_access_project(database, user, action.project_id)
    return user.role is Role.MANAGER and action.project_id is None and action.owner_id == user.id


def can_resolve_action(database: Database, user: User, action: ActionItem) -> bool:
    """Only the action's owner may resolve it, and only a manager may delegate."""
    return action.owner_id == user.id or (
        user.role is Role.MANAGER
        and action.project_id is not None
        and is_manager_of_project(database, user, action.project_id)
    )


def can_view_task(database: Database, user: User, task: Task) -> bool:
    return can_access_project(database, user, task.project_id)


def can_edit_task(database: Database, user: User, task: Task) -> bool:
    """Task owners update their own work; managers update anything they own."""
    if task.owner_id == user.id:
        return True
    return is_manager_of_project(database, user, task.project_id)


def can_view_handover(database: Database, user: User, handover: HandoverRecord) -> bool:
    if user.id in {
        handover.unavailable_user_id,
        handover.requested_by,
        handover.selected_backup_id,
    }:
        return True
    if user.role is Role.MANAGER:
        return any(
            can_access_project(database, user, project_id)
            for project_id in handover.affected_project_ids
        ) or not handover.affected_project_ids
    # A ranked candidate may see that they were recommended.
    return any(
        recommendation.user_id == user.id
        for recommendation in handover.candidate_recommendations
    )


def can_approve_handover(database: Database, user: User, handover: HandoverRecord) -> bool:
    """Only a manager of an affected project may approve a reassignment."""
    if user.role is not Role.MANAGER:
        return False
    if not handover.affected_project_ids:
        return True
    return any(
        is_manager_of_project(database, user, project_id)
        for project_id in handover.affected_project_ids
    )


def require_manager(user: User) -> None:
    if user.role is not Role.MANAGER:
        raise AuthorizationError("This action requires a manager role.")


def visible_requests(database: Database, user: User) -> list[SupportRequest]:
    return [
        request
        for request in database.requests.list_all()
        if can_view_request(database, user, request)
    ]


def visible_actions(database: Database, user: User) -> list[ActionItem]:
    return [
        action
        for action in database.actions.list_all()
        if can_view_action(database, user, action)
    ]


def visible_handovers(database: Database, user: User) -> list[HandoverRecord]:
    return [
        handover
        for handover in database.handovers.list_all()
        if can_view_handover(database, user, handover)
    ]
