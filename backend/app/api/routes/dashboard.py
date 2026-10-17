"""Role dashboards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AI, Context, Notifications
from app.models.enums import Role
from app.schemas.api import EngineerDashboard, ManagerDashboard
from app.services.dashboard import build_engineer_dashboard, build_manager_dashboard
from app.services.sweeps import run_sweep

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/manager", response_model=ManagerDashboard)
def manager_dashboard(
    context: Context, notifications: Notifications, ai_service: AI
) -> ManagerDashboard:
    if context.user.role is not Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The manager dashboard requires a manager role.",
        )
    # Deterministic sweep: cheap, idempotent, no model call.
    run_sweep(
        context.db,
        notifications,
        project_ids=context.project_ids,
        now=context.now,
    )
    return build_manager_dashboard(context, notifications, ai_service)


@router.get("/engineer", response_model=EngineerDashboard)
def engineer_dashboard(context: Context, notifications: Notifications) -> EngineerDashboard:
    run_sweep(
        context.db,
        notifications,
        project_ids=context.project_ids,
        now=context.now,
    )
    return build_engineer_dashboard(context, notifications)
