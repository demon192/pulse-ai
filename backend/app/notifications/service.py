"""In-app notification engine.

Two behaviours matter for the product:

* **Deduplication** — the same underlying event never produces a second
  notification. Callers supply a stable ``deduplication_key`` derived from the
  event and the record it concerns.
* **Escalation instead of repetition** — a still-unresolved item is not
  re-announced on every sweep. It is escalated at most once per
  ``escalation_interval_hours``, and only when the item has become more urgent.

Reading a notification never changes the underlying request, task or action.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.core.clock import hours_between, utc_now
from app.core.logging import get_logger
from app.models.enums import PRIORITY_WEIGHT, NotificationType, Priority
from app.repositories.database import Database
from app.schemas.domain import Notification

logger = get_logger(__name__)

DEFAULT_ESCALATION_INTERVAL_HOURS = 24.0
MAX_ESCALATIONS = 3


def attention_key(entity_type: str, entity_id: str, recipient_id: str) -> str:
    """Dedup key for "this record needs your attention".

    Creation, a passing deadline and a worsening blocker are all the *same*
    concern about one record, so they share a key: the first one creates the
    notification and later ones escalate it instead of stacking up.
    """
    return make_dedup_key(
        event="attention",
        entity_type=entity_type,
        entity_id=entity_id,
        recipient_id=recipient_id,
    )


def make_dedup_key(
    *, event: str, entity_type: str, entity_id: str, recipient_id: str, discriminator: str = ""
) -> str:
    """Build the stable key that suppresses repeat notifications."""
    parts = [event, entity_type, entity_id, recipient_id]
    if discriminator:
        parts.append(discriminator)
    return "|".join(parts)


class NotificationService:
    def __init__(self, database: Database) -> None:
        self._db = database

    # -- queries --------------------------------------------------------
    def for_recipient(
        self, recipient_id: str, *, include_read: bool = True, include_resolved: bool = False
    ) -> list[Notification]:
        notifications = self._db.notifications.find(
            lambda item: item.recipient_id == recipient_id
        )
        if not include_read:
            notifications = [item for item in notifications if item.read_at is None]
        if not include_resolved:
            notifications = [item for item in notifications if item.resolved_at is None]
        notifications.sort(
            key=lambda item: (-PRIORITY_WEIGHT[item.priority], -item.created_at.timestamp())
        )
        return notifications

    def unread_count(self, recipient_id: str) -> int:
        return len(self.for_recipient(recipient_id, include_read=False))

    def _find_by_key(self, dedup_key: str) -> Notification | None:
        return self._db.notifications.find_one(
            lambda item: item.deduplication_key == dedup_key and item.resolved_at is None
        )

    # -- emission -------------------------------------------------------
    def emit(
        self,
        *,
        recipient_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        reason: str,
        dedup_key: str,
        suggested_action: str | None = None,
        priority: Priority = Priority.MEDIUM,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        allow_escalation: bool = False,
        escalation_interval_hours: float = DEFAULT_ESCALATION_INTERVAL_HOURS,
        now: datetime | None = None,
    ) -> Notification | None:
        """Create a notification, or return ``None`` when it is a duplicate.

        When ``allow_escalation`` is set, an existing unresolved notification is
        escalated (priority raised, message refreshed) rather than duplicated —
        but only once per interval and only while it is becoming more urgent.
        """
        now = now or utc_now()
        existing = self._find_by_key(dedup_key)

        if existing is not None:
            if not allow_escalation:
                return None
            if existing.escalation_count >= MAX_ESCALATIONS:
                return None
            reference = existing.last_escalated_at or existing.created_at
            if hours_between(reference, now) < escalation_interval_hours:
                return None
            if PRIORITY_WEIGHT[priority] <= PRIORITY_WEIGHT[existing.priority]:
                # Nothing got worse: stay quiet rather than nag.
                return None
            escalated = existing.model_copy(
                update={
                    "priority": priority,
                    "message": message,
                    "reason": reason,
                    "suggested_action": suggested_action,
                    "escalation_count": existing.escalation_count + 1,
                    "last_escalated_at": now,
                    # Re-surface it in the unread list.
                    "read_at": None,
                }
            )
            self._db.notifications.save(escalated)
            logger.info(
                "Escalated notification %s (%s) to %s",
                escalated.id,
                notification_type.value,
                priority.value,
            )
            return escalated

        notification = Notification(
            id=f"ntf-{uuid.uuid4().hex[:12]}",
            recipient_id=recipient_id,
            type=notification_type,
            title=title,
            message=message,
            reason=reason,
            suggested_action=suggested_action,
            priority=priority,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            created_at=now,
            deduplication_key=dedup_key,
        )
        self._db.notifications.save(notification)
        logger.info(
            "Created notification %s (%s) for %s",
            notification.id,
            notification_type.value,
            recipient_id,
        )
        return notification

    # -- state transitions ------------------------------------------------
    def mark_read(self, notification_id: str, *, recipient_id: str) -> Notification | None:
        """Mark as read. Deliberately does not touch the underlying record."""
        notification = self._db.notifications.get(notification_id)
        if notification is None or notification.recipient_id != recipient_id:
            return None
        if notification.read_at is None:
            notification = notification.model_copy(update={"read_at": utc_now()})
            self._db.notifications.save(notification)
        return notification

    def mark_resolved(
        self, notification_id: str, *, recipient_id: str
    ) -> Notification | None:
        notification = self._db.notifications.get(notification_id)
        if notification is None or notification.recipient_id != recipient_id:
            return None
        now = utc_now()
        notification = notification.model_copy(
            update={"resolved_at": now, "read_at": notification.read_at or now}
        )
        self._db.notifications.save(notification)
        return notification

    def resolve_by_entity(self, entity_type: str, entity_id: str) -> int:
        """Resolve every open notification about one record.

        Called when the underlying request/action/handover reaches a terminal
        state so the inbox does not keep stale items.
        """
        now = utc_now()
        count = 0
        for notification in self._db.notifications.find(
            lambda item: item.related_entity_type == entity_type
            and item.related_entity_id == entity_id
            and item.resolved_at is None
        ):
            self._db.notifications.save(
                notification.model_copy(
                    update={"resolved_at": now, "read_at": notification.read_at or now}
                )
            )
            count += 1
        return count
