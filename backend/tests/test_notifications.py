"""Notification engine.

Covers requirement 5: duplicate events do not create duplicate notifications.
"""

from __future__ import annotations

from datetime import timedelta

from app.models.enums import NotificationType, Priority
from app.notifications.service import make_dedup_key
from app.services.sweeps import run_sweep

from tests.conftest import FROZEN_NOW, MANAGER


def _emit(notifications, *, priority=Priority.MEDIUM, now=FROZEN_NOW, **overrides):
    payload = {
        "recipient_id": MANAGER,
        "notification_type": NotificationType.TASK_OVERDUE,
        "title": "Overdue task",
        "message": "A task is overdue.",
        "reason": "The due date has passed.",
        "dedup_key": make_dedup_key(
            event="task_overdue",
            entity_type="task",
            entity_id="task-x",
            recipient_id=MANAGER,
        ),
        "related_entity_type": "task",
        "related_entity_id": "task-x",
        "priority": priority,
        "allow_escalation": True,
        "now": now,
    }
    payload.update(overrides)
    return notifications.emit(**payload)


def test_duplicate_event_does_not_create_a_second_notification(database, notifications):
    before = database.notifications.count()
    first = _emit(notifications)
    assert first is not None
    assert database.notifications.count() == before + 1

    for _ in range(5):
        assert _emit(notifications) is None
    assert database.notifications.count() == before + 1


def test_repeated_sweeps_are_idempotent(database, notifications):
    project_ids = {"proj-payments", "proj-identity", "proj-insights"}
    first = run_sweep(database, notifications, project_ids=project_ids, now=FROZEN_NOW)
    assert first > 0
    total_after_first = database.notifications.count()

    second = run_sweep(database, notifications, project_ids=project_ids, now=FROZEN_NOW)
    assert second == 0
    assert database.notifications.count() == total_after_first


def test_sweep_reuses_the_seeded_dedup_keys(database, notifications):
    """The seeded approval notification must not be duplicated by a sweep."""
    run_sweep(
        database,
        notifications,
        project_ids={"proj-payments"},
        now=FROZEN_NOW,
    )
    approval_notifications = database.notifications.find(
        lambda item: item.related_entity_id == "act-001"
    )
    assert len(approval_notifications) == 1


def test_unresolved_item_escalates_rather_than_repeating(database, notifications):
    created = _emit(notifications, priority=Priority.MEDIUM)
    assert created is not None

    # Same day, worse priority: too soon to escalate.
    assert _emit(notifications, priority=Priority.HIGH, now=FROZEN_NOW + timedelta(hours=2)) is None

    later = FROZEN_NOW + timedelta(hours=25)
    # A day later but no worse: stay quiet.
    assert _emit(notifications, priority=Priority.MEDIUM, now=later) is None
    # A day later and worse: escalate the same record, not a new one.
    escalated = _emit(notifications, priority=Priority.HIGH, now=later)
    assert escalated is not None
    assert escalated.id == created.id
    assert escalated.escalation_count == 1
    assert escalated.priority is Priority.HIGH
    # Escalation re-surfaces it as unread.
    assert escalated.read_at is None


def test_escalation_is_capped(database, notifications):
    created = _emit(notifications, priority=Priority.LOW)
    assert created is not None
    priorities = [Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
    for index, priority in enumerate(priorities, start=1):
        result = _emit(
            notifications,
            priority=priority,
            now=FROZEN_NOW + timedelta(hours=25 * index),
        )
        assert result is not None
        assert result.escalation_count == index
    # A fourth escalation is suppressed.
    assert (
        _emit(notifications, priority=Priority.CRITICAL, now=FROZEN_NOW + timedelta(days=30))
        is None
    )


def test_marking_read_does_not_resolve_or_delete(database, notifications):
    created = _emit(notifications)
    updated = notifications.mark_read(created.id, recipient_id=MANAGER)
    assert updated.read_at is not None
    assert updated.resolved_at is None
    assert database.notifications.get(created.id) is not None


def test_notifications_are_scoped_to_their_recipient(database, notifications):
    created = _emit(notifications)
    assert notifications.mark_read(created.id, recipient_id="eng-001") is None
    assert database.notifications.get(created.id).read_at is None


def test_resolving_by_entity_closes_open_notifications(database, notifications):
    created = _emit(notifications)
    count = notifications.resolve_by_entity("task", "task-x")
    assert count == 1
    assert database.notifications.get(created.id).resolved_at is not None
    # A resolved notification no longer blocks a fresh one for a new occurrence.
    assert _emit(notifications) is not None


def test_every_notification_carries_the_required_fields(database, notifications):
    created = _emit(notifications, suggested_action="Do the thing.")
    assert created.recipient_id
    assert created.reason
    assert created.priority
    assert created.related_entity_type and created.related_entity_id
    assert created.suggested_action
    assert created.created_at
    assert created.deduplication_key
