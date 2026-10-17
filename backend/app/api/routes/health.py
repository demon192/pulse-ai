"""Liveness and configuration probe (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import Config
from app.schemas.api import HealthResponse

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
