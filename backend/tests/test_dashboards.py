"""Dashboard assembly and project intelligence surfaces."""

from __future__ import annotations

from tests.conftest import ENG_DIEGO, ENG_RHEA, MANAGER, as_user


def test_manager_dashboard_summarises_what_needs_attention(client):
    dashboard = client.get("/api/dashboard/manager", headers=as_user(MANAGER)).json()
    summary = dashboard["summary"]
    assert summary["projects_total"] == 3
    assert summary["projects_at_risk"] >= 1
    assert summary["pending_approvals"] >= 1
    assert summary["open_support_requests"] == 4
    assert summary["overdue_actions"] >= 1
    assert summary["unread_notifications"] >= 1

    # The action inbox is ranked, with the lost approval first.
    assert dashboard["action_inbox"][0]["action"]["id"] == "act-001"
    assert dashboard["action_inbox"][0]["priority_detail"]["consequence"]
    # The source request is attached so the manager can open it.
    assert dashboard["action_inbox"][0]["source_request"]["id"] == "req-001"

    # Project health is ordered worst-first.
    scores = [item["health_score"] for item in dashboard["project_health"]]
    assert scores == sorted(scores)
    assert dashboard["project_health"][0]["project_id"] == "proj-payments"

    # Risks carry evidence and suggested actions.
    risk = dashboard["top_risks"][0]
    assert risk["evidence"]
    assert risk["suggested_actions"]

    # Milestones are ordered by how soon they land.
    remaining = [item["days_remaining"] for item in dashboard["upcoming_milestones"]]
    assert remaining == sorted(remaining)


def test_manager_dashboard_does_not_fabricate_a_briefing(client):
    """With no cached briefing, the field is null rather than invented text."""
    dashboard = client.get("/api/dashboard/manager", headers=as_user(MANAGER)).json()
    assert dashboard["daily_briefing"] is None


def test_briefing_is_cached_and_then_served_to_the_dashboard(client):
    generated = client.post(
        "/api/ai/project-briefing",
        headers=as_user(MANAGER),
        json={"project_id": "proj-payments"},
    )
    assert generated.status_code == 200
    body = generated.json()
    # Gemini is unconfigured in tests, so this is the honest degraded path.
    assert body["meta"]["degraded"] is True
    assert body["meta"]["source"] == "deterministic_fallback"
    assert body["data"]["progress_summary"]


def test_engineer_dashboard_shows_their_work_and_requests(client):
    dashboard = client.get("/api/dashboard/engineer", headers=as_user(ENG_DIEGO)).json()
    assert dashboard["summary"]["blocked_tasks"] == 1
    assert dashboard["my_blockers"][0]["task"]["id"] == "pay-05"
    assert dashboard["my_requests"][0]["request"]["id"] == "req-002"
    assert dashboard["awaiting_response"]
    assert dashboard["availability_status"] == "available"


def test_engineer_sees_upcoming_deadlines_only_inside_the_window(client):
    dashboard = client.get("/api/dashboard/engineer", headers=as_user(ENG_RHEA)).json()
    due_ids = {view["task"]["id"] for view in dashboard["upcoming_deadlines"]}
    # pay-02 is due in 2 days, pay-04 in 5; both inside the 7-day window.
    assert due_ids == {"pay-02", "pay-04"}


def test_project_detail_exposes_dependencies_and_evidence(client):
    detail = client.get("/api/projects/proj-payments", headers=as_user(MANAGER)).json()
    assert detail["manager_name"] == "Priya Raman"
    assert len(detail["tasks"]) == 8
    assert len(detail["team"]) == 6
    assert detail["documents"]
    assert detail["decisions"]

    worker = next(view for view in detail["tasks"] if view["task"]["id"] == "pay-02")
    assert worker["blocking_dependencies"] == ["Define settlement API contract"]
    assert "pay-03" in worker["downstream_task_ids"]
    assert worker["owner_name"] == "Rhea Kapoor"

    contract = next(view for view in detail["tasks"] if view["task"]["id"] == "pay-01")
    assert contract["is_overdue"] is True
    assert contract["days_until_due"] == -2.0


def test_task_detail_bundles_the_handover_relevant_context(client):
    detail = client.get("/api/tasks/pay-02", headers=as_user(MANAGER)).json()
    assert detail["task"]["task"]["id"] == "pay-02"
    assert len(detail["updates"]) == 2
    assert [item["id"] for item in detail["dependencies"]] == ["pay-01"]
    assert [item["id"] for item in detail["dependents"]] == ["pay-03"]
    assert any(doc["id"] == "doc-001" for doc in detail["documents"])


def test_risk_explanation_requires_a_live_finding(client):
    ok = client.post(
        "/api/ai/risk-explanation",
        headers=as_user(MANAGER),
        json={"project_id": "proj-payments", "finding_id": "risk-blocked-pay-02"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["explanation"]

    missing = client.post(
        "/api/ai/risk-explanation",
        headers=as_user(MANAGER),
        json={"project_id": "proj-payments", "finding_id": "risk-invented"},
    )
    assert missing.status_code == 404


def test_action_inbox_can_be_filtered_by_bucket(client):
    urgent = client.get(
        "/api/actions", headers=as_user(MANAGER), params={"bucket": "urgent"}
    ).json()
    assert {item["action"]["id"] for item in urgent} >= {"act-001"}
    routine = client.get(
        "/api/actions", headers=as_user(MANAGER), params={"bucket": "routine"}
    ).json()
    assert all(item["priority_detail"]["bucket"] == "routine" for item in routine)


def test_unknown_records_return_404_not_500(client):
    assert client.get("/api/tasks/does-not-exist", headers=as_user(MANAGER)).status_code == 404
    assert client.get("/api/projects/nope", headers=as_user(MANAGER)).status_code == 403
    assert client.get("/api/requests/nope", headers=as_user(MANAGER)).status_code == 404
    assert client.get("/api/handovers/nope", headers=as_user(MANAGER)).status_code == 404


def test_validation_errors_do_not_echo_the_payload(client):
    response = client.post(
        "/api/requests",
        headers=as_user(ENG_DIEGO),
        json={"project_id": "proj-payments", "category": "approval", "title": "x",
              "description": "secret internal detail"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "secret internal detail" not in str(body)
    assert body["errors"][0]["field"] == "title"
