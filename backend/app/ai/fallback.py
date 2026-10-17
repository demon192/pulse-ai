"""Deterministic replacements for every AI capability.

When Gemini is unconfigured, unreachable or returns unusable output, these
builders produce an honest, lower-fidelity answer from the same facts payload.
Nothing here guesses: it restates what the rules engine already established.
"""

from __future__ import annotations

from app.ai.schemas import (
    HANDOVER_SECTION_HEADINGS,
    AIRiskNote,
    HandoverBriefAI,
    HandoverSectionAI,
    HandoverSectionKey,
    ProjectBriefingAI,
    RequestInterpretationAI,
    RiskExplanationAI,
)
from app.models.enums import EvidenceKind, Priority, RequestCategory


def project_briefing(facts: dict) -> ProjectBriefingAI:
    project = facts.get("project", {})
    counts = facts.get("task_counts", {})
    findings = facts.get("risk_findings", [])

    summary = (
        f"{project.get('name', 'This project')} has "
        f"{counts.get('total', 0)} recorded task(s): "
        f"{counts.get('completed', 0)} completed, "
        f"{counts.get('in_progress', 0)} in progress, "
        f"{counts.get('blocked', 0)} blocked and "
        f"{counts.get('overdue', 0)} past their due date. "
        f"{len(findings)} rules-engine finding(s) need review."
    )

    key_risks = [
        AIRiskNote(
            title=finding.get("title", "Risk"),
            explanation=finding.get("summary", ""),
            evidence_kind=EvidenceKind.RULE_DERIVED,
            source_ids=list(finding.get("task_ids", []))
            + list(finding.get("action_ids", [])),
        )
        for finding in findings[:6]
    ]
    blockers = [
        AIRiskNote(
            title=task.get("title", "Blocked task"),
            explanation=task.get("blocked_reason") or "Marked blocked; no reason recorded.",
            evidence_kind=EvidenceKind.VERIFIED_FACT,
            source_ids=[task.get("id", "")],
        )
        for task in facts.get("tasks", [])
        if task.get("status") == "blocked"
    ]

    recommended: list[str] = []
    for finding in findings[:4]:
        recommended.extend(finding.get("suggested_actions", [])[:1])
    if not recommended:
        recommended = ["No rules-engine findings require action right now."]

    return ProjectBriefingAI(
        progress_summary=summary,
        key_risks=key_risks,
        blockers=blockers,
        recommended_actions=recommended,
        uncertainties=[
            "This briefing was generated without the language model, so it "
            "restates rule findings rather than interpreting them."
        ],
    )


def request_interpretation(facts: dict) -> RequestInterpretationAI:
    stated_category = facts.get("stated_category") or RequestCategory.OTHER.value
    stated_priority = facts.get("stated_priority") or Priority.MEDIUM.value
    task_id = facts.get("linked_task_id") or ""
    return RequestInterpretationAI(
        summary=(
            "Automatic interpretation is unavailable. The request was recorded "
            "exactly as the engineer submitted it and needs a human read."
        ),
        suggested_category=RequestCategory(stated_category),
        suggested_priority=Priority(stated_priority),
        suggested_task_id=task_id,
        suggested_next_steps=[
            "Read the engineer's description and acknowledge the request.",
        ],
        missing_context=[
            "The language model was unavailable, so no additional context "
            "questions were generated."
        ],
    )


