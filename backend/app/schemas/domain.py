"""Persisted domain entities.

These models are the contract shared by the Firestore repositories, the rules
engine and the HTTP API. Timestamps are always timezone-aware UTC.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.clock import ensure_utc, utc_now
from app.models.enums import (
    ActionStatus,
    ActionType,
    ApprovalStatus,
    AvailabilityStatus,
    EvidenceKind,
    HandoverStatus,
    NotificationType,
    Priority,
    ProjectStatus,
    RequestCategory,
    RequestStatus,
    Role,
    TaskStatus,
)


class TeamPulseModel(BaseModel):
    """Base model: strict field names, UTC-normalised datetimes."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    @field_validator("*", mode="after")
    @classmethod
    def _normalise_datetimes(cls, value: object) -> object:
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------


class User(TeamPulseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    team_id: str
    title: str | None = None
    manager_id: str | None = None
    skills: list[str] = Field(default_factory=list)
    # project_id -> familiarity score 0..1 (derived from authorized work records)
    project_familiarity: dict[str, float] = Field(default_factory=dict)
    weekly_capacity: float = 40.0
    assigned_workload: float = 0.0
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    # Hard eligibility gate: a user can only be assigned work in these projects.
    authorized_project_ids: list[str] = Field(default_factory=list)
    # Coarse-grained capability flags, e.g. "approve_api_design".
    permissions: list[str] = Field(default_factory=list)
    is_demo_data: bool = True

    @field_validator("project_familiarity")
    @classmethod
    def _bounded_familiarity(cls, value: dict[str, float]) -> dict[str, float]:
        for project_id, score in value.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"project_familiarity[{project_id}] must be between 0 and 1"
                )
        return value

    @property
    def utilisation(self) -> float:
        """Assigned hours as a fraction of weekly capacity (0 when no capacity)."""
        if self.weekly_capacity <= 0:
            return 1.0
        return self.assigned_workload / self.weekly_capacity


class UserPublic(TeamPulseModel):
    """Projection returned to clients. Never carries permissions or workload."""

    id: str
    name: str
    role: Role
    title: str | None = None
    availability_status: AvailabilityStatus


# --------------------------------------------------------------------------
# Projects, milestones, tasks
# --------------------------------------------------------------------------


class Milestone(TeamPulseModel):
    id: str
    project_id: str
    name: str
    description: str | None = None
    target_date: datetime
    task_ids: list[str] = Field(default_factory=list)
    completed: bool = False


class Project(TeamPulseModel):
    id: str
    name: str
    description: str
    manager_id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    start_date: datetime
    target_date: datetime
    milestone_ids: list[str] = Field(default_factory=list)
    team_member_ids: list[str] = Field(default_factory=list)
    is_demo_data: bool = True


class Task(TeamPulseModel):
    id: str
    project_id: str
    title: str
    description: str
    owner_id: str | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    due_date: datetime | None = None
    # Tasks this task depends on (must finish first).
    dependency_ids: list[str] = Field(default_factory=list)
    related_request_ids: list[str] = Field(default_factory=list)
    related_document_ids: list[str] = Field(default_factory=list)
    next_step: str | None = None
    # Skills needed to pick this task up; drives backup-candidate ranking.
    required_skills: list[str] = Field(default_factory=list)
    # Optional capability flag a user must hold to own this task.
    required_permission: str | None = None
    estimated_effort: float | None = None
    remaining_effort: float | None = None
    blocked_reason: str | None = None
    is_demo_data: bool = True

    @property
    def is_open(self) -> bool:
        return self.status is not TaskStatus.COMPLETED


class TaskUpdate(TeamPulseModel):
    """A free-text progress note. Treated as untrusted input by the AI layer."""

    id: str
    task_id: str
    author_id: str
    body: str
    created_at: datetime = Field(default_factory=utc_now)
    is_demo_data: bool = True


class ProjectDocument(TeamPulseModel):
    id: str
    project_id: str
    task_ids: list[str] = Field(default_factory=list)
    title: str
    doc_type: str = "reference"
    url: str | None = None
    summary: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    is_demo_data: bool = True


class DecisionRecord(TeamPulseModel):
    id: str
    project_id: str
    task_id: str | None = None
    title: str
    decision: str
    rationale: str | None = None
    decided_by: str
    decided_at: datetime = Field(default_factory=utc_now)
    is_demo_data: bool = True


# --------------------------------------------------------------------------
# Support requests and manager actions
# --------------------------------------------------------------------------


class RequestResponse(TeamPulseModel):
    author_id: str
    body: str
    created_at: datetime = Field(default_factory=utc_now)


