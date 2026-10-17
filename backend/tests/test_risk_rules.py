"""Deterministic risk detection.

Covers requirement 3 (a blocked task with downstream dependencies is
identified) and requirement 4 (task age alone is never treated as a problem,
and never attributed to the owner).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.models.enums import Priority, RiskKind, TaskStatus
from app.rules.dependencies import DependencyGraph
from app.rules.risk import build_project_health, detect_project_risks
from app.schemas.domain import Task

from tests.conftest import FROZEN_NOW


@pytest.fixture
def payments_findings(database):
    project = database.projects.require("proj-payments")
    tasks = database.tasks.find(lambda task: task.project_id == "proj-payments")
    return detect_project_risks(
        project=project,
        tasks=tasks,
        graph=DependencyGraph(database.tasks.list_all()),
        milestones=database.milestones.list_all(),
        requests=database.requests.list_all(),
        actions=database.actions.list_all(),
        now=FROZEN_NOW,
    )


def test_blocked_task_with_downstream_dependencies_is_identified(payments_findings):
    finding = next(
        item for item in payments_findings if item.id == "risk-blocked-pay-02"
    )
    assert finding.kind is RiskKind.BLOCKED_DEPENDENCY_CHAIN
    # pay-03 depends on pay-02 and must be named as downstream.
    assert "pay-03" in finding.downstream_task_ids
    # The milestone three days out must be linked.
    assert "ms-pay-1" in finding.milestone_ids
    # Evidence must carry the recorded blocker reason, not a guess.
    details = " ".join(item.detail for item in finding.evidence)
    assert "partial-refund" in details.lower()
    assert finding.severity >= 60


def test_overdue_task_is_identified_with_evidence(payments_findings):
    finding = next(item for item in payments_findings if item.id == "risk-overdue-pay-01")
    assert finding.kind is RiskKind.OVERDUE_TASK
    assert finding.task_ids == ["pay-01"]
    assert {"pay-02", "pay-03"} <= set(finding.downstream_task_ids)
    assert any("past the deadline" in item.detail for item in finding.evidence)


def test_pending_approval_blocking_work_is_identified(payments_findings):
    finding = next(item for item in payments_findings if item.id == "risk-pending-act-001")
    assert finding.kind is RiskKind.PENDING_APPROVAL_BLOCKING_WORK
    assert finding.action_ids == ["act-001"]
    assert "req-001" in finding.request_ids
    assert "pay-02" in finding.downstream_task_ids
    assert any("Milestone target" in item.detail for item in finding.evidence)


def test_unassigned_high_priority_work_is_identified(payments_findings):
    finding = next(item for item in payments_findings if item.id == "risk-unassigned-pay-07")
    assert finding.kind is RiskKind.UNASSIGNED_CRITICAL_WORK


def test_milestone_at_risk_is_identified(payments_findings):
    finding = next(item for item in payments_findings if item.id == "risk-milestone-ms-pay-1")
    assert finding.kind is RiskKind.MILESTONE_AT_RISK
    assert "blocked task(s) in scope" in finding.summary


def test_task_age_alone_produces_no_finding_and_no_owner_judgement(database):
    """Requirement 4.

    A task that has existed for a year but has no deadline, no blocker and no
    dependents must not produce any finding, and nothing in the output may
    characterise its owner.
    """
    project = database.projects.require("proj-insights")
    old_task = Task(
        id="in-old",
        project_id="proj-insights",
        title="Long-running research spike",
        description="Open-ended investigation with no deadline.",
        owner_id="eng-005",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        created_at=FROZEN_NOW - timedelta(days=365),
        updated_at=FROZEN_NOW - timedelta(days=200),
        due_date=None,
    )
    database.tasks.save(old_task)

    findings = detect_project_risks(
        project=project,
        tasks=[old_task],
        graph=DependencyGraph([old_task]),
        milestones=[],
        requests=[],
        actions=[],
        now=FROZEN_NOW,
    )
    assert findings == []

    # And the project report must not degrade because of the task's age.
    report = build_project_health(
        project=project,
        tasks=[old_task],
        graph=DependencyGraph([old_task]),
        milestones=[],
        requests=[],
        actions=[],
        now=FROZEN_NOW,
    )
    assert report.health_score == 100
    assert "eng-005" not in report.headline


def test_age_becomes_a_finding_only_when_a_deadline_is_missed(database):
    """The same task with a passed due date *is* reported — on the deadline,
    not on the owner."""
    project = database.projects.require("proj-insights")
    task = Task(
        id="in-old-2",
        project_id="proj-insights",
        title="Spike with a deadline",
        description="Same age, but with a recorded due date.",
        owner_id="eng-005",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        created_at=FROZEN_NOW - timedelta(days=365),
        updated_at=FROZEN_NOW - timedelta(days=200),
        due_date=FROZEN_NOW - timedelta(days=3),
    )
    findings = detect_project_risks(
        project=project,
        tasks=[task],
        graph=DependencyGraph([task]),
        milestones=[],
        requests=[],
        actions=[],
        now=FROZEN_NOW,
    )
    assert [item.kind for item in findings] == [RiskKind.OVERDUE_TASK]
    assert "3 day(s) ago" in findings[0].summary


def test_project_health_degrades_with_findings(database):
    project = database.projects.require("proj-payments")
    report = build_project_health(
        project=project,
        tasks=database.tasks.find(lambda t: t.project_id == "proj-payments"),
        graph=DependencyGraph(database.tasks.list_all()),
        milestones=database.milestones.list_all(),
        requests=database.requests.list_all(),
        actions=database.actions.list_all(),
        now=FROZEN_NOW,
    )
    assert report.health.value in {"at_risk", "needs_attention"}
    assert report.blocked_tasks == 2
    assert report.overdue_tasks == 1
    assert report.next_milestone is not None
    assert report.next_milestone.milestone_id == "ms-pay-1"
    assert report.next_milestone.at_risk is True


def test_health_score_does_not_saturate_with_many_findings(database):
    """Several findings must still leave a score that distinguishes degrees.

    Summing the top findings equally pinned every troubled project at zero,
    which hid the difference between 'bad' and 'worse'.
    """
    graph = DependencyGraph(database.tasks.list_all())

    def health_for(project_id: str):
        return build_project_health(
            project=database.projects.require(project_id),
            tasks=database.tasks.find(lambda t: t.project_id == project_id),
            graph=graph,
            milestones=database.milestones.list_all(),
            requests=database.requests.list_all(),
            actions=database.actions.list_all(),
            now=FROZEN_NOW,
        )

    payments = health_for("proj-payments")
    identity = health_for("proj-identity")
    insights = health_for("proj-insights")

    # The worst project has eight findings including a severity-100 one, and is
    # still scored above the floor.
    assert len(payments.risks) >= 6
    assert payments.risks[0].severity == 100
    assert 0 < payments.health_score < 25
    # And the three projects remain ordered and distinguishable.
    assert payments.health_score < identity.health_score < insights.health_score
    assert insights.health_score == 100
