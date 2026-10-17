"""Emergency-leave handover, end to end.

Covers requirement 8 (an ineligible candidate cannot be selected),
requirement 9 (a manager must approve before the assignment is finalised),
requirement 10 (the brief contains the required fields) and requirement 11
(missing information is explicitly identified).
"""

from __future__ import annotations

from app.ai.schemas import REQUIRED_HANDOVER_SECTIONS
from app.models.enums import ApprovalStatus, AvailabilityStatus, HandoverStatus

from tests.conftest import (
    ENG_ARJUN,
    ENG_DIEGO,
    ENG_MEI,
    ENG_RHEA,
    ENG_VICTOR,
    FROZEN_NOW,
    MANAGER,
    as_user,
)


def _raise_handover(client, engineer=ENG_RHEA, notes=None):
    payload = {
        "start_time": FROZEN_NOW.isoformat(),
        "reason_category": "unplanned_leave",
    }
    if notes:
        payload["handover_notes"] = notes
    return client.post("/api/handovers", headers=as_user(engineer), json=payload)


def _analyze(client, handover_id):
    return client.post(f"/api/handovers/{handover_id}/analyze", headers=as_user(MANAGER))


def test_engineer_can_raise_a_handover_without_personal_detail(client, database):
    response = _raise_handover(client)
    assert response.status_code == 201
    body = response.json()["handover"]
    assert body["unavailable_user_id"] == ENG_RHEA
    assert body["handover_status"] == HandoverStatus.DRAFT.value
    assert body["manager_approval_status"] == ApprovalStatus.PENDING.value
    # Only an operational category is stored, never a reason narrative.
    assert set(body) >= {"reason_category", "start_time", "expected_return"}
    assert "reason" not in body
    # Availability is reflected immediately.
    assert database.users.require(ENG_RHEA).availability_status is (
        AvailabilityStatus.UNAVAILABLE
    )


def test_analysis_identifies_tasks_dependencies_deadlines_and_approvals(client):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    response = _analyze(client, handover_id)
    assert response.status_code == 200
    analysis = response.json()["analysis"]

    # 1. Active tasks owned by the unavailable engineer.
    assert set(analysis["active_task_ids"]) == {"pay-02", "pay-04"}
    # 2. Dependency-linked work.
    assert "pay-03" in analysis["downstream_task_ids"]
    assert "pay-06" in analysis["downstream_task_ids"]
    # 3. Affected milestones.
    assert "ms-pay-1" in analysis["affected_milestone_ids"]
    # 4. Documentation and pending approvals, including the upstream approval
    # that is the real reason pay-02 is blocked.
    assert "doc-001" in analysis["relevant_document_ids"]
    assert "pay-01" in analysis["upstream_blocking_task_ids"]
    assert "act-001" in analysis["pending_approval_action_ids"]
    # Evidence links every claim back to a record.
    assert all(item["entity_id"] for item in analysis["evidence"])


def test_analysis_ranks_candidates_with_reasons(client):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    candidates = _analyze(client, handover_id).json()["analysis"]["candidates"]

    eligible = [item for item in candidates if item["eligible"]]
    assert eligible[0]["user_id"] == ENG_ARJUN
    assert eligible[0]["breakdown"]
    assert all(item["explanation"] for item in eligible[0]["breakdown"])

    # Requirement 8: ineligible candidates are shown with their reason, scoreless.
    mei = next(item for item in candidates if item["user_id"] == ENG_MEI)
    assert mei["eligible"] is False
    assert mei["total_score"] == 0.0
    assert any("access authorisation" in r for r in mei["ineligibility_reasons"])

    victor = next(item for item in candidates if item["user_id"] == ENG_VICTOR)
    assert victor["eligible"] is False


