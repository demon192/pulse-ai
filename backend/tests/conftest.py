"""Shared test fixtures.

Tests run against the in-memory store with the clock frozen, so every rule
assertion is deterministic.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.service import AIService  # noqa: E402
from app.core import clock  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.demo.seed import seed  # noqa: E402
from app.main import create_app  # noqa: E402
from app.notifications.service import NotificationService  # noqa: E402
from app.repositories.database import Database  # noqa: E402
from app.repositories.memory import InMemoryDocumentStore  # noqa: E402
from app.services.handovers import HandoverService  # noqa: E402

FROZEN_NOW = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)

MANAGER = "mgr-001"
ENG_ARJUN = "eng-001"       # payments, api-design, high workload
ENG_LENA = "eng-002"        # payments + identity, spare capacity
ENG_DIEGO = "eng-003"       # frontend, payments + insights
ENG_MEI = "eng-004"         # identity only -> ineligible on payments
ENG_SAMUEL = "eng-005"      # insights only
ENG_NORA = "eng-006"        # identity only
ENG_RHEA = "eng-008"        # payments critical-path owner
ENG_VICTOR = "eng-009"      # on leave -> ineligible


@pytest.fixture(autouse=True)
def frozen_clock():
    clock.freeze_time(FROZEN_NOW)
    yield FROZEN_NOW
    clock.freeze_time(None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="local",
        data_backend="memory",
        auth_mode="dev",
        dev_auth_enabled=True,
        seed_endpoint_enabled=True,
        gemini_enabled=False,
        gemini_api_key=None,
        demo_data_mode=True,
    )


@pytest.fixture
def database() -> Database:
    db = Database(InMemoryDocumentStore())
    seed(db, reset=True, now=FROZEN_NOW)
    return db


@pytest.fixture
def notifications(database: Database) -> NotificationService:
    return NotificationService(database)


@pytest.fixture
def ai_service(settings: Settings, database: Database) -> AIService:
    return AIService(settings, database)


@pytest.fixture
def handover_service(
    database: Database, notifications: NotificationService, ai_service: AIService
) -> HandoverService:
    return HandoverService(database, notifications, ai_service)


@pytest.fixture
def client(settings: Settings, database: Database):
    app = create_app(settings=settings, database=database)
    with TestClient(app) as test_client:
        yield test_client


def as_user(user_id: str) -> dict[str, str]:
    """Headers that authenticate as a development persona."""
    return {"X-Dev-User-Id": user_id}
