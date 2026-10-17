"""Backend authorization.

Covers requirement 6: an engineer cannot access another engineer's requests.
Authorization is asserted at the HTTP layer, not by checking the UI.
"""

from __future__ import annotations

from tests.conftest import (
    ENG_ARJUN,
    ENG_DIEGO,
    ENG_LENA,
    ENG_MEI,
    ENG_NORA,
    ENG_SAMUEL,
    MANAGER,
    as_user,
)

# --------------------------------------------------------------------------
# Support requests
# --------------------------------------------------------------------------


def test_engineer_cannot_read_another_engineers_request(client):
    """Requirement 6. req-001 belongs to Arjun; Diego shares the project but
    not the request."""
    response = client.get("/api/requests/req-001", headers=as_user(ENG_DIEGO))
    assert response.status_code == 403


def test_request_list_is_scoped_to_the_caller(client):
    diego = client.get("/api/requests", headers=as_user(ENG_DIEGO)).json()
    assert {item["request"]["id"] for item in diego} == {"req-002"}

    arjun = client.get("/api/requests", headers=as_user(ENG_ARJUN)).json()
    assert {item["request"]["id"] for item in arjun} == {"req-001"}


def test_manager_sees_requests_for_authorized_projects(client):
    manager = client.get("/api/requests", headers=as_user(MANAGER)).json()
    ids = {item["request"]["id"] for item in manager}
    assert ids == {"req-001", "req-002", "req-003", "req-004", "req-005"}


def test_engineer_cannot_respond_to_another_engineers_request(client):
    response = client.post(
        "/api/requests/req-001/respond",
        headers=as_user(ENG_DIEGO),
        json={"body": "Approved by a peer."},
    )
    assert response.status_code == 403