def test_generated_brief_has_every_required_section(client):
    """Requirement 10."""
    handover_id = _raise_handover(client).json()["handover"]["id"]
    handover = _analyze(client, handover_id).json()["handover"]["handover"]

    assert handover["generated_brief"]
    for brief in handover["generated_brief"]:
        keys = [section["key"] for section in brief["sections"]]
        assert keys == list(REQUIRED_HANDOVER_SECTIONS)
        for section in brief["sections"]:
            assert section["heading"]
            assert section["content"].strip()
            assert section["evidence_kind"] in {
                "verified_fact",
                "rule_derived",
                "hypothesis",
                "recommendation",
            }


def test_brief_is_generated_without_handover_notes_and_says_so(client):
    """Requirement 11: gaps are named rather than invented."""
    handover_id = _raise_handover(client).json()["handover"]["id"]
    handover = _analyze(client, handover_id).json()["handover"]["handover"]

    missing = " ".join(handover["missing_information"])
    assert "handover notes" in missing.lower()
    assert handover["generated_brief"], "a preliminary brief is produced anyway"


def test_missing_information_names_specific_gaps(client, database):
    """A task with no next step, no updates and no documents is called out."""
    task = database.tasks.require("pay-04")
    database.tasks.save(task.model_copy(update={"next_step": None, "remaining_effort": None}))
    for update in database.task_updates.find(lambda item: item.task_id == "pay-04"):
        database.task_updates.delete(update.id)

    handover_id = _raise_handover(client).json()["handover"]["id"]
    handover = _analyze(client, handover_id).json()["handover"]["handover"]
    missing = " ".join(handover["missing_information"])
    assert "No next step is recorded on 'Payment retry policy'." in missing
    assert "No progress updates have been written for 'Payment retry policy'." in missing
    assert "Remaining effort is not estimated" in missing


def test_analysis_creates_a_manager_approval_action(client, database):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)

    action = database.actions.find_one(
        lambda item: item.source_handover_id == handover_id
    )
    assert action is not None
    assert action.owner_id == MANAGER
    assert action.type.value == "handover_approval"

    notifications = client.get(
        "/api/notifications", headers=as_user(MANAGER)
    ).json()["notifications"]
    assert any(item["related_entity_id"] == action.id for item in notifications)


def test_assignment_is_not_final_until_the_manager_approves(client, database):
    """Requirement 9."""
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)

    # The backup cannot accept before approval.
    premature = client.post(
        f"/api/handovers/{handover_id}/accept", headers=as_user(ENG_ARJUN)
    )
    assert premature.status_code == 403  # not yet the nominated backup

    # Ownership has not moved.
    assert database.tasks.require("pay-02").owner_id == ENG_RHEA


def test_manager_approval_then_backup_acceptance_transfers_ownership(client, database):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)

    approve = client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(MANAGER),
        json={"selected_backup_id": ENG_ARJUN, "notes": "Arjun knows the contract."},
    )
    assert approve.status_code == 200
    approved = approve.json()["handover"]
    assert approved["manager_approval_status"] == ApprovalStatus.APPROVED.value
    assert approved["approved_by"] == MANAGER
    assert approved["selected_backup_id"] == ENG_ARJUN

    # Approval alone is a recommendation, not a transfer.
    assert database.tasks.require("pay-02").owner_id == ENG_RHEA

    # The nominated backup is notified.
    backup_notifications = client.get(
        "/api/notifications", headers=as_user(ENG_ARJUN)
    ).json()["notifications"]
    assert any(item["type"] == "backup_assigned" for item in backup_notifications)

    # Acceptance finalises it.
    accept = client.post(
        f"/api/handovers/{handover_id}/accept", headers=as_user(ENG_ARJUN)
    )
    assert accept.status_code == 200
    assert accept.json()["handover"]["handover_status"] == HandoverStatus.ACCEPTED.value
    assert database.tasks.require("pay-02").owner_id == ENG_ARJUN
    assert database.tasks.require("pay-04").owner_id == ENG_ARJUN

    # The manager is told coverage is in place.
    manager_notifications = client.get(
        "/api/notifications", headers=as_user(MANAGER)
    ).json()["notifications"]
    assert any(
        item["type"] == "handover_assignment_accepted" for item in manager_notifications
    )

    # The audit trail names who approved and who accepted.
    events = database.audit.find(lambda item: item.entity_id == handover_id)
    actions_taken = {(event.action, event.actor_id) for event in events}
    assert ("handover.approve", MANAGER) in actions_taken
    assert ("handover.accept", ENG_ARJUN) in actions_taken


