"""Action prioritisation.

The score must be driven by explicit urgency, deadlines, blocked downstream
work, milestone proximity and waiting time — and nothing else.
"""

from __future__ import annotations

from datetime import timedelta

from app.models.enums import ActionStatus, ActionType, Priority
from app.rules.dependencies import DependencyGraph
from app.rules.prioritization import (
    BUCKET_APPROVAL,
    BUCKET_BLOCKED_WORK,
    BUCKET_ROUTINE,
    BUCKET_SUPPORT,
    BUCKET_URGENT,
    rank_actions,
    score_action,
)
from app.schemas.domain import ActionItem

from tests.conftest import FROZEN_NOW, MANAGER


def _score(database, action):
    return score_action(
        action,
        graph=DependencyGraph(database.tasks.list_all()),
        milestones=database.milestones.list_all(),
        now=FROZEN_NOW,
    )


def _action(**overrides) -> ActionItem:
    payload = {
        "id": "act-test",
        "type": ActionType.FOLLOW_UP,
        "title": "Test action",
        "description": "",
        "owner_id": MANAGER,
        "created_by": MANAGER,
        "created_at": FROZEN_NOW,
        "updated_at": FROZEN_NOW,
        "status": ActionStatus.OPEN,
        "priority": Priority.MEDIUM,
    }
    payload.update(overrides)
    return ActionItem(**payload)


def test_all_six_factors_are_reported(database):
    action = database.actions.require("act-001")
    detail = _score(database, action)
    factors = {item.factor for item in detail.factors}
    assert factors == {
        "explicit_urgency",
        "deadline_proximity",
        "blocks_downstream_work",
        "milestone_proximity",
        "time_waiting",
    }
    assert detail.score == round(sum(item.points for item in detail.factors), 2)
    assert all(item.detail for item in detail.factors)


def test_the_lost_approval_outranks_a_routine_follow_up(database):
    approval = _score(database, database.actions.require("act-001"))
    follow_up = _score(database, database.actions.require("act-005"))
    assert approval.score > follow_up.score
    assert approval.bucket == BUCKET_URGENT
    assert follow_up.bucket == BUCKET_ROUTINE


def test_downstream_consequence_is_stated(database):
    detail = _score(database, database.actions.require("act-001"))
    assert "pay-02" in detail.blocks_task_ids
    assert "ms-pay-1" in detail.affected_milestone_ids
    assert detail.consequence is not None
    assert "dependent task(s) cannot proceed" in detail.consequence
    assert "Settlement API GA" in detail.consequence


def test_blocking_downstream_work_raises_the_score(database):
    without = _score(database, _action(task_id=None))
    with_downstream = _score(database, _action(task_id="pay-01"))
    assert with_downstream.score > without.score


def test_waiting_longer_raises_the_score_but_cannot_dominate(database):
    fresh = _score(database, _action(created_at=FROZEN_NOW))
    stale = _score(database, _action(created_at=FROZEN_NOW - timedelta(days=30)))
    assert stale.score > fresh.score
    waiting = next(i for i in stale.factors if i.factor == "time_waiting")
    # Capped so an old, consequence-free item never beats a blocking one.
    assert waiting.points == 15.0


def test_overdue_action_is_urgent(database):
    detail = _score(
        database, _action(due_date=FROZEN_NOW - timedelta(days=2), priority=Priority.LOW)
    )
    assert detail.bucket == BUCKET_URGENT


def test_buckets_separate_the_inbox_sections(database):
    assert (
        _score(database, _action(type=ActionType.APPROVAL, priority=Priority.MEDIUM)).bucket
        == BUCKET_APPROVAL
    )
    assert (
        _score(database, _action(type=ActionType.SUPPORT_REQUEST, priority=Priority.LOW)).bucket
        == BUCKET_SUPPORT
    )
    assert (
        _score(database, _action(type=ActionType.BLOCKER, priority=Priority.MEDIUM)).bucket
        == BUCKET_BLOCKED_WORK
    )


def test_ranking_is_stable_and_descending(database):
    actions = [action for action in database.actions.list_all() if action.is_open]
    ranked = rank_actions(
        actions,
        graph=DependencyGraph(database.tasks.list_all()),
        milestones=database.milestones.list_all(),
        now=FROZEN_NOW,
    )
    scores = [item.score for item in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0].action_id == "act-001"
