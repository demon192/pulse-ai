"""Domain enumerations shared by schemas, rules and the API surface."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    MANAGER = "manager"
    ENGINEER = "engineer"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    LIMITED = "limited"
    ON_LEAVE = "on_leave"
    UNAVAILABLE = "unavailable"


class ProjectStatus(StrEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ProjectHealth(StrEnum):
    ON_TRACK = "on_track"
    NEEDS_ATTENTION = "needs_attention"
    AT_RISK = "at_risk"


class TaskStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_WEIGHT: dict[str, int] = {
    Priority.LOW: 1,
    Priority.MEDIUM: 2,
    Priority.HIGH: 3,
    Priority.CRITICAL: 4,
}


class RequestCategory(StrEnum):
    BLOCKER = "blocker"
    DECISION = "decision"
    APPROVAL = "approval"
    ONE_ON_ONE = "one_on_one"
    PROGRESS_UPDATE = "progress_update"
    OTHER = "other"


class RequestStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


TERMINAL_REQUEST_STATUSES = frozenset({RequestStatus.RESOLVED, RequestStatus.CANCELLED})


class ActionType(StrEnum):
    APPROVAL = "approval"
    QUESTION = "question"
    SUPPORT_REQUEST = "support_request"
    FOLLOW_UP = "follow_up"
    DEADLINE = "deadline"
    OVERDUE_TASK = "overdue_task"
    BLOCKER = "blocker"
    HANDOVER_APPROVAL = "handover_approval"
    ONE_ON_ONE = "one_on_one"


class ActionStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


TERMINAL_ACTION_STATUSES = frozenset({ActionStatus.RESOLVED, ActionStatus.CANCELLED})


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class HandoverStatus(StrEnum):
    DRAFT = "draft"
    ANALYZED = "analyzed"
    PENDING_MANAGER_REVIEW = "pending_manager_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NotificationType(StrEnum):
    SUPPORT_REQUEST_CREATED = "support_request_created"
    APPROVAL_REQUESTED = "approval_requested"
    ACTION_DUE_SOON = "action_due_soon"
    BLOCKER_REPORTED = "blocker_reported"
    TASK_OVERDUE = "task_overdue"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    HANDOVER_REVIEW_REQUIRED = "handover_review_required"
    HANDOVER_APPROVED = "handover_approved"
    HANDOVER_ASSIGNMENT_ACCEPTED = "handover_assignment_accepted"
    REQUEST_RESPONDED = "request_responded"
    REQUEST_RESOLVED = "request_resolved"
    BACKUP_ASSIGNED = "backup_assigned"


class EvidenceKind(StrEnum):
    """How a statement in a briefing was derived.

    The AI layer is required to keep these apart so a manager can tell a
    database fact from a rules-engine inference from a model hypothesis.
    """

    VERIFIED_FACT = "verified_fact"
    RULE_DERIVED = "rule_derived"
    HYPOTHESIS = "hypothesis"
    RECOMMENDATION = "recommendation"


class RiskKind(StrEnum):
    OVERDUE_TASK = "overdue_task"
    BLOCKED_TASK = "blocked_task"
    BLOCKED_DEPENDENCY_CHAIN = "blocked_dependency_chain"
    PENDING_APPROVAL_BLOCKING_WORK = "pending_approval_blocking_work"
    MILESTONE_AT_RISK = "milestone_at_risk"
    UNASSIGNED_CRITICAL_WORK = "unassigned_critical_work"
    COVERAGE_GAP = "coverage_gap"
