"""FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.ai.service import AIService
from app.core.config import Settings
from app.core.security import AuthenticationError, resolve_user
from app.notifications.service import NotificationService
from app.repositories.base import EntityNotFound
from app.repositories.database import Database
from app.schemas.domain import User
from app.services.authz import AuthorizationError
from app.services.context import WorkContext
from app.services.handovers import HandoverService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_notifications(request: Request) -> NotificationService:
    return request.app.state.notifications


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def get_handover_service(request: Request) -> HandoverService:
    return request.app.state.handover_service


def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    database: Annotated[Database, Depends(get_database)],
) -> User:
    try:
        return resolve_user(
            settings=settings,
            database=database,
            headers=dict(request.headers),
            verifier=request.app.state.firebase_verifier,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[Database, Depends(get_database)]
Notifications = Annotated[NotificationService, Depends(get_notifications)]
AI = Annotated[AIService, Depends(get_ai_service)]
Handovers = Annotated[HandoverService, Depends(get_handover_service)]
Config = Annotated[Settings, Depends(get_settings_dep)]


def get_context(user: CurrentUser, database: Db) -> WorkContext:
    return WorkContext(database, user)


Context = Annotated[WorkContext, Depends(get_context)]


def forbidden(exc: AuthorizationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.detail)


def not_found(exc: EntityNotFound) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{exc.collection.rstrip('s').replace('_', ' ')} '{exc.doc_id}' was not found.",
    )
