"""Liveness and configuration probes (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import Config
from app.schemas.api import AuthConfigResponse, HealthResponse

router = APIRouter(tags=["health"])

VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
def health(settings: Config) -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        data_backend=settings.data_backend,
        ai_configured=settings.ai_configured,
        version=VERSION,
    )


@router.get("/auth-config", response_model=AuthConfigResponse)
def auth_config(settings: Config) -> AuthConfigResponse:
    """How this instance expects callers to authenticate.

    Deliberately unauthenticated and deliberately runtime: the SPA is built
    once into the container image and asks the instance it is served from,
    rather than having a project baked in at build time.
    """
    firebase_mode = settings.auth_mode == "firebase"
    return AuthConfigResponse(
        auth_mode=settings.auth_mode,
        environment=settings.environment,
        sign_in_configured=settings.sign_in_configured,
        dev_personas_enabled=settings.dev_auth_enabled and settings.auth_mode == "dev",
        firebase_api_key=settings.firebase_web_api_key if firebase_mode else None,
        firebase_auth_domain=settings.resolved_auth_domain if firebase_mode else None,
        firebase_project_id=settings.firebase_project_id if firebase_mode else None,
    )