def test_engineer_filter_cannot_be_used_to_read_others_requests(client):
    """Filtering by another engineer's id returns nothing, not their data."""
    response = client.get(
        "/api/requests", headers=as_user(ENG_DIEGO), params={"engineer_id": ENG_ARJUN}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_engineer_cannot_interpret_another_engineers_request(client):
    response = client.post("/api/requests/req-001/interpret", headers=as_user(ENG_DIEGO))
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Projects and tasks
# --------------------------------------------------------------------------


def test_engineer_cannot_read_an_unauthorized_project(client):
    """Samuel is only on the insights project."""
    assert client.get("/api/projects/proj-payments", headers=as_user(ENG_SAMUEL)).status_code == 403
    assert (
        client.get("/api/projects/proj-payments/tasks", headers=as_user(ENG_SAMUEL)).status_code
        == 403
    )


def test_project_list_is_scoped(client):
    samuel = client.get("/api/projects", headers=as_user(ENG_SAMUEL)).json()
    assert {item["project"]["id"] for item in samuel} == {"proj-insights"}

    manager = client.get("/api/projects", headers=as_user(MANAGER)).json()
    assert len(manager) == 3


def test_engineer_cannot_read_a_task_outside_their_projects(client):
    assert client.get("/api/tasks/pay-01", headers=as_user(ENG_MEI)).status_code == 403


def test_engineer_cannot_edit_a_task_they_do_not_own(client):
    response = client.patch(
        "/api/tasks/pay-01", headers=as_user(ENG_DIEGO), json={"status": "completed"}
    )
    assert response.status_code == 403


def test_task_owner_can_update_their_own_task(client, database):
    response = client.patch(
        "/api/tasks/pay-05",
        headers=as_user(ENG_DIEGO),
        json={
            "next_step": "Awaiting the messaging decision.",
            "progress_note": "Generic decline state is implemented behind a flag.",
        },
    )
    assert response.status_code == 200
    assert database.tasks.require("pay-05").next_step == "Awaiting the messaging decision."
    assert database.task_updates.find(lambda item: item.task_id == "pay-05")


def test_manager_can_update_a_task_in_their_project(client):
    response = client.patch(
        "/api/tasks/pay-03", headers=as_user(MANAGER), json={"priority": "critical"}
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------


def test_engineer_sees_only_actions_that_concern_them(client):
    """An engineer sees the action tracking their own request, nothing else."""
    arjun = client.get("/api/actions", headers=as_user(ENG_ARJUN)).json()
    assert {item["action"]["id"] for item in arjun} == {"act-001"}

    nora = client.get("/api/actions", headers=as_user(ENG_NORA)).json()
    assert {item["action"]["id"] for item in nora} == {"act-003"}


def test_engineer_cannot_create_an_action_item(client):
    response = client.post(
        "/api/actions",
        headers=as_user(ENG_ARJUN),
        json={"type": "follow_up", "title": "Remind the manager", "owner_id": MANAGER},
    )
    assert response.status_code == 403


def test_manager_cannot_delegate_to_an_unauthorized_user(client):
    """act-001 is on the payments project; Mei has no access there."""
    response = client.patch(
        "/api/actions/act-001", headers=as_user(MANAGER), json={"owner_id": ENG_MEI}
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]


def test_manager_can_delegate_to_an_authorized_user(client, database):
    response = client.patch(
        "/api/actions/act-001", headers=as_user(MANAGER), json={"owner_id": ENG_LENA}
    )
    assert response.status_code == 200
    assert database.actions.require("act-001").owner_id == ENG_LENA
    # The delegate is notified.
    notifications = client.get(
        "/api/notifications", headers=as_user(ENG_LENA)
    ).json()["notifications"]
    assert any(item["related_entity_id"] == "act-001" for item in notifications)


# --------------------------------------------------------------------------
# Dashboards, notifications and admin
# --------------------------------------------------------------------------


def test_engineer_cannot_open_the_manager_dashboard(client):
    assert client.get("/api/dashboard/manager", headers=as_user(ENG_ARJUN)).status_code == 403


def test_engineer_dashboard_only_shows_own_work(client):
    dashboard = client.get("/api/dashboard/engineer", headers=as_user(ENG_DIEGO)).json()
    owners = {view["task"]["owner_id"] for view in dashboard["my_tasks"]}
    assert owners == {ENG_DIEGO}
    assert {view["request"]["engineer_id"] for view in dashboard["my_requests"]} == {ENG_DIEGO}


def test_notifications_are_private_to_their_recipient(client, database):
    manager_notifications = client.get(
        "/api/notifications", headers=as_user(MANAGER)
    ).json()["notifications"]
    target = manager_notifications[0]["id"]
    response = client.post(f"/api/notifications/{target}/read", headers=as_user(ENG_DIEGO))
    assert response.status_code == 404
    assert database.notifications.get(target).read_at is None


def test_ai_endpoints_enforce_project_authorization(client):
    response = client.post(
        "/api/ai/project-briefing",
        headers=as_user(ENG_SAMUEL),
        json={"project_id": "proj-payments"},
    )
    assert response.status_code == 403


def test_ai_handover_brief_enforces_handover_authorization(client, database):
    from app.core.clock import utc_now
    from app.schemas.domain import HandoverRecord

    database.handovers.save(
        HandoverRecord(
            id="hdv-private",
            unavailable_user_id=ENG_NORA,
            requested_by=ENG_NORA,
            start_time=utc_now(),
            affected_project_ids=["proj-identity"],
            affected_task_ids=["id-01"],
        )
    )
    response = client.post(
        "/api/ai/handover-brief",
        headers=as_user(ENG_SAMUEL),
        json={"handover_id": "hdv-private"},
    )
    assert response.status_code == 403


def test_seed_endpoint_is_unavailable_when_disabled(settings, database):
    from app.main import create_app
    from fastapi.testclient import TestClient

    locked = settings.model_copy(update={"seed_endpoint_enabled": False})
    with TestClient(create_app(settings=locked, database=database)) as test_client:
        assert test_client.post("/api/admin/seed", headers=as_user(MANAGER)).status_code == 404
        assert test_client.get("/api/admin/stats", headers=as_user(MANAGER)).status_code == 404


def test_team_listing_is_scoped_to_shared_projects(client):
    samuel = client.get("/api/team", headers=as_user(ENG_SAMUEL)).json()
    names = {item["user"]["id"] for item in samuel}
    # Insights team plus the project manager, and nobody from payments-only.
    assert "eng-010" in names
    assert MANAGER in names
    assert ENG_ARJUN not in names


def test_public_user_projection_hides_workload_and_permissions(client):
    team = client.get("/api/team", headers=as_user(MANAGER)).json()
    sample = team[0]["user"]
    assert set(sample) == {"id", "name", "role", "title", "availability_status"}
