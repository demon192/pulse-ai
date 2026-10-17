"""Deterministic prioritisation of manager action items.

Gemini never changes these numbers. It is only asked to explain them.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import days_until, hours_between, utc_now
from app.models.enums import PRIORITY_WEIGHT, ActionType, Priority
from app.rules.dependencies import DependencyGraph
from app.schemas.analysis import ActionPriority, PriorityFactor
from app.schemas.domain import ActionItem, Milestone

MILESTONE_HORIZON_DAYS = 14.0

BUCKET_URGENT = "urgent"
BUCKET_BLOCKED_WORK = "blocked_work"
BUCKET_APPROVAL = "approvals"
BUCKET_SUPPORT = "support"
BUCKET_ROUTINE = "routine"

def score_action(
    action: ActionItem,
    *,
    graph: DependencyGraph,
    milestones: list[Milestone],
    now: datetime | None = None,
) -> ActionPriority:
    now = now or utc_now()
    factors: list[PriorityFactor] = []

    # --- Explicit urgency ------------------------------------------------
    urgency_points = PRIORITY_WEIGHT[action.priority] * 7.5
    factors.append(
        PriorityFactor(
            factor="explicit_urgency",
            points=urgency_points,
            detail=f"Recorded priority is '{action.priority.value}'.",
        )
    )

    # --- Time remaining before the action's own deadline ------------------
    remaining = days_until(action.due_date, now=now)
    if remaining is not None:
        if remaining < 0:
            deadline_points = min(30.0, 18.0 + abs(remaining) * 4.0)
            detail = f"Overdue by {abs(remaining):.1f} day(s)."
        else:
            deadline_points = max(0.0, 18.0 - remaining * 3.0)
            detail = f"Due in {remaining:.1f} day(s)."
        factors.append(
            PriorityFactor(
                factor="deadline_proximity", points=deadline_points, detail=detail
            )
        )

    # --- Does it block other work? ---------------------------------------
    blocked_task_ids: list[str] = []
    critical_downstream = 0
    if action.task_id:
        downstream = graph.downstream(action.task_id)
        blocked_task_ids = [task.id for task in downstream]
        critical_downstream = sum(
            1
            for task in downstream
            if task.priority in (Priority.HIGH, Priority.CRITICAL)
        )
        if downstream:
            blocking_points = min(25.0, 10.0 + len(downstream) * 5.0)
            factors.append(
                PriorityFactor(
                    factor="blocks_downstream_work",
                    points=blocking_points,
                    detail=(
                        f"{len(downstream)} task(s) depend on this, "
                        f"{critical_downstream} of them high or critical priority."
                    ),
                )
            )
        else:
            own_task = graph.get(action.task_id)
            if own_task is not None and own_task.status.value == "blocked":
                factors.append(
                    PriorityFactor(
                        factor="blocks_downstream_work",
                        points=8.0,
                        detail="The linked task is itself recorded as blocked.",
                    )
                )

    # --- Milestone proximity ---------------------------------------------
    affected_task_ids = set(blocked_task_ids) | ({action.task_id} if action.task_id else set())
    affected_milestones = [
        milestone
        for milestone in milestones
        if not milestone.completed
        and affected_task_ids.intersection(milestone.task_ids)
        and (days_until(milestone.target_date, now=now) or 999) <= MILESTONE_HORIZON_DAYS
    ]
    if affected_milestones:
        closest = min(
            affected_milestones,
            key=lambda m: days_until(m.target_date, now=now) or MILESTONE_HORIZON_DAYS,
        )
        closest_days = days_until(closest.target_date, now=now) or 0.0
        milestone_points = max(
            0.0,
            20.0 * (MILESTONE_HORIZON_DAYS - closest_days) / MILESTONE_HORIZON_DAYS,
        )
        factors.append(
            PriorityFactor(
                factor="milestone_proximity",
                points=milestone_points,
                detail=f"'{closest.name}' is {closest_days:.1f} day(s) away.",
            )
        )

    # --- Time already spent waiting ---------------------------------------
    waiting_hours = hours_between(action.created_at, now)
    waiting_points = min(15.0, waiting_hours / 16.0)
    factors.append(
        PriorityFactor(
            factor="time_waiting",
            points=waiting_points,
            detail=f"Open for {waiting_hours / 24:.1f} day(s).",
        )
    )

    score = round(sum(factor.points for factor in factors), 2)
    bucket = _bucket_for(action, score=score, blocks=bool(blocked_task_ids), overdue=(remaining or 0) < 0)
    consequence = _consequence(
        blocked_task_ids=blocked_task_ids,
        critical_downstream=critical_downstream,
        milestones=affected_milestones,
        now=now,
    )

    return ActionPriority(
        action_id=action.id,
        score=score,
        bucket=bucket,
        due_in_days=round(remaining, 2) if remaining is not None else None,
        factors=factors,
        blocks_task_ids=blocked_task_ids,
        affected_milestone_ids=[milestone.id for milestone in affected_milestones],
        consequence=consequence,
    )


def _bucket_for(
    action: ActionItem, *, score: float, blocks: bool, overdue: bool
) -> str:
    """Group an action the way a manager triages: by what it *is*, then by
    whether it is holding work up.

    A request for the manager's time stays under support even when the
    engineer's task happens to have dependents — the conversation is not what
    is blocking anything.
    """
    if overdue or score >= 70.0 or action.priority is Priority.CRITICAL:
        return BUCKET_URGENT
    if action.type is ActionType.BLOCKER:
        return BUCKET_BLOCKED_WORK
    if action.type in (ActionType.APPROVAL, ActionType.HANDOVER_APPROVAL):
        return BUCKET_APPROVAL
    if action.type in (ActionType.SUPPORT_REQUEST, ActionType.ONE_ON_ONE):
        return BUCKET_SUPPORT
    # An unanswered question that is holding up other work is blocked work.
    if action.type is ActionType.QUESTION:
        return BUCKET_BLOCKED_WORK if blocks else BUCKET_SUPPORT
    return BUCKET_BLOCKED_WORK if blocks else BUCKET_ROUTINE


def _consequence(
    *,
    blocked_task_ids: list[str],
    critical_downstream: int,
    milestones: list[Milestone],
    now: datetime,
) -> str | None:
    """A plain-language statement of the downstream consequence, if any."""
    if not blocked_task_ids and not milestones:
        return None
    parts: list[str] = []
    if blocked_task_ids:
        parts.append(f"{len(blocked_task_ids)} dependent task(s) cannot proceed")
        if critical_downstream:
            parts.append(f"{critical_downstream} of them high or critical priority")
    for milestone in milestones[:2]:
        remaining = days_until(milestone.target_date, now=now) or 0.0
        parts.append(f"'{milestone.name}' is {remaining:.1f} day(s) away")
    return "; ".join(parts) + "."


def rank_actions(
    actions: list[ActionItem],
    *,
    graph: DependencyGraph,
    milestones: list[Milestone],
    now: datetime | None = None,
) -> list[ActionPriority]:
    """Score and sort action items, highest priority first."""
    now = now or utc_now()
    scored = [
        score_action(action, graph=graph, milestones=milestones, now=now)
        for action in actions
    ]
    scored.sort(key=lambda item: (-item.score, item.action_id))
    return scored
