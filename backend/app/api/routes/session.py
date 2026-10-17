"""Session and identity."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import Config, CurrentUser, Db
from app.models.enums import Role
from app.schemas.api import DevPersona, SessionInfo, SessionUser

router = APIRouter(tags=["session"])


@router.get("/session", response_model=SessionInfo)
def read_session(user: CurrentUser, settings: Config, database: Db) -> SessionInfo:
    personas: list[DevPersona] = []
    if settings.dev_auth_enabled and settings.auth_mode == "dev":
        # Managers first so the demo opens on the manager persona.
        people = sorted(
            database.users.list_all(),
            key=lambda item: (item.role is not Role.MANAGER, item.name),
        )
        personas = [
            DevPersona(id=item.id, name=item.name, role=item.role, title=item.title)
            for item in people
        ]
    return SessionInfo(
        user=SessionUser(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            title=user.title,
            team_id=user.team_id,
            availability_status=user.availability_status,
            authorized_project_ids=user.authorized_project_ids,
            skills=user.skills,
        ),
        auth_mode=settings.auth_mode,
        environment=settings.environment,
        demo_data_mode=settings.demo_data_mode,
        ai_configured=settings.ai_configured,
        ai_model=settings.gemini_model if settings.ai_configured else None,
        dev_personas=personas,
    )
