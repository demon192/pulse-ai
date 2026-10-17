"""Timezone handling.

All timestamps in TeamPulse are timezone-aware UTC. The clock is injectable so
that deterministic rule tests can pin "now".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_frozen_now: datetime | None = None


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    if _frozen_now is not None:
        return _frozen_now
    return datetime.now(UTC)


def freeze_time(moment: datetime | None) -> None:
    """Pin (or unpin, with ``None``) the clock. Test-only helper."""
    global _frozen_now
    if moment is not None and moment.tzinfo is None:
        raise ValueError("freeze_time requires a timezone-aware datetime")
    _frozen_now = moment if moment is None else moment.astimezone(UTC)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Normalise any datetime to UTC, assuming naive values are already UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hours_between(start: datetime, end: datetime) -> float:
    return (ensure_utc(end) - ensure_utc(start)).total_seconds() / 3600.0


def days_until(target: datetime | None, *, now: datetime | None = None) -> float | None:
    """Fractional days from ``now`` until ``target``. Negative when overdue."""
    if target is None:
        return None
    reference = now or utc_now()
    return (ensure_utc(target) - ensure_utc(reference)).total_seconds() / 86400.0


def shift(moment: datetime, **kwargs: float) -> datetime:
    return ensure_utc(moment) + timedelta(**kwargs)
