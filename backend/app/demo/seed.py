"""Reproducible synthetic demo data.

Every record is flagged ``is_demo_data=True`` and every date is relative to the
seeding moment, so the demo always shows a release three days away.

Nothing here is real: the organisation, people and projects are fictional.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.clock import utc_now
from app.models.enums import (
    ActionStatus,
    ActionType,
    AvailabilityStatus,
    NotificationType,
    Priority,
    ProjectStatus,
    RequestCategory,
    RequestStatus,
    Role,
    TaskStatus,
)
from app.notifications.service import attention_key, make_dedup_key
from app.repositories.database import Database
from app.schemas.domain import (
    ActionItem,
    DecisionRecord,
    Milestone,
    Notification,
    Project,
    ProjectDocument,
    RequestResponse,
    SupportRequest,
    Task,
    TaskUpdate,
    User,
)

MANAGER_ID = "mgr-001"
PROJECT_PAYMENTS = "proj-payments"
PROJECT_IDENTITY = "proj-identity"
PROJECT_INSIGHTS = "proj-insights"

ALL_PROJECTS = [PROJECT_PAYMENTS, PROJECT_IDENTITY, PROJECT_INSIGHTS]


def _at(now: datetime, days: float = 0.0, hours: float = 0.0) -> datetime:
    return now + timedelta(days=days, hours=hours)


def build_users(now: datetime) -> list[User]:
    """One manager and ten engineers with distinct skills and workloads."""
    return [
        User(
            id=MANAGER_ID,
            name="Priya Raman",
            email="priya.raman@example.com",
            role=Role.MANAGER,
            team_id="team-platform",
            title="Engineering Manager, Platform",
            skills=["people-management", "architecture", "payments"],
            project_familiarity={
                PROJECT_PAYMENTS: 0.8,
                PROJECT_IDENTITY: 0.6,
                PROJECT_INSIGHTS: 0.5,
            },
            weekly_capacity=40.0,
            assigned_workload=12.0,
            availability_status=AvailabilityStatus.AVAILABLE,
            authorized_project_ids=list(ALL_PROJECTS),
            permissions=["approve_api_design", "approve_handover", "security_reviewer"],
        ),
        User(
            id="eng-001",
            name="Arjun Mehta",
            email="arjun.mehta@example.com",
            role=Role.ENGINEER,
            team_id="team-platform",
            title="Senior Backend Engineer",
            manager_id=MANAGER_ID,
            skills=["backend", "api-design", "python", "payments"],
            project_familiarity={PROJECT_PAYMENTS: 0.9, PROJECT_IDENTITY: 0.2},
            weekly_capacity=40.0,
            assigned_workload=36.0,
            authorized_project_ids=[PROJECT_PAYMENTS, PROJECT_IDENTITY],
        ),
        User(
            id="eng-002",
            name="Lena Fischer",
            email="lena.fischer@example.com",
            role=Role.ENGINEER,
            team_id="team-platform",
            title="Backend Engineer",
            manager_id=MANAGER_ID,
            skills=["backend", "python", "postgres"],
            project_familiarity={PROJECT_PAYMENTS: 0.6, PROJECT_IDENTITY: 0.5},
            weekly_capacity=40.0,
            assigned_workload=20.0,
            authorized_project_ids=[PROJECT_PAYMENTS, PROJECT_IDENTITY],
        ),
        User(
            id="eng-003",
            name="Diego Alvarez",
            email="diego.alvarez@example.com",
            role=Role.ENGINEER,
            team_id="team-experience",
            title="Frontend Engineer",
            manager_id=MANAGER_ID,
            skills=["frontend", "react", "typescript"],
            project_familiarity={PROJECT_PAYMENTS: 0.4, PROJECT_INSIGHTS: 0.3},
            weekly_capacity=40.0,
            assigned_workload=30.0,
            authorized_project_ids=[PROJECT_PAYMENTS, PROJECT_INSIGHTS],
        ),
        User(
            id="eng-004",
            name="Mei Tanaka",
            email="mei.tanaka@example.com",
            role=Role.ENGINEER,
            team_id="team-identity",
            title="Backend Engineer",
            manager_id=MANAGER_ID,
            skills=["backend", "go", "kubernetes"],
            project_familiarity={PROJECT_IDENTITY: 0.8},
            weekly_capacity=40.0,
            assigned_workload=24.0,
            # Deliberately not authorised on payments: demonstrates the gate.
            authorized_project_ids=[PROJECT_IDENTITY],
        ),
        User(
            id="eng-005",
            name="Samuel Okafor",
            email="samuel.okafor@example.com",
            role=Role.ENGINEER,
            team_id="team-data",
            title="Data Engineer",
            manager_id=MANAGER_ID,
            skills=["data", "python", "dbt"],
            project_familiarity={PROJECT_INSIGHTS: 0.85},
            weekly_capacity=40.0,
            assigned_workload=32.0,
            authorized_project_ids=[PROJECT_INSIGHTS],
        ),
        User(
            id="eng-006",
            name="Nora Haddad",
            email="nora.haddad@example.com",
            role=Role.ENGINEER,
            team_id="team-identity",
            title="Security Engineer",
            manager_id=MANAGER_ID,
            skills=["security", "oauth", "identity"],
            project_familiarity={PROJECT_IDENTITY: 0.9},
            weekly_capacity=40.0,
            assigned_workload=26.0,
            authorized_project_ids=[PROJECT_IDENTITY],
            permissions=["security_reviewer"],
        ),
        User(
            id="eng-007",
            name="Tom Bergqvist",
            email="tom.bergqvist@example.com",
            role=Role.ENGINEER,
            team_id="team-experience",
            title="Frontend Engineer",
            manager_id=MANAGER_ID,
            skills=["frontend", "react"],
            project_familiarity={PROJECT_PAYMENTS: 0.3, PROJECT_IDENTITY: 0.4},
            weekly_capacity=40.0,
            assigned_workload=28.0,
            authorized_project_ids=[PROJECT_PAYMENTS, PROJECT_IDENTITY],
        ),
        User(
            id="eng-008",
            name="Rhea Kapoor",
            email="rhea.kapoor@example.com",
            role=Role.ENGINEER,
            team_id="team-platform",
            title="Senior Backend Engineer",
            manager_id=MANAGER_ID,
            skills=["backend", "python", "payments", "kafka"],
            project_familiarity={PROJECT_PAYMENTS: 0.95},
            weekly_capacity=40.0,
            assigned_workload=34.0,
            authorized_project_ids=[PROJECT_PAYMENTS],
        ),
        User(
            id="eng-009",
            name="Victor Oliveira",
            email="victor.oliveira@example.com",
            role=Role.ENGINEER,
            team_id="team-platform",
            title="Site Reliability Engineer",
            manager_id=MANAGER_ID,
            skills=["sre", "kubernetes", "terraform", "backend"],
            project_familiarity={PROJECT_PAYMENTS: 0.5},
            weekly_capacity=40.0,
            assigned_workload=18.0,
            # Already away: demonstrates the availability gate.
            availability_status=AvailabilityStatus.ON_LEAVE,
            authorized_project_ids=[PROJECT_PAYMENTS, PROJECT_INSIGHTS],
        ),
        User(
            id="eng-010",
            name="Aisha Khan",
            email="aisha.khan@example.com",
            role=Role.ENGINEER,
            team_id="team-data",
            title="Data Engineer",
            manager_id=MANAGER_ID,
            skills=["data", "spark", "python"],
            project_familiarity={PROJECT_INSIGHTS: 0.7},
            weekly_capacity=32.0,
            assigned_workload=16.0,
            availability_status=AvailabilityStatus.LIMITED,
            authorized_project_ids=[PROJECT_INSIGHTS],
        ),
    ]


def build_projects(now: datetime) -> list[Project]:
    return [
        Project(
            id=PROJECT_PAYMENTS,
            name="Payments Platform v2",
            description=(
                "Rebuild of the settlement and retry pipeline ahead of the "
                "Settlement API general-availability release."
            ),
            manager_id=MANAGER_ID,
            status=ProjectStatus.ACTIVE,
            start_date=_at(now, days=-70),
            target_date=_at(now, days=24),
            milestone_ids=["ms-pay-1", "ms-pay-2"],
            team_member_ids=[
                "eng-001",
                "eng-002",
                "eng-003",
                "eng-007",
                "eng-008",
                "eng-009",
            ],
        ),
        Project(
            id=PROJECT_IDENTITY,
            name="Identity & Access Revamp",
            description=(
                "Move internal sign-in to an OIDC provider and retire the legacy "
                "auth service."
            ),
            manager_id=MANAGER_ID,
            status=ProjectStatus.ACTIVE,
            start_date=_at(now, days=-40),
            target_date=_at(now, days=45),
            milestone_ids=["ms-id-1"],
            team_member_ids=["eng-001", "eng-002", "eng-004", "eng-006", "eng-007"],
        ),
        Project(
            id=PROJECT_INSIGHTS,
            name="Customer Insights Pipeline",
            description=(
                "Event ingestion and warehouse modelling for the customer "
                "insights dashboard."
            ),
            manager_id=MANAGER_ID,
            status=ProjectStatus.ACTIVE,
            start_date=_at(now, days=-25),
            target_date=_at(now, days=60),
            milestone_ids=["ms-in-1"],
            team_member_ids=["eng-003", "eng-005", "eng-009", "eng-010"],
        ),
    ]


def build_milestones(now: datetime) -> list[Milestone]:
    return [
        Milestone(
            id="ms-pay-1",
            project_id=PROJECT_PAYMENTS,
            name="Settlement API GA",
            description="Settlement API contract frozen and the worker in production.",
            target_date=_at(now, days=3),
            task_ids=["pay-01", "pay-02", "pay-03"],
        ),
        Milestone(
            id="ms-pay-2",
            project_id=PROJECT_PAYMENTS,
            name="Payments v2 full release",
            target_date=_at(now, days=24),
            task_ids=["pay-04", "pay-05", "pay-06", "pay-07"],
        ),
        Milestone(
            id="ms-id-1",
            project_id=PROJECT_IDENTITY,
            name="SSO pilot with two teams",
            target_date=_at(now, days=12),
            task_ids=["id-01", "id-02", "id-03"],
        ),
        Milestone(
            id="ms-in-1",
            project_id=PROJECT_INSIGHTS,
            name="Insights pipeline v1",
            target_date=_at(now, days=20),
            task_ids=["in-01", "in-02", "in-03"],
        ),
    ]


def build_tasks(now: datetime) -> list[Task]:
    return [
        # --- Payments -----------------------------------------------------
        Task(
            id="pay-01",
            project_id=PROJECT_PAYMENTS,
            title="Define settlement API contract",
            description=(
                "Finalise request/response schemas, idempotency semantics and "
                "partial-refund handling for the settlement API."
            ),
            owner_id="eng-001",
            status=TaskStatus.IN_REVIEW,
            priority=Priority.CRITICAL,
            created_at=_at(now, days=-21),
            updated_at=_at(now, days=-3),
            due_date=_at(now, days=-2),
            next_step="Manager approval of contract v3 is required before freeze.",
            required_skills=["api-design", "backend"],
            estimated_effort=24.0,
            remaining_effort=4.0,
            related_document_ids=["doc-001"],
        ),
        Task(
            id="pay-02",
            project_id=PROJECT_PAYMENTS,
            title="Implement settlement worker",
            description=(
                "Consume settlement events and write ledger entries using the "
                "approved API contract."
            ),
            owner_id="eng-008",
            status=TaskStatus.BLOCKED,
            priority=Priority.CRITICAL,
            created_at=_at(now, days=-18),
            updated_at=_at(now, days=-2),
            due_date=_at(now, days=2),
            dependency_ids=["pay-01"],
            blocked_reason=(
                "Partial-refund field semantics in the settlement API contract are "
                "still undecided, so the ledger write path cannot be finalised."
            ),
            next_step="Resume once contract v3 is approved; branch is ready to rebase.",
            required_skills=["backend", "python", "payments"],
            estimated_effort=40.0,
            remaining_effort=18.0,
            related_document_ids=["doc-001"],
        ),
        Task(
            id="pay-03",
            project_id=PROJECT_PAYMENTS,
            title="Settlement reconciliation UI",
            description="Operations view for reconciling settlement batches.",
            owner_id="eng-007",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.HIGH,
            created_at=_at(now, days=-14),
            updated_at=_at(now, days=-6),
            due_date=_at(now, days=6),
            dependency_ids=["pay-01", "pay-02"],
            required_skills=["frontend", "react"],
            estimated_effort=20.0,
            remaining_effort=20.0,
        ),
        Task(
            id="pay-04",
            project_id=PROJECT_PAYMENTS,
            title="Payment retry policy",
            description="Implement the agreed exponential backoff retry policy.",
            owner_id="eng-008",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=_at(now, days=-12),
            updated_at=_at(now, days=-3),
            due_date=_at(now, days=5),
            next_step="Benchmark backoff against the sandbox gateway.",
            required_skills=["backend", "python", "payments"],
            estimated_effort=16.0,
            remaining_effort=10.0,
            related_document_ids=["doc-003"],
        ),
        Task(
            id="pay-05",
            project_id=PROJECT_PAYMENTS,
            title="Checkout error states",
            description="Error and recovery states for declined and pending payments.",
            owner_id="eng-003",
            status=TaskStatus.BLOCKED,
            priority=Priority.HIGH,
            created_at=_at(now, days=-10),
            updated_at=_at(now, days=-1),
            due_date=_at(now, days=4),
            blocked_reason=(
                "The requirement for declined-card messaging is ambiguous: it is "
                "unclear whether the issuer reason code may be shown to customers."
            ),
            required_skills=["frontend", "react", "typescript"],
            estimated_effort=18.0,
            remaining_effort=12.0,
        ),
        Task(
            id="pay-06",
            project_id=PROJECT_PAYMENTS,
            title="Gateway sandbox load test",
            description="Load-test the retry path against the gateway sandbox.",
            owner_id="eng-009",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-9),
            updated_at=_at(now, days=-4),
            due_date=_at(now, days=9),
            dependency_ids=["pay-04"],
            required_skills=["sre", "kubernetes"],
            estimated_effort=12.0,
            remaining_effort=8.0,
        ),
        Task(
            id="pay-07",
            project_id=PROJECT_PAYMENTS,
            title="PCI scope review",
            description="Confirm which v2 components fall inside PCI scope.",
            owner_id=None,
            status=TaskStatus.NOT_STARTED,
            priority=Priority.HIGH,
            created_at=_at(now, days=-7),
            updated_at=_at(now, days=-7),
            due_date=_at(now, days=11),
            required_skills=["security"],
            required_permission="security_reviewer",
            estimated_effort=10.0,
            remaining_effort=10.0,
        ),
        Task(
            id="pay-08",
            project_id=PROJECT_PAYMENTS,
            title="Migrate ledger schema",
            description="Online migration of the ledger tables to the v2 schema.",
            owner_id="eng-002",
            status=TaskStatus.COMPLETED,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-35),
            updated_at=_at(now, days=-8),
            due_date=_at(now, days=-8),
            required_skills=["backend", "postgres"],
            estimated_effort=20.0,
            remaining_effort=0.0,
        ),
        # --- Identity -----------------------------------------------------
        Task(
            id="id-01",
            project_id=PROJECT_IDENTITY,
            title="OIDC provider integration",
            description="Integrate the hosted OIDC provider for the pilot teams.",
            owner_id="eng-006",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=_at(now, days=-30),
            updated_at=_at(now, days=-2),
            due_date=_at(now, days=7),
            next_step="Confirm token lifetime with the manager, then enable the pilot.",
            required_skills=["security", "oauth", "identity"],
            estimated_effort=30.0,
            remaining_effort=9.0,
            related_document_ids=["doc-004"],
        ),
        Task(
            id="id-02",
            project_id=PROJECT_IDENTITY,
            title="Session management service",
            description="Session issuance, refresh and revocation service.",
            owner_id="eng-004",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-26),
            updated_at=_at(now, days=-5),
            due_date=_at(now, days=10),
            dependency_ids=["id-01"],
            required_skills=["backend", "go"],
            estimated_effort=28.0,
            remaining_effort=14.0,
        ),
        Task(
            id="id-03",
            project_id=PROJECT_IDENTITY,
            title="Login UI refresh",
            description="Update the sign-in experience for the OIDC flow.",
            owner_id="eng-007",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-20),
            updated_at=_at(now, days=-20),
            due_date=_at(now, days=14),
            dependency_ids=["id-01"],
            required_skills=["frontend", "react"],
            estimated_effort=16.0,
            remaining_effort=16.0,
        ),
        Task(
            id="id-04",
            project_id=PROJECT_IDENTITY,
            title="SCIM user provisioning",
            description="Automate joiner/leaver provisioning through SCIM.",
            owner_id="eng-002",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-16),
            updated_at=_at(now, days=-16),
            due_date=_at(now, days=20),
            required_skills=["backend", "python"],
            estimated_effort=22.0,
            remaining_effort=22.0,
        ),
        Task(
            id="id-05",
            project_id=PROJECT_IDENTITY,
            title="Audit log retention policy",
            description="Define and implement retention for authentication logs.",
            owner_id="eng-006",
            status=TaskStatus.IN_REVIEW,
            priority=Priority.LOW,
            created_at=_at(now, days=-15),
            updated_at=_at(now, days=-3),
            due_date=_at(now, days=6),
            required_skills=["security"],
            estimated_effort=8.0,
            remaining_effort=2.0,
        ),
        Task(
            id="id-06",
            project_id=PROJECT_IDENTITY,
            title="Decommission legacy auth",
            description="Remove the legacy auth service once the pilot succeeds.",
            owner_id="eng-004",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.LOW,
            created_at=_at(now, days=-14),
            updated_at=_at(now, days=-14),
            due_date=_at(now, days=40),
            dependency_ids=["id-01", "id-02"],
            required_skills=["backend", "go"],
            estimated_effort=14.0,
            remaining_effort=14.0,
        ),
        # --- Insights -------------------------------------------------------
        Task(
            id="in-01",
            project_id=PROJECT_INSIGHTS,
            title="Event ingestion pipeline",
            description="Stream product events into the warehouse landing zone.",
            owner_id="eng-005",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=_at(now, days=-22),
            updated_at=_at(now, days=-2),
            due_date=_at(now, days=8),
            next_step="Finish the dead-letter queue handling.",
            required_skills=["data", "python", "dbt"],
            estimated_effort=34.0,
            remaining_effort=12.0,
            related_document_ids=["doc-005"],
        ),
        Task(
            id="in-02",
            project_id=PROJECT_INSIGHTS,
            title="Warehouse schema design",
            description="Dimensional model for customer and usage facts.",
            owner_id="eng-010",
            status=TaskStatus.IN_REVIEW,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-20),
            updated_at=_at(now, days=-4),
            due_date=_at(now, days=5),
            required_skills=["data", "spark"],
            estimated_effort=20.0,
            remaining_effort=4.0,
            related_document_ids=["doc-005"],
        ),
        Task(
            id="in-03",
            project_id=PROJECT_INSIGHTS,
            title="Daily aggregation jobs",
            description="Scheduled aggregation of usage facts for the dashboard.",
            owner_id="eng-005",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-12),
            updated_at=_at(now, days=-12),
            due_date=_at(now, days=15),
            dependency_ids=["in-01", "in-02"],
            required_skills=["data", "dbt"],
            estimated_effort=18.0,
            remaining_effort=18.0,
        ),
        Task(
            id="in-04",
            project_id=PROJECT_INSIGHTS,
            title="Insights dashboard",
            description="Customer-facing insights dashboard built on the aggregates.",
            owner_id="eng-003",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.MEDIUM,
            created_at=_at(now, days=-10),
            updated_at=_at(now, days=-10),
            due_date=_at(now, days=22),
            dependency_ids=["in-03"],
            required_skills=["frontend", "react"],
            estimated_effort=26.0,
            remaining_effort=26.0,
        ),
        Task(
            id="in-05",
            project_id=PROJECT_INSIGHTS,
            title="Data retention controls",
            description="Retention and deletion controls for customer event data.",
            owner_id="eng-010",
            status=TaskStatus.NOT_STARTED,
            priority=Priority.LOW,
            created_at=_at(now, days=-8),
            updated_at=_at(now, days=-8),
            due_date=_at(now, days=30),
            required_skills=["data", "python"],
            estimated_effort=12.0,
            remaining_effort=12.0,
        ),
    ]


def build_documents(now: datetime) -> list[ProjectDocument]:
    return [
        ProjectDocument(
            id="doc-001",
            project_id=PROJECT_PAYMENTS,
            task_ids=["pay-01", "pay-02"],
            title="Settlement API contract v3",
            doc_type="specification",
            url="https://docs.example.com/payments/settlement-api-v3",
            summary=(
                "Draft 3 of the settlement API. Open question: whether partial "
                "refunds are modelled as negative settlements or separate events."
            ),
            updated_at=_at(now, days=-3),
        ),
        ProjectDocument(
            id="doc-002",
            project_id=PROJECT_PAYMENTS,
            task_ids=["pay-02", "pay-04", "pay-06"],
            title="Payments v2 architecture overview",
            doc_type="reference",
            url="https://docs.example.com/payments/architecture-v2",
            summary="Component diagram and event flow for the v2 settlement pipeline.",
            updated_at=_at(now, days=-15),
        ),
        ProjectDocument(
            id="doc-003",
            project_id=PROJECT_PAYMENTS,
            task_ids=["pay-04"],
            title="Retry policy RFC",
            doc_type="rfc",
            url="https://docs.example.com/payments/retry-rfc",
            summary="Accepted RFC for exponential backoff with a five-attempt cap.",
            updated_at=_at(now, days=-6),
        ),
        ProjectDocument(
            id="doc-004",
            project_id=PROJECT_IDENTITY,
            task_ids=["id-01", "id-02"],
            title="OIDC pilot plan",
            doc_type="plan",
            url="https://docs.example.com/identity/oidc-pilot",
            summary="Rollout plan and success criteria for the two pilot teams.",
            updated_at=_at(now, days=-9),
        ),
        ProjectDocument(
            id="doc-005",
            project_id=PROJECT_INSIGHTS,
            task_ids=["in-01", "in-02", "in-03"],
            title="Insights data dictionary",
            doc_type="reference",
            url="https://docs.example.com/insights/data-dictionary",
            summary="Field-level definitions for the customer and usage fact tables.",
            updated_at=_at(now, days=-5),
        ),
    ]


def build_decisions(now: datetime) -> list[DecisionRecord]:
    return [
        DecisionRecord(
            id="dec-001",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-04",
            title="Retry backoff strategy",
            decision="Exponential backoff, capped at five attempts, jittered.",
            rationale="Matches the gateway's documented rate limits.",
            decided_by=MANAGER_ID,
            decided_at=_at(now, days=-6),
        ),
        DecisionRecord(
            id="dec-002",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-08",
            title="Ledger schema migration approach",
            decision="Online dual-write migration with a one-week verification window.",
            decided_by=MANAGER_ID,
            decided_at=_at(now, days=-12),
        ),
        DecisionRecord(
            id="dec-003",
            project_id=PROJECT_IDENTITY,
            task_id="id-01",
            title="Hosted login page for the pilot",
            decision="Use the provider-hosted login page for the pilot, not an embedded form.",
            rationale="Removes credential handling from our codebase during the pilot.",
            decided_by=MANAGER_ID,
            decided_at=_at(now, days=-9),
        ),
    ]


def build_task_updates(now: datetime) -> list[TaskUpdate]:
    return [
        TaskUpdate(
            id="upd-001",
            task_id="pay-01",
            author_id="eng-001",
            body=(
                "Contract v3 is ready for review. The only open item is partial "
                "refunds — I need a decision before the schemas can be frozen."
            ),
            created_at=_at(now, days=-3),
        ),
        TaskUpdate(
            id="upd-002",
            task_id="pay-02",
            author_id="eng-008",
            body=(
                "Consumer, deduplication and ledger write skeleton are done and "
                "unit tested against the v2 draft. Integration tests are stubbed."
            ),
            created_at=_at(now, days=-5),
        ),
        TaskUpdate(
            id="upd-003",
            task_id="pay-02",
            author_id="eng-008",
            body=(
                "Pausing here. The refund path depends on the contract decision; "
                "branch feature/settlement-worker is rebased on main and green."
            ),
            created_at=_at(now, days=-2),
        ),
        TaskUpdate(
            id="upd-004",
            task_id="pay-04",
            author_id="eng-008",
            body=(
                "Backoff implemented per the RFC. Still need the sandbox benchmark "
                "before enabling it in staging."
            ),
            created_at=_at(now, days=-3),
        ),
        TaskUpdate(
            id="upd-005",
            task_id="pay-05",
            author_id="eng-003",
            body=(
                "Built the generic decline state, but I cannot ship copy until we "
                "know whether issuer reason codes may be surfaced to customers."
            ),
            created_at=_at(now, days=-1),
        ),
        TaskUpdate(
            id="upd-006",
            task_id="id-01",
            author_id="eng-006",
            body="Provider sandbox is wired up; token lifetime is the last open choice.",
            created_at=_at(now, days=-2),
        ),
        TaskUpdate(
            id="upd-007",
            task_id="in-01",
            author_id="eng-005",
            body="Ingestion is running in staging; dead-letter handling is in progress.",
            created_at=_at(now, days=-2),
        ),
    ]


def build_requests(now: datetime) -> list[SupportRequest]:
    """Seeded support requests, including the 'lost approval' scenario."""
    return [
        SupportRequest(
            id="req-001",
            engineer_id="eng-001",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-01",
            category=RequestCategory.APPROVAL,
            title="Approve settlement API contract v3",
            description=(
                "Contract v3 is ready to freeze. I need a decision on whether "
                "partial refunds are modelled as negative settlements or as their "
                "own event type. The settlement worker cannot be finished until "
                "this is settled."
            ),
            priority=Priority.CRITICAL,
            status=RequestStatus.OPEN,
            assigned_owner_id=MANAGER_ID,
            created_at=_at(now, days=-3),
            updated_at=_at(now, days=-3),
            due_date=_at(now, days=-1),
        ),
        SupportRequest(
            id="req-002",
            engineer_id="eng-003",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-05",
            category=RequestCategory.BLOCKER,
            title="Declined-card messaging requirement is ambiguous",
            description=(
                "The spec says to 'show a helpful reason' for declined cards, but "
                "compliance guidance says issuer reason codes must not be shown to "
                "customers. I need one agreed rule before I can finish the error states."
            ),
            priority=Priority.HIGH,
            status=RequestStatus.OPEN,
            assigned_owner_id=MANAGER_ID,
            created_at=_at(now, days=-1),
            updated_at=_at(now, days=-1),
            due_date=_at(now, days=1),
        ),
        SupportRequest(
            id="req-003",
            engineer_id="eng-006",
            project_id=PROJECT_IDENTITY,
            task_id="id-01",
            category=RequestCategory.DECISION,
            title="Token lifetime for the OIDC pilot",
            description=(
                "Security prefers a 15-minute access token; the pilot teams want "
                "8 hours so they are not re-prompted. I need a decision to enable "
                "the pilot."
            ),
            priority=Priority.MEDIUM,
            status=RequestStatus.OPEN,
            assigned_owner_id=MANAGER_ID,
            created_at=_at(now, days=-2),
            updated_at=_at(now, days=-2),
        ),
        SupportRequest(
            id="req-004",
            engineer_id="eng-005",
            project_id=PROJECT_INSIGHTS,
            task_id="in-01",
            category=RequestCategory.ONE_ON_ONE,
            title="15 minutes on insights pipeline scope",
            description=(
                "I would like to confirm whether dead-letter replay is in scope for "
                "pipeline v1 or can wait."
            ),
            priority=Priority.LOW,
            status=RequestStatus.ACKNOWLEDGED,
            assigned_owner_id=MANAGER_ID,
            created_at=_at(now, days=-4),
            updated_at=_at(now, days=-3),
            responses=[
                RequestResponse(
                    author_id=MANAGER_ID,
                    body="Happy to. Put 15 minutes in on Thursday and bring the scope list.",
                    created_at=_at(now, days=-3),
                )
            ],
        ),
        SupportRequest(
            id="req-005",
            engineer_id="eng-002",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-08",
            category=RequestCategory.PROGRESS_UPDATE,
            title="Ledger schema migration complete",
            description="Dual-write migration finished and verified; no issues found.",
            priority=Priority.LOW,
            status=RequestStatus.RESOLVED,
            assigned_owner_id=MANAGER_ID,
            created_at=_at(now, days=-8),
            updated_at=_at(now, days=-8),
            resolution_notes="Confirmed. Thanks for the clean migration.",
        ),
    ]


def build_actions(now: datetime) -> list[ActionItem]:
    """Action items mirroring the seeded requests, plus a manager follow-up."""
    return [
        ActionItem(
            id="act-001",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-01",
            source_request_id="req-001",
            type=ActionType.APPROVAL,
            title="Approve settlement API contract v3",
            description=(
                "Arjun Mehta needs a decision on partial-refund modelling before "
                "the contract can be frozen."
            ),
            owner_id=MANAGER_ID,
            created_by="eng-001",
            created_at=_at(now, days=-3),
            updated_at=_at(now, days=-3),
            due_date=_at(now, days=-1),
            status=ActionStatus.OPEN,
            priority=Priority.CRITICAL,
        ),
        ActionItem(
            id="act-002",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-05",
            source_request_id="req-002",
            type=ActionType.BLOCKER,
            title="Declined-card messaging requirement is ambiguous",
            description=(
                "Diego Alvarez is blocked on whether issuer reason codes may be "
                "shown to customers."
            ),
            owner_id=MANAGER_ID,
            created_by="eng-003",
            created_at=_at(now, days=-1),
            updated_at=_at(now, days=-1),
            due_date=_at(now, days=1),
            status=ActionStatus.OPEN,
            priority=Priority.HIGH,
        ),
        ActionItem(
            id="act-003",
            project_id=PROJECT_IDENTITY,
            task_id="id-01",
            source_request_id="req-003",
            type=ActionType.QUESTION,
            title="Token lifetime for the OIDC pilot",
            description="Nora Haddad needs a decision between a 15-minute and an 8-hour token.",
            owner_id=MANAGER_ID,
            created_by="eng-006",
            created_at=_at(now, days=-2),
            updated_at=_at(now, days=-2),
            status=ActionStatus.OPEN,
            priority=Priority.MEDIUM,
        ),
        ActionItem(
            id="act-004",
            project_id=PROJECT_INSIGHTS,
            task_id="in-01",
            source_request_id="req-004",
            type=ActionType.ONE_ON_ONE,
            title="15 minutes on insights pipeline scope",
            description="Samuel Okafor asked for a short scope conversation.",
            owner_id=MANAGER_ID,
            created_by="eng-005",
            created_at=_at(now, days=-4),
            updated_at=_at(now, days=-3),
            status=ActionStatus.ACKNOWLEDGED,
            priority=Priority.LOW,
        ),
        ActionItem(
            id="act-005",
            project_id=PROJECT_PAYMENTS,
            task_id="pay-07",
            type=ActionType.FOLLOW_UP,
            title="Find an owner for the PCI scope review",
            description=(
                "PCI scope review is unassigned and needs a security reviewer "
                "before the v2 release."
            ),
            owner_id=MANAGER_ID,
            created_by=MANAGER_ID,
            created_at=_at(now, days=-5),
            updated_at=_at(now, days=-5),
            due_date=_at(now, days=4),
            status=ActionStatus.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]


def build_notifications(now: datetime) -> list[Notification]:
    """Notifications matching the seeded actions, with the same dedup keys the
    notification service would have produced, so sweeps stay idempotent."""
    return [
        Notification(
            id="ntf-seed-001",
            recipient_id=MANAGER_ID,
            type=NotificationType.APPROVAL_REQUESTED,
            title="Approve settlement API contract v3",
            message=(
                "Arjun Mehta needs a decision on partial-refund modelling before "
                "the contract can be frozen."
            ),
            reason="An approval is waiting on you.",
            suggested_action="Open the action and record a decision.",
            priority=Priority.CRITICAL,
            related_entity_type="action_item",
            related_entity_id="act-001",
            created_at=_at(now, days=-3),
            deduplication_key=attention_key("action_item", "act-001", MANAGER_ID),
        ),
        Notification(
            id="ntf-seed-002",
            recipient_id=MANAGER_ID,
            type=NotificationType.BLOCKER_REPORTED,
            title="Declined-card messaging requirement is ambiguous",
            message="Diego Alvarez is blocked on the declined-card messaging rule.",
            reason="A blocker is waiting on you.",
            suggested_action="Open the action and record a decision.",
            priority=Priority.HIGH,
            related_entity_type="action_item",
            related_entity_id="act-002",
            created_at=_at(now, days=-1),
            deduplication_key=attention_key("action_item", "act-002", MANAGER_ID),
        ),
        Notification(
            id="ntf-seed-003",
            recipient_id="eng-005",
            type=NotificationType.REQUEST_RESPONDED,
            title="Response on: 15 minutes on insights pipeline scope",
            message="Happy to. Put 15 minutes in on Thursday and bring the scope list.",
            reason="Priya Raman responded to your request.",
            suggested_action="Open the request to read the response.",
            priority=Priority.LOW,
            related_entity_type="support_request",
            related_entity_id="req-004",
            created_at=_at(now, days=-3),
            read_at=_at(now, days=-3, hours=2),
            deduplication_key=make_dedup_key(
                event="request_responded",
                entity_type="support_request",
                entity_id="req-004",
                recipient_id="eng-005",
                discriminator="1",
            ),
        ),
    ]


def seed(database: Database, *, reset: bool = True, now: datetime | None = None) -> dict[str, int]:
    """Populate the workspace with the demo organisation.

    ``reset=True`` wipes the known collections first. The caller is responsible
    for ensuring this is never run against real data — the HTTP route that
    exposes it is disabled outside local/staging.
    """
    now = now or utc_now()
    if reset:
        database.clear_all()

    users = build_users(now)
    projects = build_projects(now)
    milestones = build_milestones(now)
    tasks = build_tasks(now)
    documents = build_documents(now)
    decisions = build_decisions(now)
    updates = build_task_updates(now)
    requests = build_requests(now)
    actions = build_actions(now)
    notifications = build_notifications(now)

    # Keep tasks' back-references to their requests consistent.
    requests_by_task: dict[str, list[str]] = {}
    for request in requests:
        if request.task_id:
            requests_by_task.setdefault(request.task_id, []).append(request.id)
    tasks = [
        task.model_copy(update={"related_request_ids": requests_by_task.get(task.id, [])})
        for task in tasks
    ]

    database.users.save_many(users)
    database.projects.save_many(projects)
    database.milestones.save_many(milestones)
    database.tasks.save_many(tasks)
    database.documents.save_many(documents)
    database.decisions.save_many(decisions)
    database.task_updates.save_many(updates)
    database.requests.save_many(requests)
    database.actions.save_many(actions)
    database.notifications.save_many(notifications)

    return {
        "users": len(users),
        "projects": len(projects),
        "milestones": len(milestones),
        "tasks": len(tasks),
        "documents": len(documents),
        "decisions": len(decisions),
        "task_updates": len(updates),
        "support_requests": len(requests),
        "action_items": len(actions),
        "notifications": len(notifications),
    }
