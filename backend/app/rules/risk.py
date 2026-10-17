"""Deterministic delivery-risk detection.

Design rule: a finding is only produced from *explicit* signals — a missed
due date, a recorded blocker, an unresolved dependency, a pending approval, an
approaching milestone. Task age on its own is never a risk signal and is never
attributed to the task's owner. See ``tests/test_risk_rules.py``.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import days_until, hours_between, utc_now
from app.models.enums import (
    PRIORITY_WEIGHT,
    ActionType,
    Priority,
    ProjectHealth,
    RiskKind,
    TaskStatus,
)
from app.rules.dependencies import DependencyGraph
from app.schemas.analysis import (
    Evidence,
    MilestoneStatus,
    ProjectHealthReport,
    RiskFinding,
)
from app.schemas.domain import ActionItem, Milestone, Project, SupportRequest, Task

# A milestone inside this horizon amplifies the severity of nearby problems.
MILESTONE_HORIZON_DAYS = 14.0
# Diminishing weights applied to the findings, worst first, when scoring health.
# Findings beyond the fourth do not reduce the score further: by then the
# project is already reported as at risk and the detail is in the finding list.
HEALTH_PENALTY_WEIGHTS = (0.50, 0.25, 0.15, 0.10)
# Approval-shaped action types that can hold up downstream work.
DECISION_ACTION_TYPES = frozenset(
    {ActionType.APPROVAL, ActionType.QUESTION, ActionType.BLOCKER}
)


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _task_evidence(task: Task, detail: str) -> Evidence:
    return Evidence(
        label=task.title, detail=detail, entity_type="task", entity_id=task.id
    )


def _milestone_pressure(
    milestones: list[Milestone], now: datetime
) -> tuple[float, list[Milestone]]:
    """Severity bonus and the milestones driving it."""
    imminent = [
        milestone
        for milestone in milestones
        if not milestone.completed
        and (days_until(milestone.target_date, now=now) or 999) <= MILESTONE_HORIZON_DAYS
    ]
    if not imminent:
        return 0.0, []
    closest = min(
        imminent, key=lambda m: days_until(m.target_date, now=now) or MILESTONE_HORIZON_DAYS
    )
    remaining = days_until(closest.target_date, now=now) or MILESTONE_HORIZON_DAYS
    # Linear ramp: 0 points at the horizon, 25 points on/after the target date.
    bonus = 25.0 * max(0.0, (MILESTONE_HORIZON_DAYS - remaining) / MILESTONE_HORIZON_DAYS)
    return bonus, imminent


def _milestones_for_tasks(
    milestones: list[Milestone], task_ids: set[str]
) -> list[Milestone]:
    return [
        milestone
        for milestone in milestones
        if task_ids.intersection(milestone.task_ids) and not milestone.completed
    ]


def detect_project_risks(
    *,
    project: Project,
    tasks: list[Task],
    graph: DependencyGraph,
    milestones: list[Milestone],
    requests: list[SupportRequest],
    actions: list[ActionItem],
    now: datetime | None = None,
) -> list[RiskFinding]:
    """Produce every risk finding for one project, highest severity first."""
    now = now or utc_now()
    findings: list[RiskFinding] = []
    project_milestones = [m for m in milestones if m.project_id == project.id]

    for task in tasks:
        if not task.is_open:
            continue
        downstream = graph.downstream(task.id)
        downstream_ids = [item.id for item in downstream]
        critical_downstream = [
            item
            for item in downstream
            if item.priority in (Priority.HIGH, Priority.CRITICAL)
        ]
        related_milestones = _milestones_for_tasks(
            project_milestones, {task.id, *downstream_ids}
        )
        milestone_bonus, _ = _milestone_pressure(related_milestones, now)
        priority_bonus = PRIORITY_WEIGHT[task.priority] * 6.0
        downstream_bonus = min(24.0, len(downstream) * 8.0 + len(critical_downstream) * 4.0)

        # --- Rule 1: the due date has passed -------------------------------
        overdue_days = -(days_until(task.due_date, now=now) or 0.0)
        if task.due_date is not None and overdue_days > 0:
            severity = _clamp(
                30 + min(30.0, overdue_days * 5.0)
                + priority_bonus
                + downstream_bonus
                + milestone_bonus
            )
            evidence = [
                _task_evidence(
                    task,
                    f"Due {task.due_date.date().isoformat()}, "
                    f"{overdue_days:.1f} days past the deadline.",
                ),
                Evidence(
                    label="Current status",
                    detail=f"Status is '{task.status.value}', priority '{task.priority.value}'.",
                    entity_type="task",
                    entity_id=task.id,
                ),
            ]
            evidence += [
                _task_evidence(item, "Waiting on the overdue task.")
                for item in downstream[:5]
            ]
            findings.append(
                RiskFinding(
                    id=f"risk-overdue-{task.id}",
                    kind=RiskKind.OVERDUE_TASK,
                    severity=severity,
                    title=f"Overdue: {task.title}",
                    summary=(
                        f"{task.title} passed its due date "
                        f"{overdue_days:.0f} day(s) ago and is still open."
                    ),
                    project_id=project.id,
                    task_ids=[task.id],
                    downstream_task_ids=downstream_ids,
                    milestone_ids=[m.id for m in related_milestones],
                    evidence=evidence,
                    suggested_actions=_overdue_suggestions(task, downstream),
                )
            )

        # --- Rule 2: an explicitly recorded blocker ------------------------
        if task.status is TaskStatus.BLOCKED:
            severity = _clamp(
                35 + priority_bonus + downstream_bonus + milestone_bonus
            )
            kind = (
                RiskKind.BLOCKED_DEPENDENCY_CHAIN
                if downstream
                else RiskKind.BLOCKED_TASK
            )
            evidence = [
                _task_evidence(
                    task,
                    task.blocked_reason
                    or "Marked blocked without a recorded reason.",
                )
            ]
            evidence += [
                _task_evidence(item, "Downstream work waiting on this blocker.")
                for item in downstream[:5]
            ]
            blocking = graph.blocking_dependencies(task.id)
            evidence += [
                _task_evidence(item, "Incomplete dependency of the blocked task.")
                for item in blocking[:5]
            ]
            related_request_ids = [
                request.id
                for request in requests
                if request.task_id == task.id and request.is_open
            ]
            findings.append(
                RiskFinding(
                    id=f"risk-blocked-{task.id}",
                    kind=kind,
                    severity=severity,
                    title=f"Blocked: {task.title}",
                    summary=(
                        f"{task.title} is blocked"
                        + (f" and {len(downstream)} task(s) depend on it." if downstream
                           else " with no recorded downstream dependency.")
                    ),
                    project_id=project.id,
                    task_ids=[task.id],
                    downstream_task_ids=downstream_ids,
                    milestone_ids=[m.id for m in related_milestones],
                    request_ids=related_request_ids,
                    evidence=evidence,
                    suggested_actions=_blocked_suggestions(task, downstream, blocking),
                )
            )

        # --- Rule 3: high-priority work with no owner ----------------------
        if task.owner_id is None and task.priority in (Priority.HIGH, Priority.CRITICAL):
            findings.append(
                RiskFinding(
                    id=f"risk-unassigned-{task.id}",
                    kind=RiskKind.UNASSIGNED_CRITICAL_WORK,
                    severity=_clamp(25 + priority_bonus + milestone_bonus),
                    title=f"Unassigned {task.priority.value} work: {task.title}",
                    summary=f"{task.title} has no owner.",
                    project_id=project.id,
                    task_ids=[task.id],
                    downstream_task_ids=downstream_ids,
                    milestone_ids=[m.id for m in related_milestones],
                    evidence=[_task_evidence(task, "No owner_id is set on this task.")],
                    suggested_actions=["Assign an owner before the next milestone."],
                )
            )

    findings += _detect_pending_decision_risks(
        project=project,
        graph=graph,
        milestones=project_milestones,
        requests=requests,
        actions=actions,
        now=now,
    )
    findings += _detect_milestone_risks(
        project=project, tasks=tasks, milestones=project_milestones, now=now
    )

    findings.sort(key=lambda finding: (-finding.severity, finding.id))
    return findings


def _overdue_suggestions(task: Task, downstream: list[Task]) -> list[str]:
    suggestions = [
        f"Ask {task.owner_id or 'the project team'} for a revised date and the current next step."
    ]
    if downstream:
        suggestions.append(
            f"Check whether {len(downstream)} dependent task(s) can start with partial output."
        )
    if task.next_step:
        suggestions.append(f"Recorded next step: {task.next_step}")
    return suggestions


def _blocked_suggestions(
    task: Task, downstream: list[Task], blocking: list[Task]
) -> list[str]:
    suggestions: list[str] = []
    if blocking:
        suggestions.append(
            "Unblock the upstream dependency: "
            + ", ".join(item.title for item in blocking[:3])
        )
    if task.blocked_reason:
        suggestions.append(f"Resolve the recorded blocker: {task.blocked_reason}")
    else:
        suggestions.append("Ask the owner to record why the task is blocked.")
    if downstream:
        suggestions.append(
            f"Re-sequence or re-scope {len(downstream)} dependent task(s) if the blocker persists."
        )
    return suggestions


def _detect_pending_decision_risks(
    *,
    project: Project,
    graph: DependencyGraph,
    milestones: list[Milestone],
    requests: list[SupportRequest],
    actions: list[ActionItem],
    now: datetime,
) -> list[RiskFinding]:
    """Pending approvals and questions that hold up other work."""
    findings: list[RiskFinding] = []
    request_index = {request.id: request for request in requests}

    for action in actions:
        if not action.is_open or action.type not in DECISION_ACTION_TYPES:
            continue
        if action.project_id != project.id:
            continue
        task = graph.get(action.task_id) if action.task_id else None
        downstream = graph.downstream(task.id) if task else []
        if task is None and not downstream:
            continue

        waiting_hours = hours_between(action.created_at, now)
        related_milestones = _milestones_for_tasks(
            milestones, {task.id for task in ([task] if task else []) + downstream}
        )
        milestone_bonus, imminent = _milestone_pressure(related_milestones, now)
        # Blocking downstream work is the main driver; waiting time is secondary.
        severity = _clamp(
            20
            + PRIORITY_WEIGHT[action.priority] * 6.0
            + min(20.0, len(downstream) * 10.0)
            + min(15.0, waiting_hours / 12.0)
            + milestone_bonus
        )

        evidence: list[Evidence] = [
            Evidence(
                label=action.title,
                detail=f"Open for {waiting_hours / 24:.1f} day(s) awaiting {action.owner_id}.",
                entity_type="action_item",
                entity_id=action.id,
            )
        ]
        if task is not None:
            evidence.append(_task_evidence(task, "The task this decision belongs to."))
        for item in downstream[:5]:
            evidence.append(
                _task_evidence(item, "Cannot proceed until the decision is recorded.")
            )
        for milestone in imminent[:3]:
            remaining = days_until(milestone.target_date, now=now) or 0.0
            evidence.append(
                Evidence(
                    label=milestone.name,
                    detail=f"Milestone target in {remaining:.1f} day(s).",
                    entity_type="milestone",
                    entity_id=milestone.id,
                )
            )

        source_request = (
            request_index.get(action.source_request_id)
            if action.source_request_id
            else None
        )
        findings.append(
            RiskFinding(
                id=f"risk-pending-{action.id}",
                kind=RiskKind.PENDING_APPROVAL_BLOCKING_WORK,
                severity=severity,
                title=f"Pending decision: {action.title}",
                summary=(
                    f"{action.title} has been waiting {waiting_hours / 24:.1f} day(s)"
                    + (f" and blocks {len(downstream)} task(s)." if downstream else ".")
                ),
                project_id=project.id,
                task_ids=[task.id] if task else [],
                downstream_task_ids=[item.id for item in downstream],
                milestone_ids=[milestone.id for milestone in related_milestones],
                action_ids=[action.id],
                request_ids=[source_request.id] if source_request else [],
                evidence=evidence,
                suggested_actions=[
                    "Review and record the decision on the action item.",
                    "Delegate to an authorised technical approver if you cannot review it today.",
                ],
            )
        )
    return findings


def _detect_milestone_risks(
    *,
    project: Project,
    tasks: list[Task],
    milestones: list[Milestone],
    now: datetime,
) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    task_index = {task.id: task for task in tasks}
    for milestone in milestones:
        if milestone.completed:
            continue
        status = summarise_milestone(milestone, task_index, now)
        if not status.at_risk:
            continue
        severity = _clamp(
            30
            + min(30.0, max(0.0, MILESTONE_HORIZON_DAYS - status.days_remaining) * 2.0)
            + status.blocked_tasks * 8.0
            + status.overdue_tasks * 8.0
        )
        evidence = [
            Evidence(
                label=milestone.name,
                detail=(
                    f"Target {milestone.target_date.date().isoformat()} "
                    f"({status.days_remaining:.1f} days away). "
                    f"{status.completed_tasks}/{status.total_tasks} tasks complete."
                ),
                entity_type="milestone",
                entity_id=milestone.id,
            )
        ]
        for task_id in milestone.task_ids:
            task = task_index.get(task_id)
            if task is None or not task.is_open:
                continue
            evidence.append(
                _task_evidence(
                    task, f"Open with status '{task.status.value}' before the milestone."
                )
            )
        findings.append(
            RiskFinding(
                id=f"risk-milestone-{milestone.id}",
                kind=RiskKind.MILESTONE_AT_RISK,
                severity=severity,
                title=f"Milestone at risk: {milestone.name}",
                summary="; ".join(status.reasons),
                project_id=project.id,
                task_ids=[
                    task_id
                    for task_id in milestone.task_ids
                    if task_id in task_index and task_index[task_id].is_open
                ],
                milestone_ids=[milestone.id],
                evidence=evidence[:8],
                suggested_actions=[
                    "Confirm scope for the milestone and decide what can move out.",
                    "Clear the blockers on the remaining tasks or extend the target date.",
                ],
            )
        )
    return findings


def summarise_milestone(
    milestone: Milestone, task_index: dict[str, Task], now: datetime
) -> MilestoneStatus:
    related = [task_index[tid] for tid in milestone.task_ids if tid in task_index]
    completed = [task for task in related if task.status is TaskStatus.COMPLETED]
    blocked = [task for task in related if task.status is TaskStatus.BLOCKED]
    overdue = [
        task
        for task in related
        if task.is_open
        and task.due_date is not None
        and (days_until(task.due_date, now=now) or 0.0) < 0
    ]
    days_remaining = days_until(milestone.target_date, now=now) or 0.0

    reasons: list[str] = []
    if blocked:
        reasons.append(f"{len(blocked)} blocked task(s) in scope")
    if overdue:
        reasons.append(f"{len(overdue)} overdue task(s) in scope")
    incomplete = len(related) - len(completed)
    if days_remaining <= MILESTONE_HORIZON_DAYS and incomplete:
        reasons.append(
            f"{incomplete} of {len(related)} task(s) still open with "
            f"{days_remaining:.1f} day(s) to the target"
        )
    if days_remaining < 0 and incomplete:
        reasons.append("Target date has already passed")

    at_risk = bool(blocked or overdue) or (
        days_remaining <= MILESTONE_HORIZON_DAYS and incomplete > 0
    )
    return MilestoneStatus(
        milestone_id=milestone.id,
        name=milestone.name,
        target_date=milestone.target_date,
        days_remaining=round(days_remaining, 2),
        total_tasks=len(related),
        completed_tasks=len(completed),
        blocked_tasks=len(blocked),
        overdue_tasks=len(overdue),
        at_risk=at_risk,
        reasons=reasons or ["On track against recorded task statuses"],
    )


def build_project_health(
    *,
    project: Project,
    tasks: list[Task],
    graph: DependencyGraph,
    milestones: list[Milestone],
    requests: list[SupportRequest],
    actions: list[ActionItem],
    now: datetime | None = None,
) -> ProjectHealthReport:
    now = now or utc_now()
    risks = detect_project_risks(
        project=project,
        tasks=tasks,
        graph=graph,
        milestones=milestones,
        requests=requests,
        actions=actions,
        now=now,
    )
    task_index = {task.id: task for task in tasks}
    project_milestones = [m for m in milestones if m.project_id == project.id]
    milestone_statuses = [
        summarise_milestone(milestone, task_index, now)
        for milestone in sorted(project_milestones, key=lambda m: m.target_date)
    ]
    upcoming = [status for status in milestone_statuses if status.days_remaining >= 0]

    completed = sum(1 for t in tasks if t.status is TaskStatus.COMPLETED)
    in_progress = sum(1 for t in tasks if t.status is TaskStatus.IN_PROGRESS)
    blocked = sum(1 for t in tasks if t.status is TaskStatus.BLOCKED)
    overdue = sum(
        1
        for t in tasks
        if t.is_open and t.due_date and (days_until(t.due_date, now=now) or 0.0) < 0
    )

    # Health starts at 100 and is reduced by the most severe findings with
    # diminishing weight: the worst problem dominates, and each additional one
    # adds less. Summing them equally saturated the score at zero on any project
    # with several findings, which hid the difference between bad and worse.
    health_score = _clamp(
        100 - sum(
            finding.severity * weight
            for finding, weight in zip(risks, HEALTH_PENALTY_WEIGHTS, strict=False)
        )
    )
    if health_score >= 75:
        health = ProjectHealth.ON_TRACK
    elif health_score >= 50:
        health = ProjectHealth.NEEDS_ATTENTION
    else:
        health = ProjectHealth.AT_RISK

    headline = (
        risks[0].summary
        if risks
        else "No blockers, overdue tasks or pending decisions recorded."
    )

    return ProjectHealthReport(
        project_id=project.id,
        project_name=project.name,
        health=health,
        health_score=health_score,
        total_tasks=len(tasks),
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        blocked_tasks=blocked,
        overdue_tasks=overdue,
        open_requests=sum(1 for r in requests if r.project_id == project.id and r.is_open),
        open_actions=sum(1 for a in actions if a.project_id == project.id and a.is_open),
        next_milestone=upcoming[0] if upcoming else None,
        milestones=milestone_statuses,
        risks=risks,
        headline=headline,
    )
