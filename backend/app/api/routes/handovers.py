"""Handover workflow endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import Context, CurrentUser, Db, Handovers
from app.schemas.api import (
    HandoverAnalysisResponse,
    HandoverApprove,
    HandoverCreate,
    HandoverDecision,
    HandoverReject,
    HandoverView,
)
from app.services import authz, views

router = APIRouter(prefix="/handovers", tags=["handovers"])


def _view(context: Context, handover, *, include_audit: bool = False) -> HandoverView:
    return views.handover_view(
        handover,
        database=context.db,
        viewer=context.user,
        now=context.now,
        include_audit=include_audit,
    )


@router.post("", response_model=HandoverView, status_code=status.HTTP_201_CREATED)
def create_handover(
    payload: HandoverCreate,
    context: Context,
    user: CurrentUser,
    handover_service: Handovers,
) -> HandoverView:
    handover = handover_service.create(
        actor=user,
        unavailable_user_id=payload.unavailable_user_id or user.id,
        start_time=payload.start_time,
        expected_return=payload.expected_return,
        reason_category=payload.reason_category,
        handover_notes=payload.handover_notes,
        affected_task_ids=payload.affected_task_ids,
    )
    return _view(context, handover)


@router.get("", response_model=list[HandoverView])
def list_handovers(
    context: Context,
    pending_only: bool = Query(default=False),
) -> list[HandoverView]:
    items = authz.visible_handovers(context.db, context.user)
    if pending_only:
        items = [item for item in items if item.manager_approval_status.value == "pending"]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return [_view(context, item) for item in items]


@router.get("/{handover_id}", response_model=HandoverView)
def get_handover(handover_id: str, context: Context) -> HandoverView:
    handover = context.db.handovers.require(handover_id)
    if not authz.can_view_handover(context.db, context.user, handover):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this handover.",
        )
    return _view(context, handover, include_audit=True)


@router.post("/{handover_id}/analyze", response_model=HandoverAnalysisResponse)
def analyze_handover(
    handover_id: str,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> HandoverAnalysisResponse:
    """Run the impact analysis, rank candidates and generate the brief."""
    handover = database.handovers.require(handover_id)
    updated, analysis = handover_service.analyze(handover=handover, actor=user)
    return HandoverAnalysisResponse(
        handover=_view(context, updated, include_audit=True), analysis=analysis
    )


@router.post("/{handover_id}/approve", response_model=HandoverView)
def approve_handover(
    handover_id: str,
    payload: HandoverApprove,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> HandoverView:
    handover = database.handovers.require(handover_id)
    try:
        updated = handover_service.approve(
            handover=handover,
            manager=user,
            selected_backup_id=payload.selected_backup_id,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _view(context, updated, include_audit=True)


@router.post("/{handover_id}/reject", response_model=HandoverView)
def reject_handover(
    handover_id: str,
    payload: HandoverReject,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> HandoverView:
    handover = database.handovers.require(handover_id)
    updated = handover_service.reject(handover=handover, manager=user, reason=payload.reason)
    return _view(context, updated, include_audit=True)


@router.post("/{handover_id}/accept", response_model=HandoverView)
def accept_handover(
    handover_id: str,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> HandoverView:
    """The nominated backup accepts; task ownership transfers here."""
    handover = database.handovers.require(handover_id)
    try:
        updated = handover_service.accept(handover=handover, backup=user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _view(context, updated, include_audit=True)


@router.post("/{handover_id}/decline", response_model=HandoverView)
def decline_handover(
    handover_id: str,
    payload: HandoverDecision,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> HandoverView:
    handover = database.handovers.require(handover_id)
    updated = handover_service.decline(
        handover=handover, backup=user, reason=payload.reason or "No reason given."
    )
    return _view(context, updated, include_audit=True)
