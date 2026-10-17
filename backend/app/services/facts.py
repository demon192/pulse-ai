"""Builders for the ``<facts>`` payloads handed to Gemini.

Two rules hold throughout:

* Only records the requesting user is authorised to read enter a payload.
* Free-text written by people (task updates, request descriptions, document
  summaries) is returned separately as *untrusted* content, never mixed into
  the trusted facts block.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import days_until, hours_between
from app.models.enums import TaskStatus
from app.repositories.database import Database
from app.rules.dependencies import DependencyGraph
from app.schemas.analysis import ProjectHealthReport, RiskFinding
from app.schemas.domain import (
    ActionItem,
    Project,
    SupportRequest,
    Task,
    User,
)


def _task_fact(task: Task, owner_name: str) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "owner_name": owner_name,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "next_step": task.next_step,
        "blocked_reason": task.blocked_reason,
        "dependency_ids": list(task.dependency_ids),
    }


def project_briefing_facts(
    *,
    report: ProjectHealthReport,
    project: Project,
    tasks: list[Task],
    actions: list[ActionItem],
    requests: list[SupportRequest],
    user_names: dict[str, str],
    now: datetime,
) -> tuple[dict, list[dict[str, str]]]:
    """Facts and untrusted text for the project-briefing capability."""
    facts = {
        "generated_at": now.isoformat(),
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "target_date": project.target_date.isoformat(),
        },
        "task_counts": {
            "total": report.total_tasks,
            "completed": report.completed_tasks,
            "in_progress": report.in_progress_tasks,
            "blocked": report.blocked_tasks,
            "overdue": report.overdue_tasks,
        },
        "tasks": [
            _task_fact(task, user_names.get(task.owner_id or "", "Unassigned"))
            for task in tasks
        ],
        "milestones": [
            {
                "id": milestone.milestone_id,
                "name": milestone.name,
                "target_date": milestone.target_date.isoformat(),
                "days_remaining": milestone.days_remaining,
                "at_risk": milestone.at_risk,
                "reasons": milestone.reasons,
            }
            for milestone in report.milestones
        ],
        "risk_findings": [_finding_fact(finding) for finding in report.risks],
        "open_actions": [
            {
                "id": action.id,
                "title": action.title,
                "type": action.type.value,
                "priority": action.priority.value,
                "task_id": action.task_id,
                "days_waiting": round(hours_between(action.created_at, now) / 24, 2),
                "due_date": action.due_date.isoformat() if action.due_date else None,
            }
            for action in actions
            if action.is_open and action.project_id == project.id
        ],
        "open_requests": [
            {
                "id": request.id,
                "title": request.title,
                "category": request.category.value,
                "priority": request.priority.value,
                "task_id": request.task_id,
            }
            for request in requests
            if request.is_open and request.project_id == project.id
        ],
    }

    untrusted: list[dict[str, str]] = [
        {"kind": "support_request_description", "id": request.id, "body": request.description}
        for request in requests
        if request.is_open and request.project_id == project.id
    ]
    return facts, untrusted


def _finding_fact(finding: RiskFinding) -> dict:
    return {
        "id": finding.id,
        "kind": finding.kind.value,
        "severity": finding.severity,
        "title": finding.title,
        "summary": finding.summary,
        "task_ids": list(finding.task_ids),
        "downstream_task_ids": list(finding.downstream_task_ids),
        "milestone_ids": list(finding.milestone_ids),
        "action_ids": list(finding.action_ids),
        "evidence": [
            {
                "label": item.label,
                "detail": item.detail,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
            }
            for item in finding.evidence
        ],
        "suggested_actions": list(finding.suggested_actions),
    }


def risk_explanation_facts(
    *, finding: RiskFinding, tasks: dict[str, Task], user_names: dict[str, str], now: datetime
) -> dict:
    related_ids = set(finding.task_ids) | set(finding.downstream_task_ids)
    return {
        "generated_at": now.isoformat(),
        "finding": _finding_fact(finding),
        "related_tasks": [
            _task_fact(tasks[task_id], user_names.get(tasks[task_id].owner_id or "", "Unassigned"))
            for task_id in sorted(related_ids)
            if task_id in tasks
        ],
    }


def request_interpretation_facts(
    *,
    request: SupportRequest,
    engineer: User,
    project: Project,
    candidate_tasks: list[Task],
    now: datetime,
) -> tuple[dict, list[dict[str, str]]]:
    facts = {
        "generated_at": now.isoformat(),
        "engineer": {"id": engineer.id, "name": engineer.name},
        "project": {"id": project.id, "name": project.name, "description": project.description},
        "stated_category": request.category.value,
        "stated_priority": request.priority.value,
        "linked_task_id": request.task_id or "",
        "candidate_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task in candidate_tasks
        ],
    }
    untrusted = [
        {"kind": "request_title", "id": request.id, "body": request.title},
        {"kind": "request_description", "id": request.id, "body": request.description},
    ]
    if request.engineer_context_note:
        untrusted.append(
            {
                "kind": "engineer_correction",
                "id": request.id,
                "body": request.engineer_context_note,
            }
        )
    return facts, untrusted


def handover_task_facts(
    database: Database,
    *,
    task: Task,
    graph: DependencyGraph,
    unavailable_user: User,
    handover_notes: str | None,
    now: datetime,
) -> tuple[dict, list[dict[str, str]], list[str]]:
    """Facts, untrusted text and detected information gaps for one task.

    The unavailable engineer's reason for being away is never included.
    """
    project = database.projects.require(task.project_id)
    dependencies = graph.direct_dependencies(task.id)
    dependents = graph.downstream(task.id)

    documents = database.documents.find(
        lambda doc: doc.project_id == task.project_id
        and (task.id in doc.task_ids or doc.id in task.related_document_ids)
    )
    decisions = database.decisions.find(
        lambda item: item.task_id == task.id
        or (item.project_id == task.project_id and item.task_id is None)
    )
    updates = database.task_updates.find(lambda item: item.task_id == task.id)
    updates.sort(key=lambda item: item.created_at, reverse=True)
    open_requests = database.requests.find(
        lambda item: item.task_id == task.id and item.is_open
    )
    pending_actions = database.actions.find(
        lambda item: item.task_id == task.id and item.is_open
    )
    milestones = database.milestones.find(
        lambda item: task.id in item.task_ids and not item.completed
    )

    reviewers = {
        user.id: user
        for user in database.users.list_all()
        if user.id != unavailable_user.id
        and (user.id == project.manager_id or user.id in project.team_member_ids)
    }

    facts = {
        "generated_at": now.isoformat(),
        "engineer": {"id": unavailable_user.id, "name": unavailable_user.name},
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "next_step": task.next_step,
            "blocked_reason": task.blocked_reason,
            "estimated_effort": task.estimated_effort,
            "remaining_effort": task.remaining_effort,
            "required_skills": list(task.required_skills),
        },
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "target_date": project.target_date.isoformat(),
        },
        "dependencies": [
            {"id": item.id, "title": item.title, "status": item.status.value}
            for item in dependencies
        ],
        "dependents": [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status.value,
                "priority": item.priority.value,
            }
            for item in dependents
        ],
        "documents": [
            {"id": doc.id, "title": doc.title, "doc_type": doc.doc_type, "url": doc.url}
            for doc in documents
        ],
        "decisions": [
            {
                "id": item.id,
                "title": item.title,
                "decision": item.decision,
                "decided_at": item.decided_at.isoformat(),
            }
            for item in decisions
        ],
        "pending_actions": [
            {
                "id": item.id,
                "title": item.title,
                "type": item.type.value,
                "owner_name": database.users.get(item.owner_id).name
                if database.users.get(item.owner_id)
                else item.owner_id,
            }
            for item in pending_actions
        ],
        "open_requests": [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category.value,
                "status": item.status.value,
            }
            for item in open_requests
        ],
        "milestones": [
            {
                "id": item.id,
                "name": item.name,
                "target_date": item.target_date.isoformat(),
                "days_remaining": round(days_until(item.target_date, now=now) or 0.0, 2),
            }
            for item in milestones
        ],
        "contacts": [
            {
                "id": user.id,
                "name": user.name,
                "role": "project manager" if user.id == project.manager_id else "team member",
            }
            for user in reviewers.values()
        ],
        "task_update_count": len(updates),
        "handover_notes_provided": bool(handover_notes),
    }

    untrusted: list[dict[str, str]] = [
        {"kind": "task_update", "id": update.id, "body": update.body}
        for update in updates[:8]
    ]
    untrusted.extend(
        {"kind": "document_summary", "id": doc.id, "body": doc.summary or ""}
        for doc in documents
        if doc.summary
    )
    if handover_notes:
        untrusted.append(
            {"kind": "handover_notes", "id": task.id, "body": handover_notes}
        )

    missing = detect_missing_information(
        task=task,
        update_count=len(updates),
        document_count=len(documents),
        decision_count=len(decisions),
        handover_notes=handover_notes,
        now=now,
        last_update_at=updates[0].created_at if updates else None,
    )
    facts["missing_information"] = missing
    return facts, untrusted, missing


def detect_missing_information(
    *,
    task: Task,
    update_count: int,
    document_count: int,
    decision_count: int,
    handover_notes: str | None,
    now: datetime,
    last_update_at: datetime | None,
    stale_update_days: float = 7.0,
) -> list[str]:
    """Deterministically list what a backup engineer cannot learn from records."""
    gaps: list[str] = []
    if not task.next_step:
        gaps.append(f"No next step is recorded on '{task.title}'.")
    if task.status is TaskStatus.BLOCKED and not task.blocked_reason:
        gaps.append(f"'{task.title}' is marked blocked with no reason recorded.")
    if update_count == 0:
        gaps.append(f"No progress updates have been written for '{task.title}'.")
    elif last_update_at is not None and hours_between(last_update_at, now) / 24 > stale_update_days:
        gaps.append(
            f"The latest progress update on '{task.title}' is "
            f"{hours_between(last_update_at, now) / 24:.0f} days old."
        )
    if document_count == 0:
        gaps.append(f"No documents or links are attached to '{task.title}'.")
    if decision_count == 0:
        gaps.append(f"No decisions are recorded for '{task.title}'.")
    if not handover_notes:
        gaps.append(
            "The engineer did not write handover notes, so this brief is "
            "assembled from project records only."
        )
    if task.remaining_effort is None:
        gaps.append(f"Remaining effort is not estimated for '{task.title}'.")
    return gaps
