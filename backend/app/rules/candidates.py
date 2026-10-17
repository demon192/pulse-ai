"""Backup-candidate eligibility and ranking.

Two stages, in this order:

1. **Eligibility gates** — hard requirements (authorisation, availability,
   required capability). A candidate that fails any gate is returned with
   ``eligible=False`` and can never be selected for an assignment. The gate is
   re-checked at assignment time in :mod:`app.services.handovers`.
2. **Ranking** — a weighted, explainable score over work-related data only.

Deliberately excluded from both stages: protected personal characteristics,
inferred personality, private leave reasons and performance scores.
"""

from __future__ import annotations

from app.models.enums import AvailabilityStatus, Role
from app.schemas.domain import (
    CandidateRecommendation,
    CandidateScoreBreakdown,
    Task,
    User,
)

# Initial, tunable weights — not validated industry standards.
WEIGHTS: dict[str, float] = {
    "relevant_skills": 0.30,
    "project_familiarity": 0.25,
    "availability": 0.20,
    "current_workload": 0.15,
    "access_and_eligibility": 0.10,
}

ASSIGNABLE_AVAILABILITY = {
    AvailabilityStatus.AVAILABLE: 1.0,
    AvailabilityStatus.LIMITED: 0.5,
}

# Above this utilisation a candidate is treated as having no headroom at all.
WORKLOAD_SATURATION = 1.0


def check_eligibility(
    candidate: User,
    *,
    unavailable_user_id: str,
    tasks: list[Task],
) -> list[str]:
    """Return the reasons ``candidate`` cannot take over ``tasks``.

    An empty list means eligible. This is the single source of truth for
    assignability and is called both when ranking and when a manager confirms a
    handover.
    """
    reasons: list[str] = []

    if candidate.id == unavailable_user_id:
        reasons.append("Candidate is the unavailable engineer.")
    if candidate.role is not Role.ENGINEER:
        reasons.append("Only engineers can be assigned task ownership.")
    if candidate.availability_status not in ASSIGNABLE_AVAILABILITY:
        reasons.append(
            f"Availability is '{candidate.availability_status.value}', not assignable."
        )

    authorized = set(candidate.authorized_project_ids)
    unauthorised_projects = sorted(
        {task.project_id for task in tasks} - authorized
    )
    if unauthorised_projects:
        reasons.append(
            "No access authorisation for project(s): "
            + ", ".join(unauthorised_projects)
        )

    missing_permissions = sorted(
        {
            task.required_permission
            for task in tasks
            if task.required_permission
            and task.required_permission not in candidate.permissions
        }
    )
    if missing_permissions:
        reasons.append(
            "Missing required capability: " + ", ".join(missing_permissions)
        )

    return reasons


def _skill_score(candidate: User, tasks: list[Task]) -> tuple[float, str]:
    required = {skill.lower() for task in tasks for skill in task.required_skills}
    if not required:
        return 0.5, "No skills recorded on the affected tasks; scored neutral."
    held = {skill.lower() for skill in candidate.skills}
    matched = required & held
    score = len(matched) / len(required)
    matched_label = ", ".join(sorted(matched)) or "none"
    return score, (
        f"Matches {len(matched)}/{len(required)} required skill(s): {matched_label}."
    )


def _familiarity_score(candidate: User, tasks: list[Task]) -> tuple[float, str]:
    project_ids = sorted({task.project_id for task in tasks})
    if not project_ids:
        return 0.0, "No affected projects."
    scores = [candidate.project_familiarity.get(pid, 0.0) for pid in project_ids]
    average = sum(scores) / len(scores)
    detail = ", ".join(
        f"{pid}: {candidate.project_familiarity.get(pid, 0.0):.0%}" for pid in project_ids
    )
    return average, f"Recorded project familiarity — {detail}."


def _availability_score(candidate: User) -> tuple[float, str]:
    score = ASSIGNABLE_AVAILABILITY.get(candidate.availability_status, 0.0)
    return score, f"Availability status '{candidate.availability_status.value}'."


def _workload_score(candidate: User) -> tuple[float, str]:
    utilisation = candidate.utilisation
    headroom = max(0.0, WORKLOAD_SATURATION - utilisation)
    return headroom, (
        f"Assigned {candidate.assigned_workload:.0f}h of "
        f"{candidate.weekly_capacity:.0f}h weekly capacity ({utilisation:.0%} used)."
    )


