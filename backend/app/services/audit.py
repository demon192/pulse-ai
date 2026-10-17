"""Audit trail for decisions that change who owns work."""

from __future__ import annotations

import uuid

from app.core.clock import utc_now
from app.repositories.database import Database
from app.schemas.domain import AuditEvent


def record(
    database: Database,
    *,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, str] | None = None,
) -> AuditEvent:
    """Append an audit event.

    ``details`` is for short identifiers and status transitions only — never
    request bodies, notes or anything personal.
    """
    event = AuditEvent(
        id=f"aud-{uuid.uuid4().hex[:12]}",
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        created_at=utc_now(),
        details=details or {},
    )
    database.audit.save(event)
    return event


def for_entity(database: Database, entity_type: str, entity_id: str) -> list[AuditEvent]:
    events = database.audit.find(
        lambda item: item.entity_type == entity_type and item.entity_id == entity_id
    )
    events.sort(key=lambda item: item.created_at)
    return events
