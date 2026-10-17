"""Support request lifecycle, end to end through the API.

Covers requirement 1 (an approval request creates a tracked action item),
requirement 2 (an unresolved request stays visible after its notification is
read) and requirement 14 (a manager resolves an action and the engineer sees
the updated state).
"""

from __future__ import annotations

from app.models.enums import ActionStatus, ActionType, RequestStatus

from tests.conftest import ENG_ARJUN, ENG_DIEGO, ENG_LENA, MANAGER, as_user


def _create_approval(client, engineer=ENG_ARJUN):
    return client.post(
        "/api/requests",
        headers=as_user(engineer),
        params={"interpret": "false"},
        json={
            "project_id": "proj-payments",
            "category": "approval",
            "title": "Approve the refund reconciliation schema",
            "description": "Need sign-off before the schema is frozen.",
            "task_id": "pay-01",
            "priority": "high",
        },
    )


def test_approval_request_creates_a_tracked_action_item(client, database):
    """Requirement 1."""
    response = _create_approval(client)
    assert response.status_code == 201
    body = response.json()

    request_id = body["request"]["id"]
    action = body["action_item"]
    assert action is not None
    assert action["type"] == ActionType.APPROVAL.value
    assert action["source_request_id"] == request_id
    assert action["owner_id"] == MANAGER
    assert action["status"] == ActionStatus.OPEN.value
    assert action["priority"] == "high"

    # It is persisted, and it appears in the manager's inbox.
    assert database.actions.get(action["id"]) is not None
    inbox = client.get("/api/actions", headers=as_user(MANAGER)).json()
    assert action["id"] in {item["action"]["id"] for item in inbox}

    # And the manager is notified.
    notifications = client.get(
        "/api/notifications", headers=as_user(MANAGER)
    ).json()["notifications"]
    assert any(item["related_entity_id"] == action["id"] for item in notifications)


def test_progress_update_does_not_create_manager_work(client):
    """A status update is recorded but does not become an action item."""
    response = client.post(
        "/api/requests",
        headers=as_user(ENG_LENA),
        params={"interpret": "false"},
        json={
            "project_id": "proj-payments",
            "category": "progress_update",
            "title": "Schema migration verification finished",
            "description": "No issues found during the verification window.",
        },
    )
    assert response.status_code == 201
    assert response.json()["action_item"] is None


def test_unresolved_request_survives_the_notification_being_read(client, database):
    """Requirement 2."""
    notifications = client.get(
        "/api/notifications", headers=as_user(MANAGER)
    ).json()["notifications"]
    approval = next(
        item for item in notifications if item["related_entity_id"] == "act-001"
    )

    read = client.post(
        f"/api/notifications/{approval['id']}/read", headers=as_user(MANAGER)
    )
    assert read.status_code == 200

    # The engineer's request is untouched and still open.
    request = database.requests.require("req-001")
    assert request.status is RequestStatus.OPEN
    assert request.is_open

    # It is still listed for both the engineer and the manager.
    engineer_view = client.get(
        "/api/requests", headers=as_user(ENG_ARJUN), params={"include_closed": "false"}
    ).json()
    assert "req-001" in {item["request"]["id"] for item in engineer_view}

    manager_view = client.get(
        "/api/requests", headers=as_user(MANAGER), params={"include_closed": "false"}
    ).json()
    assert "req-001" in {item["request"]["id"] for item in manager_view}

    # And the tracking action is still open.
    assert database.actions.require("act-001").status is ActionStatus.OPEN


def test_manager_response_is_visible_to_the_engineer(client, database):
    response = client.post(
        "/api/requests/req-002/respond",
        headers=as_user(MANAGER),
        json={"body": "Show a generic decline message. Never surface issuer reason codes."},
    )
    assert response.status_code == 200
    assert response.json()["request"]["status"] == RequestStatus.ACKNOWLEDGED.value

    engineer_view = client.get("/api/requests/req-002", headers=as_user(ENG_DIEGO)).json()
    assert len(engineer_view["request"]["responses"]) == 1
    assert "generic decline" in engineer_view["request"]["responses"][0]["body"]

    # The engineer is notified about the response.
    engineer_notifications = client.get(
        "/api/notifications", headers=as_user(ENG_DIEGO)
    ).json()["notifications"]
    assert any(item["type"] == "request_responded" for item in engineer_notifications)

    # The tracking action moved out of 'open'.
    assert database.actions.require("act-002").status is ActionStatus.ACKNOWLEDGED


