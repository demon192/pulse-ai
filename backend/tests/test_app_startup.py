"""Requirement 15: the application starts in local development mode."""

from __future__ import annotations

from tests.conftest import MANAGER, as_user


def test_health_endpoint_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "local"
    assert body["data_backend"] == "memory"


def test_api_health_alias(client):
    assert client.get("/api/health").status_code == 200


def test_session_requires_authentication(client):
    response = client.get("/api/session")
    assert response.status_code == 401


def test_session_returns_dev_personas(client):
    response = client.get("/api/session", headers=as_user(MANAGER))
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "manager"
    assert body["auth_mode"] == "dev"
    assert body["demo_data_mode"] is True
    # The manager persona is listed first so the demo opens on it.
    assert body["dev_personas"][0]["role"] == "manager"
    assert len(body["dev_personas"]) == 11


def test_unknown_persona_is_rejected(client):
    assert client.get("/api/session", headers=as_user("eng-999")).status_code == 401


def test_demo_data_is_loaded(client):
    stats = client.get("/api/admin/stats", headers=as_user(MANAGER)).json()
    assert stats["users"] == 11
    assert stats["projects"] == 3
    assert stats["tasks"] == 19


def test_production_settings_disable_dev_affordances():
    from app.core.config import Settings

    production = Settings(
        environment="production", dev_auth_enabled=True, seed_endpoint_enabled=True
    )
    assert production.dev_auth_enabled is False
    assert production.seed_endpoint_enabled is False
    assert production.auth_mode == "firebase"