def handover_brief(facts: dict) -> HandoverBriefAI:
    """Build all eleven sections straight from authorised records."""
    task = facts.get("task", {})
    project = facts.get("project", {})
    dependencies = facts.get("dependencies", [])
    dependents = facts.get("dependents", [])
    documents = facts.get("documents", [])
    decisions = facts.get("decisions", [])
    pending_actions = facts.get("pending_actions", [])
    open_requests = facts.get("open_requests", [])
    contacts = facts.get("contacts", [])
    completed_dependencies = [
        item for item in dependencies if item.get("status") == "completed"
    ]
    update_count = facts.get("task_update_count", 0)

    def section(
        key: HandoverSectionKey,
        content: str,
        kind: EvidenceKind = EvidenceKind.VERIFIED_FACT,
        source_ids: list[str] | None = None,
    ) -> HandoverSectionAI:
        return HandoverSectionAI(
            key=key,
            content=content,
            evidence_kind=kind,
            source_ids=source_ids or [],
        )

    not_recorded = "Not recorded in TeamPulse."

    sections = [
        section(
            HandoverSectionKey.OBJECTIVE,
            f"{task.get('title', 'Task')} — {task.get('description', not_recorded)} "
            f"Part of project '{project.get('name', 'unknown')}': "
            f"{project.get('description', '')}".strip(),
            source_ids=[task.get("id", ""), project.get("id", "")],
        ),
        section(
            HandoverSectionKey.CURRENT_STATUS,
            f"Status '{task.get('status', 'unknown')}', priority "
            f"'{task.get('priority', 'unknown')}'"
            + (f", due {task.get('due_date')}" if task.get("due_date") else ", no due date recorded")
            + ".",
            source_ids=[task.get("id", "")],
        ),
        section(
            HandoverSectionKey.WORK_COMPLETED,
            (
                f"{len(completed_dependencies)} dependency task(s) are complete: "
                + ", ".join(item.get("title", "") for item in completed_dependencies)
                + f". {update_count} progress update(s) are on file."
            )
            if completed_dependencies or update_count
            else "No completed dependencies or progress updates are on file. "
            "The incoming engineer must confirm what has actually been done.",
            source_ids=[item.get("id", "") for item in completed_dependencies],
        ),
        section(
            HandoverSectionKey.FILES_AND_LINKS,
            "; ".join(
                f"{doc.get('title')} ({doc.get('url') or 'no link recorded'})"
                for doc in documents
            )
            or not_recorded,
            source_ids=[doc.get("id", "") for doc in documents],
        ),
        section(
            HandoverSectionKey.DECISIONS_MADE,
            "; ".join(
                f"{item.get('title')}: {item.get('decision')}" for item in decisions
            )
            or not_recorded,
            source_ids=[item.get("id", "") for item in decisions],
        ),
        section(
            HandoverSectionKey.OPEN_QUESTIONS,
            "; ".join(
                f"{item.get('title')} (status {item.get('status')})"
                for item in open_requests
            )
            or "No unresolved support requests are linked to this task.",
            source_ids=[item.get("id", "") for item in open_requests],
        ),
        section(
            HandoverSectionKey.DEPENDENCIES,
            (
                "Depends on: "
                + (", ".join(f"{d.get('title')} [{d.get('status')}]" for d in dependencies) or "nothing")
                + ". Tasks waiting on this one: "
                + (", ".join(f"{d.get('title')} [{d.get('status')}]" for d in dependents) or "none")
                + "."
            ),
            kind=EvidenceKind.RULE_DERIVED,
            source_ids=[d.get("id", "") for d in dependencies + dependents],
        ),
        section(
            HandoverSectionKey.KNOWN_BLOCKERS,
            task.get("blocked_reason") or "No blocker reason recorded on this task.",
            source_ids=[task.get("id", "")],
        ),
        section(
            HandoverSectionKey.NEXT_STEPS,
            task.get("next_step")
            or "No next step recorded. Confirm the immediate next action with the manager.",
            kind=EvidenceKind.RECOMMENDATION,
            source_ids=[task.get("id", "")],
        ),
        section(
            HandoverSectionKey.CONTACTS,
            "; ".join(
                f"{contact.get('name')} ({contact.get('role')})" for contact in contacts
            )
            or not_recorded,
            source_ids=[contact.get("id", "") for contact in contacts],
        ),
        section(
            HandoverSectionKey.MISSING_INFORMATION,
            "; ".join(facts.get("missing_information", []))
            or "No gaps detected in the recorded data.",
            kind=EvidenceKind.RULE_DERIVED,
        ),
    ]

    missing = list(facts.get("missing_information", []))
    if pending_actions:
        missing.append(
            f"{len(pending_actions)} pending approval(s) still sit with the manager."
        )
    missing.append(
        "Generated without the language model: sections restate stored records "
        "and have not been synthesised."
    )
    return HandoverBriefAI(sections=sections, missing_information=missing)


def risk_explanation(facts: dict) -> RiskExplanationAI:
    finding = facts.get("finding", {})
    evidence = finding.get("evidence", [])
    detail = " ".join(
        f"{item.get('label')}: {item.get('detail')}" for item in evidence[:4]
    )
    return RiskExplanationAI(
        explanation=(
            f"{finding.get('title', 'Finding')} — {finding.get('summary', '')} "
            f"Evidence: {detail}"
        ).strip(),
        statements=[],
    )


def section_headings() -> dict[str, str]:
    return dict(HANDOVER_SECTION_HEADINGS)