def test_manager_resolves_action_and_engineer_sees_the_outcome(client, database):
    """Requirement 14."""
    resolve = client.post(
        "/api/actions/act-001/resolve",
        headers=as_user(MANAGER),
        json={
            "resolution_notes": "Approved. Model partial refunds as their own event type.",
            "decision": "Partial refunds are a separate event type, not negative settlements.",
            "decision_rationale": "Keeps the ledger append-only.",
        },
    )
    assert resolve.status_code == 200
    assert resolve.json()["action"]["status"] == ActionStatus.RESOLVED.value

    # The engineer's own request now reflects the decision.
    engineer_view = client.get("/api/requests/req-001", headers=as_user(ENG_ARJUN)).json()
    assert engineer_view["request"]["status"] == RequestStatus.RESOLVED.value
    assert "own event type" in engineer_view["request"]["resolution_notes"]

    # A durable decision record was written and linked.
    action = database.actions.require("act-001")
    assert action.decision_record_id is not None
    decision = database.decisions.require(action.decision_record_id)
    assert decision.decided_by == MANAGER
    assert decision.task_id == "pay-01"
    assert "separate event type" in decision.decision

    # The engineer is notified.
    engineer_notifications = client.get(
        "/api/notifications", headers=as_user(ENG_ARJUN)
    ).json()["notifications"]
    assert any(item["type"] == "request_resolved" for item in engineer_notifications)

    # And the audit trail records who resolved it.
    events = database.audit.find(lambda item: item.entity_id == "act-001")
    assert any(event.action == "action.resolve" and event.actor_id == MANAGER for event in events)


def test_engineer_cannot_resolve_an_action_assigned_to_the_manager(client):
    response = client.post(
        "/api/actions/act-001/resolve",
        headers=as_user(ENG_ARJUN),
        json={"resolution_notes": "Approving my own request."},
    )
    assert response.status_code == 403


def test_engineer_can_add_a_context_note_but_not_change_priority(client):
    ok = client.patch(
        "/api/requests/req-001",
        headers=as_user(ENG_ARJUN),
        json={"engineer_context_note": "The AI summary missed that this blocks the worker."},
    )
    assert ok.status_code == 200
    assert "blocks the worker" in ok.json()["request"]["engineer_context_note"]

    denied = client.patch(
        "/api/requests/req-001", headers=as_user(ENG_ARJUN), json={"priority": "low"}
    )
    assert denied.status_code == 403


def test_engineer_cannot_mark_their_own_request_resolved(client):
    response = client.patch(
        "/api/requests/req-001", headers=as_user(ENG_ARJUN), json={"status": "resolved"}
    )
    assert response.status_code == 403


def test_closing_a_request_closes_its_tracking_action(client, database):
    response = client.patch(
        "/api/requests/req-003",
        headers=as_user(MANAGER),
        json={"status": "resolved", "resolution_notes": "Use a 60-minute access token."},
    )
    assert response.status_code == 200
    assert database.actions.require("act-003").status is ActionStatus.RESOLVED
    # The manager's inbox no longer shows it.
    inbox = client.get("/api/actions", headers=as_user(MANAGER)).json()
    assert "act-003" not in {item["action"]["id"] for item in inbox}


def test_request_for_an_unauthorized_project_is_refused(client):
    """Samuel is only authorised on the insights project."""
    response = client.post(
        "/api/requests",
        headers=as_user("eng-005"),
        params={"interpret": "false"},
        json={
            "project_id": "proj-payments",
            "category": "approval",
            "title": "Approve something I cannot see",
            "description": "Should be refused.",
        },
    )
    assert response.status_code == 403