def test_ineligible_candidate_cannot_be_approved(client, database):
    """Requirement 8, enforced at assignment time."""
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)

    response = client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(MANAGER),
        json={"selected_backup_id": ENG_MEI},
    )
    assert response.status_code == 403
    assert "not eligible" in response.json()["detail"]
    assert database.handovers.require(handover_id).selected_backup_id is None


def test_eligibility_is_rechecked_at_approval_time(client, database):
    """A candidate who became unavailable after ranking cannot be approved."""
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)

    arjun = database.users.require(ENG_ARJUN)
    database.users.save(
        arjun.model_copy(update={"availability_status": AvailabilityStatus.ON_LEAVE})
    )

    response = client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(MANAGER),
        json={"selected_backup_id": ENG_ARJUN},
    )
    assert response.status_code == 403
    assert "Availability" in response.json()["detail"]


def test_only_a_manager_of_an_affected_project_can_approve(client):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)
    response = client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(ENG_DIEGO),
        json={"selected_backup_id": ENG_ARJUN},
    )
    assert response.status_code == 403


def test_only_the_nominated_backup_can_accept(client):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)
    client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(MANAGER),
        json={"selected_backup_id": ENG_ARJUN},
    )
    response = client.post(
        f"/api/handovers/{handover_id}/accept", headers=as_user(ENG_DIEGO)
    )
    assert response.status_code == 403


def test_declining_returns_the_handover_for_re_review(client, database):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)
    client.post(
        f"/api/handovers/{handover_id}/approve",
        headers=as_user(MANAGER),
        json={"selected_backup_id": ENG_ARJUN},
    )
    response = client.post(
        f"/api/handovers/{handover_id}/decline",
        headers=as_user(ENG_ARJUN),
        json={"reason": "Already at capacity before the release."},
    )
    assert response.status_code == 200
    handover = response.json()["handover"]
    assert handover["handover_status"] == HandoverStatus.DECLINED.value
    assert handover["selected_backup_id"] is None
    assert handover["manager_approval_status"] == ApprovalStatus.PENDING.value
    # Ownership never moved.
    assert database.tasks.require("pay-02").owner_id == ENG_RHEA


def test_manager_can_reject_a_handover(client):
    handover_id = _raise_handover(client).json()["handover"]["id"]
    _analyze(client, handover_id)
    response = client.post(
        f"/api/handovers/{handover_id}/reject",
        headers=as_user(MANAGER),
        json={"reason": "Rhea is back tomorrow; coverage is not needed."},
    )
    assert response.status_code == 200
    assert response.json()["handover"]["handover_status"] == HandoverStatus.REJECTED.value


def test_engineer_cannot_raise_a_handover_for_someone_else(client):
    response = client.post(
        "/api/handovers",
        headers=as_user(ENG_DIEGO),
        json={"unavailable_user_id": ENG_RHEA, "start_time": FROZEN_NOW.isoformat()},
    )
    assert response.status_code == 403


def test_coverage_gap_appears_on_the_manager_dashboard(client, database):
    """An unavailable engineer with open work and no approved handover."""
    rhea = database.users.require(ENG_RHEA)
    database.users.save(
        rhea.model_copy(update={"availability_status": AvailabilityStatus.UNAVAILABLE})
    )
    dashboard = client.get("/api/dashboard/manager", headers=as_user(MANAGER)).json()
    gap = next(item for item in dashboard["coverage"] if item["user_id"] == ENG_RHEA)
    assert gap["has_approved_handover"] is False
    assert gap["open_task_count"] == 2
    assert dashboard["summary"]["coverage_gaps"] >= 1
