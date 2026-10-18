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


# --------------------------------------------------------------------------
# GET /api/auth-config
#
# The SPA cannot authenticate until it knows how, so this endpoint is public by
# necessity. It must therefore carry public client identifiers only.
# --------------------------------------------------------------------------


def test_auth_config_is_public_and_describes_dev_mode(client):
    response = client.get("/api/auth-config")
    assert response.status_code == 200
    body = response.json()
    assert body["auth_mode"] == "dev"
    assert body["dev_personas_enabled"] is True
    # Nothing Firebase-shaped leaks out of a development instance.
    assert body["sign_in_configured"] is False
    assert body["firebase_api_key"] is None
    assert body["firebase_auth_domain"] is None


def test_auth_config_hands_the_spa_what_sign_in_needs():
    from app.core.config import Settings
    from app.main import create_app
    from app.repositories.database import Database
    from app.repositories.memory import InMemoryDocumentStore
    from fastapi.testclient import TestClient

    settings = Settings(
        environment="production",
        data_backend="memory",
        firebase_project_id="teampulse-demo",
        firebase_web_api_key="public-web-api-key",
    )
    app = create_app(settings=settings, database=Database(InMemoryDocumentStore()))
    with TestClient(app) as test_client:
        body = test_client.get("/api/auth-config").json()

    assert body["auth_mode"] == "firebase"
    assert body["sign_in_configured"] is True
    assert body["dev_personas_enabled"] is False
    assert body["firebase_api_key"] == "public-web-api-key"
    # Derived from the project id rather than requiring a second variable.
    assert body["firebase_auth_domain"] == "teampulse-demo.firebaseapp.com"


def test_auth_config_reports_a_deployment_nobody_can_sign_in_to():
    from app.core.config import Settings

    # Firebase mode with no web config: the SPA must say so rather than show a
    # sign-in button that cannot work.
    settings = Settings(environment="production", firebase_project_id="teampulse-demo")
    assert settings.sign_in_configured is False
    assert settings.resolved_auth_domain == "teampulse-demo.firebaseapp.com"


def test_explicit_auth_domain_wins_over_the_derived_one():
    from app.core.config import Settings

    settings = Settings(
        environment="production",
        firebase_project_id="teampulse-demo",
        firebase_auth_domain="auth.teampulse.example",
        firebase_web_api_key="public-web-api-key",
    )
    assert settings.resolved_auth_domain == "auth.teampulse.example"
    assert settings.sign_in_configured is True
