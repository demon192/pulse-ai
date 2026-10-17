"""Development-only administration.

Both endpoints are refused unless ``SEED_ENDPOINT_ENABLED`` is true, which the
settings model forces to false in production.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import Config, Db
from app.core.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


def _require_enabled(settings: Config) -> None:
    if not settings.seed_endpoint_enabled or settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
        )


@router.post("/seed", status_code=status.HTTP_200_OK)
def reseed(settings: Config, database: Db) -> dict[str, object]:
    """Reset the workspace to the labelled synthetic demo data."""
    _require_enabled(settings)
    from app.demo.seed import seed

    summary = seed(database, reset=True)
    logger.info("Demo data reseeded: %s", summary)
    return {"status": "seeded", "counts": summary, "demo_data": True}


@router.get("/stats")
def stats(settings: Config, database: Db) -> dict[str, int]:
    _require_enabled(settings)
    return {
        "users": database.users.count(),
        "projects": database.projects.count(),
        "milestones": database.milestones.count(),
        "tasks": database.tasks.count(),
        "support_requests": database.requests.count(),
        "action_items": database.actions.count(),
        "handovers": database.handovers.count(),
        "notifications": database.notifications.count(),
        "documents": database.documents.count(),
        "decisions": database.decisions.count(),
        "task_updates": database.task_updates.count(),
    }