def _access_score(candidate: User, tasks: list[Task]) -> tuple[float, str]:
    """Breadth of authorisation beyond the minimum gate."""
    project_ids = {task.project_id for task in tasks}
    if not project_ids:
        return 0.0, "No affected projects."
    authorized = project_ids & set(candidate.authorized_project_ids)
    base = len(authorized) / len(project_ids)
    required_permissions = {
        task.required_permission for task in tasks if task.required_permission
    }
    if required_permissions:
        held = required_permissions & set(candidate.permissions)
        permission_ratio = len(held) / len(required_permissions)
        score = (base + permission_ratio) / 2
        detail = (
            f"Authorised on {len(authorized)}/{len(project_ids)} project(s) and holds "
            f"{len(held)}/{len(required_permissions)} required capability flag(s)."
        )
    else:
        score = base
        detail = f"Authorised on {len(authorized)}/{len(project_ids)} affected project(s)."
    return score, detail


_FACTOR_FUNCTIONS = {
    "relevant_skills": lambda candidate, tasks: _skill_score(candidate, tasks),
    "project_familiarity": lambda candidate, tasks: _familiarity_score(candidate, tasks),
    "availability": lambda candidate, tasks: _availability_score(candidate),
    "current_workload": lambda candidate, tasks: _workload_score(candidate),
    "access_and_eligibility": lambda candidate, tasks: _access_score(candidate, tasks),
}


def score_candidate(
    candidate: User,
    *,
    unavailable_user_id: str,
    tasks: list[Task],
) -> CandidateRecommendation:
    """Score one candidate, enforcing eligibility gates before ranking."""
    ineligibility = check_eligibility(
        candidate, unavailable_user_id=unavailable_user_id, tasks=tasks
    )
    if ineligibility:
        return CandidateRecommendation(
            user_id=candidate.id,
            user_name=candidate.name,
            eligible=False,
            ineligibility_reasons=ineligibility,
            total_score=0.0,
            breakdown=[],
            summary=(
                f"{candidate.name} cannot be assigned: " + " ".join(ineligibility)
            ),
        )

    breakdown: list[CandidateScoreBreakdown] = []
    for factor, weight in WEIGHTS.items():
        raw_score, explanation = _FACTOR_FUNCTIONS[factor](candidate, tasks)
        raw_score = max(0.0, min(1.0, raw_score))
        breakdown.append(
            CandidateScoreBreakdown(
                factor=factor,
                weight=weight,
                raw_score=round(raw_score, 4),
                weighted_score=round(raw_score * weight * 100, 2),
                explanation=explanation,
            )
        )

    total = round(sum(item.weighted_score for item in breakdown), 2)
    top_factors = sorted(breakdown, key=lambda item: -item.weighted_score)[:2]
    summary = (
        f"Score {total:.0f}/100. Strongest factors: "
        + "; ".join(f"{item.factor} ({item.weighted_score:.0f} pts)" for item in top_factors)
        + "."
    )
    return CandidateRecommendation(
        user_id=candidate.id,
        user_name=candidate.name,
        eligible=True,
        total_score=total,
        breakdown=breakdown,
        summary=summary,
    )


def rank_candidates(
    users: list[User],
    *,
    unavailable_user_id: str,
    tasks: list[Task],
    include_ineligible: bool = True,
) -> list[CandidateRecommendation]:
    """Rank every candidate. Eligible candidates always sort above ineligible ones."""
    recommendations = [
        score_candidate(user, unavailable_user_id=unavailable_user_id, tasks=tasks)
        for user in users
        if user.id != unavailable_user_id
    ]
    if not include_ineligible:
        recommendations = [item for item in recommendations if item.eligible]
    recommendations.sort(
        key=lambda item: (not item.eligible, -item.total_score, item.user_id)
    )
    return recommendations


def explain_no_candidate(
    recommendations: list[CandidateRecommendation],
) -> str | None:
    """Explain why no assignable candidate exists, for the manager's review."""
    if any(item.eligible for item in recommendations):
        return None
    if not recommendations:
        return (
            "No other team members are recorded for the affected projects. "
            "Manual intervention is required: identify a backup outside the "
            "current team or re-scope the work."
        )
    grouped: dict[str, int] = {}
    for item in recommendations:
        for reason in item.ineligibility_reasons:
            grouped[reason] = grouped.get(reason, 0) + 1
    summary = "; ".join(
        f"{reason} ({count} candidate(s))" for reason, count in sorted(grouped.items())
    )
    return (
        "No eligible backup candidate was found. Blocking reasons: "
        f"{summary}. Manual intervention is required — grant project access, "
        "re-scope the work, or extend the deadline."
    )