class SupportRequest(TeamPulseModel):
    id: str
    engineer_id: str
    project_id: str
    task_id: str | None = None
    category: RequestCategory
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    status: RequestStatus = RequestStatus.OPEN
    assigned_owner_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    due_date: datetime | None = None
    responses: list[RequestResponse] = Field(default_factory=list)
    resolution_notes: str | None = None
    # Engineer-authored correction of an inaccurate AI summary.
    engineer_context_note: str | None = None
    is_demo_data: bool = True

    @property
    def is_open(self) -> bool:
        return self.status not in (RequestStatus.RESOLVED, RequestStatus.CANCELLED)


class ActionItem(TeamPulseModel):
    id: str
    project_id: str | None = None
    task_id: str | None = None
    source_request_id: str | None = None
    source_handover_id: str | None = None
    type: ActionType
    title: str
    description: str
    owner_id: str
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    due_date: datetime | None = None
    status: ActionStatus = ActionStatus.OPEN
    priority: Priority = Priority.MEDIUM
    resolution_notes: str | None = None
    decision_record_id: str | None = None
    is_demo_data: bool = True

    @property
    def is_open(self) -> bool:
        return self.status not in (ActionStatus.RESOLVED, ActionStatus.CANCELLED)


# --------------------------------------------------------------------------
# Handover
# --------------------------------------------------------------------------


class CandidateScoreBreakdown(TeamPulseModel):
    """Per-factor contribution to a backup candidate's score.

    ``weight`` and ``raw_score`` are kept separately so the UI can show how a
    recommendation was produced rather than just a final number.
    """

    factor: str
    weight: float
    raw_score: float
    weighted_score: float
    explanation: str


class CandidateRecommendation(TeamPulseModel):
    user_id: str
    user_name: str
    eligible: bool
    # Populated when ``eligible`` is False; blocks assignment entirely.
    ineligibility_reasons: list[str] = Field(default_factory=list)
    total_score: float = 0.0
    breakdown: list[CandidateScoreBreakdown] = Field(default_factory=list)
    summary: str = ""


class HandoverBriefSection(TeamPulseModel):
    key: str
    heading: str
    content: str
    evidence_kind: EvidenceKind = EvidenceKind.VERIFIED_FACT
    source_ids: list[str] = Field(default_factory=list)


class HandoverBrief(TeamPulseModel):
    task_id: str
    task_title: str
    sections: list[HandoverBriefSection] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    generated_by: str = "deterministic"


class HandoverRecord(TeamPulseModel):
    id: str
    unavailable_user_id: str
    requested_by: str
    reason_category: str = "unplanned_leave"
    start_time: datetime
    expected_return: datetime | None = None
    affected_task_ids: list[str] = Field(default_factory=list)
    affected_project_ids: list[str] = Field(default_factory=list)
    downstream_task_ids: list[str] = Field(default_factory=list)
    pending_approval_action_ids: list[str] = Field(default_factory=list)
    relevant_document_ids: list[str] = Field(default_factory=list)
    affected_milestone_ids: list[str] = Field(default_factory=list)
    candidate_recommendations: list[CandidateRecommendation] = Field(
        default_factory=list
    )
    generated_brief: list[HandoverBrief] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    handover_notes: str | None = None
    manager_approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: str | None = None
    approved_at: datetime | None = None
    selected_backup_id: str | None = None
    backup_accepted_at: datetime | None = None
    handover_status: HandoverStatus = HandoverStatus.DRAFT
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    is_demo_data: bool = True


# --------------------------------------------------------------------------
# Notifications and audit
# --------------------------------------------------------------------------


class Notification(TeamPulseModel):
    id: str
    recipient_id: str
    type: NotificationType
    title: str
    message: str
    reason: str
    suggested_action: str | None = None
    priority: Priority = Priority.MEDIUM
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    read_at: datetime | None = None
    resolved_at: datetime | None = None
    # Stable key used to suppress duplicate notifications for the same event.
    deduplication_key: str
    escalation_count: int = 0
    last_escalated_at: datetime | None = None
    is_demo_data: bool = True


class AuditEvent(TeamPulseModel):
    """Who changed what. Deliberately free of request bodies and personal data."""

    id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    created_at: datetime = Field(default_factory=utc_now)
    details: dict[str, str] = Field(default_factory=dict)


class AISummaryCache(TeamPulseModel):
    """A persisted AI output keyed by a fingerprint of its inputs."""

    id: str
    kind: str
    subject_id: str
    fingerprint: str
    payload: dict
    generated_at: datetime = Field(default_factory=utc_now)
    generated_by: str = "gemini"
