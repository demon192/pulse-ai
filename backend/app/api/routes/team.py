"""Reference data about the team the caller is authorised to see."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import Context
from app.schemas.api import TeamMemberView
from app.services import views

router = APIRouter(tags=["team"])


@router.get("/team", response_model=list[TeamMemberView])
def list_team(context: Context) -> list[TeamMemberView]:
    """Team members who share at least one project with the caller."""
    members: list[TeamMemberView] = []
    for user in context.db.users.list_all():
        shared = set(user.authorized_project_ids) & context.project_ids
        is_project_manager = any(
            project.manager_id == user.id for project in context.projects
        )
        if not shared and not is_project_manager:
            continue
        members.append(
            TeamMemberView(
                user=views.to_public(user),
                open_task_count=len(
                    [
                        task
                        for task in context.open_tasks_for_user(user.id)
                        if task.project_id in context.project_ids
                    ]
                ),
                is_authorized_here=bool(shared),
            )
        )
    members.sort(key=lambda item: item.user.name)
    return members
