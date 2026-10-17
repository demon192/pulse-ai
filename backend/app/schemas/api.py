"""Request and response models for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActionStatus,
    ActionType,
    AvailabilityStatus,
    Priority,
    RequestCategory,
    RequestStatus,
    Role,
    TaskStatus,
)
from app.schemas.analysis import (
    ActionPriority,
    CoverageGap,
    HandoverAnalysis,
    MilestoneStatus,
    ProjectHealthReport,
    RiskFinding,
)
from app.schemas.domain import (
    ActionItem,
    AuditEvent,
    DecisionRecord,
    HandoverRecord,
    Milestone,
    Notification,
    Project,
    ProjectDocument,
    SupportRequest,
    Task,
    TaskUpdate,
    UserPublic,
)


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------


class SessionUser(APIModel):
    id: str
    name: str
    email: str
    role: Role
    title: str | None = None
    team_id: str
    availability_status: AvailabilityStatus
    authorized_project_ids: list[str]
    skills: list[str] = Field(default_factory=list)


class DevPersona(APIModel):
    id: str
    name: str
    role: Role
    title: str | None = None


class SessionInfo(APIModel):
    user: SessionUser
    auth_mode: str
    environment: str
    demo_data_mode: bool
    ai_configured: bool
    ai_model: str | None = None
    dev_personas: list[DevPersona] = Field(default_factory=list)


# --------------------------------------------------------------------------
# AI envelope
# --------------------------------------------------------------------------


class AIMeta(APIModel):
    source: str
    model: str | None = None
    generated_at: datetime | None = None
    degraded: bool = False
    notes: list[str] = Field(default_factory=list)


class AIEnvelope(APIModel):
    """Every AI response carries provenance so the UI can label it."""

    meta: AIMeta
    data: dict


# --------------------------------------------------------------------------
# Projects and tasks
# --------------------------------------------------------------------------


class TaskView(APIModel):
    task: Task
    owner_name: str
    project_name: str
    blocking_dependencies: list[str] = Field(default_factory=list)
    downstream_task_ids: list[str] = Field(default_factory=list)
    is_overdue: bool = False
    days_until_due: float | None = None


class ProjectSummary(APIModel):
    project: Project
    manager_name: str
    health: ProjectHealthReport


class ProjectDetail(APIModel):
    project: Project
    manager_name: str
    health: ProjectHealthReport
    milestones: list[Milestone]
    tasks: list[TaskView]
    team: list[UserPublic]
    documents: list[ProjectDocument]
    decisions: list[DecisionRecord]
    cached_briefing: AIEnvelope | None = None


class TaskPatch(APIModel):
    status: TaskStatus | None = None
    next_step: str | None = None
    remaining_effort: float | None = None
    blocked_reason: str | None = None
    priority: Priority | None = None
    progress_note: str | None = None


class TaskDetail(APIModel):
    task: TaskView
    updates: list[TaskUpdate]
    requests: list[SupportRequest]
    documents: list[ProjectDocument]
    dependencies: list[Task]
    dependents: list[Task]


# --------------------------------------------------------------------------
# Support requests
# --------------------------------------------------------------------------


class SupportRequestCreate(APIModel):
    project_id: str
    category: RequestCategory
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    task_id: str | None = None
    priority: Priority = Priority.MEDIUM
    due_date: datetime | None = None


class SupportRequestPatch(APIModel):
    status: RequestStatus | None = None
    priority: Priority | None = None
    assigned_owner_id: str | None = None
    resolution_notes: str | None = Field(default=None, max_length=5000)
    engineer_context_note: str | None = Field(default=None, max_length=5000)


class SupportRequestRespond(APIModel):
    body: str = Field(min_length=1, max_length=5000)
    status: RequestStatus | None = None


class SupportRequestView(APIModel):
    request: SupportRequest
    engineer_name: str
    project_name: str
    task_title: str | None = None
    owner_name: str | None = None
    action_item_id: str | None = None


class SupportRequestCreated(APIModel):
    request: SupportRequest
    action_item: ActionItem | None = None
    interpretation: AIEnvelope | None = None


# --------------------------------------------------------------------------
# Action inbox
# --------------------------------------------------------------------------


class ActionInboxItem(APIModel):
    action: ActionItem
    priority_detail: ActionPriority
    project_name: str | None = None
    task_title: str | None = None
    requester_name: str | None = None
    source_request: SupportRequest | None = None
    source_handover_id: str | None = None


class ActionCreate(APIModel):
    type: ActionType
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(max_length=5000, default="")
    owner_id: str
    project_id: str | None = None
    task_id: str | None = None
    priority: Priority = Priority.MEDIUM
    due_date: datetime | None = None


class ActionPatch(APIModel):
    status: ActionStatus | None = None
    priority: Priority | None = None
    owner_id: str | None = None
    due_date: datetime | None = None
    resolution_notes: str | None = Field(default=None, max_length=5000)


class ActionResolve(APIModel):
    resolution_notes: str = Field(min_length=1, max_length=5000)
    decision: str | None = Field(default=None, max_length=5000)
    decision_rationale: str | None = Field(default=None, max_length=5000)


# --------------------------------------------------------------------------
# Handover
# --------------------------------------------------------------------------


class HandoverCreate(APIModel):
    # Defaults to the caller; a manager may raise one for a team member.
    unavailable_user_id: str | None = None
    start_time: datetime
    expected_return: datetime | None = None
    reason_category: str = Field(default="unplanned_leave", max_length=64)
    handover_notes: str | None = Field(default=None, max_length=5000)
    affected_task_ids: list[str] = Field(default_factory=list)


class HandoverApprove(APIModel):
    selected_backup_id: str
    notes: str | None = Field(default=None, max_length=2000)


class HandoverReject(APIModel):
    reason: str = Field(min_length=1, max_length=2000)


class HandoverDecision(APIModel):
    reason: str | None = Field(default=None, max_length=2000)


class HandoverView(APIModel):
    handover: HandoverRecord
    unavailable_user_name: str
    selected_backup_name: str | None = None
    approved_by_name: str | None = None
    affected_tasks: list[Task] = Field(default_factory=list)
    downstream_tasks: list[Task] = Field(default_factory=list)
    affected_milestones: list[MilestoneStatus] = Field(default_factory=list)
    pending_actions: list[ActionItem] = Field(default_factory=list)
    documents: list[ProjectDocument] = Field(default_factory=list)
    audit_trail: list[AuditEvent] = Field(default_factory=list)
    can_approve: bool = False
    can_accept: bool = False


class HandoverAnalysisResponse(APIModel):
    handover: HandoverView
    analysis: HandoverAnalysis


# --------------------------------------------------------------------------
# Dashboards
# --------------------------------------------------------------------------


class ManagerSummary(APIModel):
    projects_total: int
    projects_at_risk: int
    tasks_needing_attention: int
    pending_approvals: int
    open_support_requests: int
    overdue_actions: int
    upcoming_milestones: int
    coverage_gaps: int
    unread_notifications: int


class ManagerDashboard(APIModel):
    generated_at: datetime
    summary: ManagerSummary
    project_health: list[ProjectHealthReport]
    action_inbox: list[ActionInboxItem]
    open_requests: list[SupportRequestView]
    upcoming_milestones: list[MilestoneStatus]
    top_risks: list[RiskFinding]
    coverage: list[CoverageGap]
    handovers_awaiting_review: list[HandoverView]
    recent_activity: list[Notification]
    # Served from cache only. Generating a new one is an explicit POST.
    daily_briefing: AIEnvelope | None = None


class EngineerSummary(APIModel):
    open_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    open_requests: int
    awaiting_response: int
    unread_notifications: int


class EngineerDashboard(APIModel):
    generated_at: datetime
    summary: EngineerSummary
    my_tasks: list[TaskView]
    my_blockers: list[TaskView]
    my_requests: list[SupportRequestView]
    awaiting_response: list[SupportRequestView]
    upcoming_deadlines: list[TaskView]
    availability_status: AvailabilityStatus
    my_handovers: list[HandoverView]
    assigned_to_me: list[HandoverView]
    recent_notifications: list[Notification]


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------


class NotificationList(APIModel):
    notifications: list[Notification]
    unread_count: int


# --------------------------------------------------------------------------
# AI endpoints
# --------------------------------------------------------------------------


class ProjectBriefingRequest(APIModel):
    project_id: str
    force_refresh: bool = False


class RequestSummaryRequest(APIModel):
    request_id: str


class HandoverBriefRequest(APIModel):
    handover_id: str
    task_id: str | None = None


class RiskExplanationRequest(APIModel):
    project_id: str
    finding_id: str


# --------------------------------------------------------------------------
# Team / reference data
# --------------------------------------------------------------------------


class TeamMemberView(APIModel):
    user: UserPublic
    open_task_count: int
    is_authorized_here: bool = True


class HealthResponse(APIModel):
    status: str
    environment: str
    data_backend: str
    ai_configured: bool
    version: str
