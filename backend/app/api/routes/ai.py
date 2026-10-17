"""Explicit AI endpoints.

Generation is always an explicit call so that no dashboard render triggers a
model request.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AI, Context, CurrentUser, Db, Handovers
from app.schemas.api import (
    AIEnvelope,
    AIMeta,
    HandoverBriefRequest,
    ProjectBriefingRequest,
    RequestSummaryRequest,
    RiskExplanationRequest,
)
from app.services import authz, facts

router = APIRouter(prefix="/ai", tags=["ai"])


def _envelope(result) -> AIEnvelope:
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


@router.post("/project-briefing", response_model=AIEnvelope)
def project_briefing(
    payload: ProjectBriefingRequest, context: Context, ai_service: AI
) -> AIEnvelope:
    authz.require_project_access(context.db, context.user, payload.project_id)
    project = context.db.projects.require(payload.project_id)
    report = context.project_health(payload.project_id)
    briefing_facts, untrusted = facts.project_briefing_facts(
        report=report,
        project=project,
        tasks=context.tasks_for_project(payload.project_id),
        actions=context.actions,
        requests=context.requests,
        user_names={user.id: user.name for user in context.db.users.list_all()},
        now=context.now,
    )
    result = ai_service.project_briefing(
        project_id=payload.project_id,
        facts=briefing_facts,
        untrusted=untrusted,
        force_refresh=payload.force_refresh,
    )
    return _envelope(result)


@router.post("/request-summary", response_model=AIEnvelope)
def request_summary(
    payload: RequestSummaryRequest, context: Context, ai_service: AI
) -> AIEnvelope:
    request = context.db.requests.require(payload.request_id)
    authz.require_request_access(context.db, context.user, request)
    engineer = context.db.users.require(request.engineer_id)
    project = context.db.projects.require(request.project_id)
    candidate_tasks = [
        task
        for task in context.db.tasks.list_all()
        if task.project_id == request.project_id
        and (task.owner_id == engineer.id or task.id == request.task_id)
    ]
    payload_facts, untrusted = facts.request_interpretation_facts(
        request=request,
        engineer=engineer,
        project=project,
        candidate_tasks=candidate_tasks,
        now=context.now,
    )
    result = ai_service.interpret_request(
        request_id=request.id, facts=payload_facts, untrusted=untrusted
    )
    return _envelope(result)


@router.post("/handover-brief", response_model=AIEnvelope)
def handover_brief(
    payload: HandoverBriefRequest,
    context: Context,
    user: CurrentUser,
    database: Db,
    handover_service: Handovers,
) -> AIEnvelope:
    """Regenerate the brief for one task of a handover."""
    handover = database.handovers.require(payload.handover_id)
    if not authz.can_view_handover(database, user, handover):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this handover.",
        )
    task_id = payload.task_id or (
        handover.affected_task_ids[0] if handover.affected_task_ids else None
    )
    if task_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This handover has no affected tasks to brief. Run /analyze first.",
        )
    if task_id not in handover.affected_task_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That task is not part of this handover.",
        )

    task = database.tasks.require(task_id)
    unavailable_user = database.users.require(handover.unavailable_user_id)
    task_facts, untrusted, _missing = facts.handover_task_facts(
        database,
        task=task,
        graph=context.graph,
        unavailable_user=unavailable_user,
        handover_notes=handover.handover_notes,
        now=context.now,
    )
    handover_service.ai.invalidate("handover_brief", f"{handover.id}:{task_id}")
    result = handover_service.ai.handover_brief(
        handover_id=handover.id,
        task_id=task_id,
        facts=task_facts,
        untrusted=untrusted,
    )
    return _envelope(result)


@router.post("/risk-explanation", response_model=AIEnvelope)
def risk_explanation(
    payload: RiskExplanationRequest, context: Context, ai_service: AI
) -> AIEnvelope:
    """Explain one deterministic finding in plain language."""
    authz.require_project_access(context.db, context.user, payload.project_id)
    report = context.project_health(payload.project_id)
    finding = next(
        (item for item in report.risks if item.id == payload.finding_id), None
    )
    if finding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That finding is not currently active for this project.",
        )
    explanation_facts = facts.risk_explanation_facts(
        finding=finding,
        tasks={task.id: task for task in context.db.tasks.list_all()},
        user_names={user.id: user.name for user in context.db.users.list_all()},
        now=context.now,
    )
    result = ai_service.explain_risk(finding_id=finding.id, facts=explanation_facts)
    return _envelope(result)
