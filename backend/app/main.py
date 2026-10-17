"""TeamPulse AI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai.service import AIService
from app.api.routes import (
    actions,
    admin,
    ai,
    dashboard,
    handovers,
    health,
    notifications,
    projects,
    requests,
    session,
    team,
)
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import FirebaseVerifier
from app.notifications.service import NotificationService
from app.repositories.base import EntityNotFound
from app.repositories.database import Database, build_database
from app.services.authz import AuthorizationError
from app.services.handovers import HandoverService

logger = get_logger(__name__)

API_PREFIX = "/api"


def create_app(
    settings: Settings | None = None, database: Database | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info(
            "Starting %s | environment=%s backend=%s auth=%s ai_configured=%s",
            settings.app_name,
            settings.environment,
            settings.data_backend,
            settings.auth_mode,
            settings.ai_configured,
        )
        if settings.environment == "production" and settings.dev_auth_enabled:
            # Defence in depth: Settings already forces this off.
            raise RuntimeError("Development authentication cannot run in production.")
        yield
        logger.info("Shutting down %s", settings.app_name)

    application = FastAPI(
        title=settings.app_name,
        version=health.VERSION,
        description=(
            "Engineering operations dashboard: project intelligence, engineer "
            "support, a manager action inbox and intelligent handovers."
        ),
        lifespan=lifespan,
    )

    application.state.settings = settings
    application.state.database = database or build_database(settings)
    application.state.notifications = NotificationService(application.state.database)
    application.state.ai_service = AIService(settings, application.state.database)
    application.state.handover_service = HandoverService(
        application.state.database,
        application.state.notifications,
        application.state.ai_service,
    )
    application.state.firebase_verifier = (
        FirebaseVerifier(settings) if settings.auth_mode == "firebase" else None
    )

    # The in-memory backend starts empty, so a local run would otherwise show a
    # blank app. Firestore is never auto-seeded: use scripts/seed_demo_data.py.
    if (
        settings.data_backend == "memory"
        and settings.demo_data_mode
        and settings.environment != "production"
        and application.state.database.is_empty()
    ):
        from app.demo.seed import seed

        counts = seed(application.state.database, reset=False)
        logger.info("Loaded synthetic demo data: %s", counts)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Dev-User-Id"],
    )

    _register_exception_handlers(application)
    _register_routes(application)
    _mount_frontend(application, settings)
    return application


def _register_routes(application: FastAPI) -> None:
    application.include_router(health.router)
    application.include_router(health.router, prefix=API_PREFIX)
    for router in (
        session.router,
        dashboard.router,
        projects.router,
        requests.router,
        actions.router,
        handovers.router,
        notifications.router,
        ai.router,
        team.router,
        admin.router,
    ):
        application.include_router(router, prefix=API_PREFIX)


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AuthorizationError)
    async def _authorization_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @application.exception_handler(EntityNotFound)
    async def _not_found_handler(_: Request, exc: EntityNotFound) -> JSONResponse:
        label = exc.collection.rstrip("s").replace("_", " ")
        return JSONResponse(
            status_code=404, content={"detail": f"{label} '{exc.doc_id}' was not found."}
        )

    @application.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Echo the field errors but never the submitted values.
        return JSONResponse(
            status_code=422,
            content={
                "detail": "The request payload failed validation.",
                "errors": [
                    {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
                    for error in exc.errors()
                ],
            },
        )

    @application.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the type and path only: never the payload or the exception text.
        logger.exception(
            "Unhandled error on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. The incident was logged."},
        )


def _mount_frontend(application: FastAPI, settings: Settings) -> None:
    """Serve the built single-page app alongside the API (Cloud Run layout)."""
    if not settings.serve_frontend:
        return
    dist = Path(settings.frontend_dist_dir)
    if not dist.is_absolute():
        dist = Path(__file__).resolve().parent.parent / dist
    if not dist.exists():
        logger.warning("SERVE_FRONTEND is on but %s does not exist", dist)
        return
    application.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
    logger.info("Serving the frontend from %s", dist)


app = create_app()
