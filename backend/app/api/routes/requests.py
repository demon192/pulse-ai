"""Engineer support requests."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AI, Context, CurrentUser, Db, Notifications
from app.models.enums import RequestCategory, RequestStatus
from app.schemas.api import (
    AIEnvelope,
    AIMeta,
    SupportRequestCreate,
    SupportRequestCreated,
    SupportRequestPatch,
    SupportRequestRespond,
    SupportRequestView,
)
from app.services import authz, facts, views
from app.services import requests as request_service

router = APIRouter(prefix="/requests", tags=["support requests"])


def _view(context: Context, request) -> SupportRequestView:
    return views.request_view(
        request,
        database=context.db,
        user_names={user.id: user.name for user in context.db.users.list_all()},
        project_names={p.id: p.name for p in context.db.projects.list_all()},
    )


@router.post("", response_model=SupportRequestCreated, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: SupportRequestCreate,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
    ai_service: AI,
    interpret: bool = Query(
        default=True, description="Also run the Gemini interpretation of the request."
    ),
) -> SupportRequestCreated:
    try:
        request, action = request_service.create_request(
            database,
            notifications,
            engineer=user,
            project_id=payload.project_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            task_id=payload.task_id,
            priority=payload.priority,
            due_date=payload.due_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    interpretation = None
    if interpret:
        interpretation = _interpret(context, ai_service, request)

    # The briefing for this project no longer reflects reality.
    database.ai_cache.delete(f"project_briefing:{payload.project_id}")
    return SupportRequestCreated(
        request=request, action_item=action, interpretation=interpretation
    )


def _interpret(context: Context, ai_service: AI, request) -> AIEnvelope:
    engineer = context.db.users.require(request.engineer_id)
    project = context.db.projects.require(request.project_id)
    candidate_tasks = [
        task
        for task in context.db.tasks.list_all()
        if task.project_id == request.project_id
        and (task.owner_id == engineer.id or task.id == request.task_id)
    ]
    payload, untrusted = facts.request_interpretation_facts(
        request=request,
        engineer=engineer,
        project=project,
        candidate_tasks=candidate_tasks,
        now=context.now,
    )
    result = ai_service.interpret_request(
        request_id=request.id, facts=payload, untrusted=untrusted
    )
    return AIEnvelope(
        meta=AIMeta(
            source=result.source,
            model=result.model,
            generated_at=result.generated_at,
            degraded=result.degraded,
            notes=result.notes,
        ),
        data=result.payload,
    )


@router.get("", response_model=list[SupportRequestView])
def list_requests(
    context: Context,
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    project_id: str | None = Query(default=None),
    category: RequestCategory | None = Query(default=None),
    engineer_id: str | None = Query(default=None),
    include_closed: bool = Query(default=True),
) -> list[SupportRequestView]:
    """Only requests the caller is authorised to see are returned."""
    items = context.requests
    if status_filter is not None:
        items = [item for item in items if item.status is status_filter]
    if not include_closed:
        items = [item for item in items if item.is_open]
    if project_id is not None:
        items = [item for item in items if item.project_id == project_id]
    if category is not None:
        items = [item for item in items if item.category is category]
    if engineer_id is not None:
        items = [item for item in items if item.engineer_id == engineer_id]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return [_view(context, item) for item in items]


@router.get("/{request_id}", response_model=SupportRequestView)
def get_request(request_id: str, context: Context) -> SupportRequestView:
    request = context.db.requests.require(request_id)
    authz.require_request_access(context.db, context.user, request)
    return _view(context, request)


@router.patch("/{request_id}", response_model=SupportRequestView)
def patch_request(
    request_id: str,
    payload: SupportRequestPatch,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> SupportRequestView:
    request = database.requests.require(request_id)
    updated = request_service.update_request(
        database,
        notifications,
        request=request,
        actor=user,
        status=payload.status,
        priority=payload.priority,
        assigned_owner_id=payload.assigned_owner_id,
        resolution_notes=payload.resolution_notes,
        engineer_context_note=payload.engineer_context_note,
    )
    return _view(context, updated)


@router.post("/{request_id}/respond", response_model=SupportRequestView)
def respond_to_request(
    request_id: str,
    payload: SupportRequestRespond,
    context: Context,
    user: CurrentUser,
    database: Db,
    notifications: Notifications,
) -> SupportRequestView:
    request = database.requests.require(request_id)
    updated = request_service.respond(
        database,
        notifications,
        request=request,
        actor=user,
        body=payload.body,
        status=payload.status,
    )
    return _view(context, updated)


@router.post("/{request_id}/interpret", response_model=AIEnvelope)
def interpret_request(
    request_id: str, context: Context, ai_service: AI
) -> AIEnvelope:
    """Re-run the AI interpretation, e.g. after the engineer corrects context."""
    request = context.db.requests.require(request_id)
    authz.require_request_access(context.db, context.user, request)
    return _interpret(context, ai_service, request)
