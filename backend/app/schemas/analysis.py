"""Computed (non-persisted) analysis structures produced by the rules engine."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EvidenceKind, Priority, ProjectHealth, RiskKind
from app.schemas.domain import CandidateRecommendation


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(AnalysisModel):
    """A single verifiable fact backing a finding, linked to its source record."""

    label: str
    detail: str
    entity_type: str | None = None
    entity_id: str | None = None


class RiskFinding(AnalysisModel):
    id: str
    kind: RiskKind
    # 0..100, produced by deterministic rules only.
    severity: int
    title: str
    summary: str
    project_id: str
    task_ids: list[str] = Field(default_factory=list)
    downstream_task_ids: list[str] = Field(default_factory=list)
    milestone_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    request_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    # Filled in by the AI layer; the finding itself is rule-derived.
    explanation: str | None = None
    explanation_source: str | None = None


class MilestoneStatus(AnalysisModel):
    milestone_id: str
    name: str
    target_date: datetime
    days_remaining: float
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    at_risk: bool
    reasons: list[str] = Field(default_factory=list)


class ProjectHealthReport(AnalysisModel):
    project_id: str
    project_name: str
    health: ProjectHealth
    # 0..100 where 100 is healthiest. Deterministic.
    health_score: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    open_requests: int
    open_actions: int
    next_milestone: MilestoneStatus | None = None
    milestones: list[MilestoneStatus] = Field(default_factory=list)
    risks: list[RiskFinding] = Field(default_factory=list)
    headline: str = ""


class PriorityFactor(AnalysisModel):
    factor: str
    points: float
    detail: str


class ActionPriority(AnalysisModel):
    action_id: str
    score: float
    bucket: str
    # Days until the action's own due date, negative when overdue. Computed
    # server-side so the UI never has to read the clock while rendering.
    due_in_days: float | None = None
    factors: list[PriorityFactor] = Field(default_factory=list)
    blocks_task_ids: list[str] = Field(default_factory=list)
    affected_milestone_ids: list[str] = Field(default_factory=list)
    consequence: str | None = None


class HandoverAnalysis(AnalysisModel):
    """Deterministic impact analysis for an unavailable engineer."""

    handover_id: str
    unavailable_user_id: str
    unavailable_user_name: str
    active_task_ids: list[str] = Field(default_factory=list)
    downstream_task_ids: list[str] = Field(default_factory=list)
    affected_project_ids: list[str] = Field(default_factory=list)
    affected_milestone_ids: list[str] = Field(default_factory=list)
    # Open upstream work the affected tasks wait on. Not reassigned, but the
    # backup needs it — a pending approval here is often the real blocker.
    upstream_blocking_task_ids: list[str] = Field(default_factory=list)
    pending_approval_action_ids: list[str] = Field(default_factory=list)
    relevant_document_ids: list[str] = Field(default_factory=list)
    open_request_ids: list[str] = Field(default_factory=list)
    candidates: list[CandidateRecommendation] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class AIStatement(AnalysisModel):
    """A single AI-produced statement, tagged with how it was derived."""

    text: str
    evidence_kind: EvidenceKind
    source_ids: list[str] = Field(default_factory=list)


class CoverageGap(AnalysisModel):
    user_id: str
    user_name: str
    availability_status: str
    open_task_count: int
    has_approved_handover: bool
    handover_id: str | None = None
    priority: Priority = Priority.MEDIUM
