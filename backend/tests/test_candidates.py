"""Backup-candidate eligibility and ranking.

Covers requirement 7 (candidates are ranked using the defined criteria) and
requirement 8 (an ineligible candidate is never assignable).
"""

from __future__ import annotations

from app.models.enums import AvailabilityStatus
from app.rules.candidates import (
    WEIGHTS,
    check_eligibility,
    explain_no_candidate,
    rank_candidates,
)

from tests.conftest import (
    ENG_ARJUN,
    ENG_LENA,
    ENG_MEI,
    ENG_RHEA,
    ENG_VICTOR,
    MANAGER,
)


def _rhea_tasks(database):
    return database.tasks.find(
        lambda task: task.owner_id == ENG_RHEA and task.is_open
    )


def test_weights_sum_to_one():
    assert round(sum(WEIGHTS.values()), 6) == 1.0


def test_ranking_uses_the_defined_criteria(database):
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    eligible = [item for item in ranked if item.eligible]
    assert [item.user_id for item in eligible[:2]] == [ENG_ARJUN, ENG_LENA]

    top = eligible[0]
    assert {item.factor for item in top.breakdown} == set(WEIGHTS)
    for item in top.breakdown:
        assert item.weight == WEIGHTS[item.factor]
        assert 0.0 <= item.raw_score <= 1.0
        assert round(item.raw_score * item.weight * 100, 2) == item.weighted_score
        assert item.explanation  # every factor is explainable
    assert round(sum(item.weighted_score for item in top.breakdown), 2) == top.total_score

    # Arjun matches all three required skills and knows the project best.
    skills = next(i for i in top.breakdown if i.factor == "relevant_skills")
    assert skills.raw_score == 1.0
    familiarity = next(i for i in top.breakdown if i.factor == "project_familiarity")
    assert familiarity.raw_score == 0.9


def test_workload_headroom_is_scored_not_gated(database):
    """Arjun is nearly saturated, so his workload factor must be close to zero
    even though he still ranks first overall."""
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    arjun = next(item for item in ranked if item.user_id == ENG_ARJUN)
    lena = next(item for item in ranked if item.user_id == ENG_LENA)
    arjun_workload = next(i for i in arjun.breakdown if i.factor == "current_workload")
    lena_workload = next(i for i in lena.breakdown if i.factor == "current_workload")
    assert arjun_workload.weighted_score < lena_workload.weighted_score


def test_unauthorized_candidate_is_ineligible(database):
    """Requirement 8: Mei has no payments authorisation."""
    tasks = _rhea_tasks(database)
    mei = database.users.require(ENG_MEI)
    reasons = check_eligibility(mei, unavailable_user_id=ENG_RHEA, tasks=tasks)
    assert any("access authorisation" in reason for reason in reasons)

    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    entry = next(item for item in ranked if item.user_id == ENG_MEI)
    assert entry.eligible is False
    assert entry.total_score == 0.0
    assert entry.breakdown == []


def test_unavailable_candidate_is_ineligible(database):
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    victor = next(item for item in ranked if item.user_id == ENG_VICTOR)
    assert victor.eligible is False
    assert any("Availability" in reason for reason in victor.ineligibility_reasons)


def test_manager_is_not_an_assignable_backup(database):
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    manager = next(item for item in ranked if item.user_id == MANAGER)
    assert manager.eligible is False


def test_required_capability_is_a_hard_gate(database):
    """pay-07 requires the security_reviewer capability."""
    task = database.tasks.require("pay-07")
    lena = database.users.require(ENG_LENA)
    reasons = check_eligibility(lena, unavailable_user_id=ENG_RHEA, tasks=[task])
    assert any("required capability" in reason for reason in reasons)


def test_eligible_candidates_always_outrank_ineligible_ones(database):
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    seen_ineligible = False
    for item in ranked:
        if not item.eligible:
            seen_ineligible = True
        else:
            assert not seen_ineligible, "an eligible candidate ranked below an ineligible one"


def test_no_eligible_candidate_is_explained(database):
    """When everyone is gated out, the manager gets a reason, not an empty list."""
    for user in database.users.list_all():
        if user.id != ENG_RHEA:
            database.users.save(
                user.model_copy(
                    update={"availability_status": AvailabilityStatus.ON_LEAVE}
                )
            )
    tasks = _rhea_tasks(database)
    ranked = rank_candidates(
        database.users.list_all(), unavailable_user_id=ENG_RHEA, tasks=tasks
    )
    assert all(not item.eligible for item in ranked)
    explanation = explain_no_candidate(ranked)
    assert explanation is not None
    assert "Manual intervention is required" in explanation


def test_protected_attributes_are_absent_from_scoring():
    """The scoring factors are work-related only."""
    assert set(WEIGHTS) == {
        "relevant_skills",
        "project_familiarity",
        "availability",
        "current_workload",
        "access_and_eligibility",
    }
