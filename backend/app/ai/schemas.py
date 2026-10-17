"""Schemas that constrain every Gemini response.

These are passed to the model as a response schema *and* re-validated on the
way back. Fields avoid optionals and free-form maps because those translate
poorly to the model's JSON schema dialect — "unknown" is expressed as an empty
string or empty list instead.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EvidenceKind, Priority, RequestCategory


class AIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class HandoverSectionKey(StrEnum):
    """The eleven required sections of a handover brief."""

    OBJECTIVE = "objective"
    CURRENT_STATUS = "current_status"
    WORK_COMPLETED = "work_completed"
    FILES_AND_LINKS = "files_and_links"
    DECISIONS_MADE = "decisions_made"
    OPEN_QUESTIONS = "open_questions"
    DEPENDENCIES = "dependencies"
    KNOWN_BLOCKERS = "known_blockers"
    NEXT_STEPS = "next_steps"
    CONTACTS = "contacts"
    MISSING_INFORMATION = "missing_information"


HANDOVER_SECTION_HEADINGS: dict[str, str] = {
    HandoverSectionKey.OBJECTIVE: "Task and project objective",
    HandoverSectionKey.CURRENT_STATUS: "Current status",
    HandoverSectionKey.WORK_COMPLETED: "Work completed",
    HandoverSectionKey.FILES_AND_LINKS: "Relevant files, links and documents",
    HandoverSectionKey.DECISIONS_MADE: "Decisions already made",
    HandoverSectionKey.OPEN_QUESTIONS: "Unresolved questions",
    HandoverSectionKey.DEPENDENCIES: "Dependencies and affected tasks",
    HandoverSectionKey.KNOWN_BLOCKERS: "Known blockers",
    HandoverSectionKey.NEXT_STEPS: "Suggested next steps",
    HandoverSectionKey.CONTACTS: "Relevant contacts and reviewers",
    HandoverSectionKey.MISSING_INFORMATION: "Missing information to confirm",
}

REQUIRED_HANDOVER_SECTIONS: tuple[str, ...] = tuple(HANDOVER_SECTION_HEADINGS)


class AIStatementOut(AIModel):
    text: str
    evidence_kind: EvidenceKind
    source_ids: list[str] = Field(default_factory=list)


class AIRiskNote(AIModel):
    title: str
    explanation: str
    evidence_kind: EvidenceKind
    source_ids: list[str] = Field(default_factory=list)


class ProjectBriefingAI(AIModel):
    """Capability 1 — project briefing."""

    progress_summary: str
    key_risks: list[AIRiskNote] = Field(default_factory=list)
    blockers: list[AIRiskNote] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class RequestInterpretationAI(AIModel):
    """Capability 2 — interpreting an engineer's written request."""

    summary: str
    suggested_category: RequestCategory
    suggested_priority: Priority
    # Empty string when the model cannot ground the request to a known task.
    suggested_task_id: str = ""
    suggested_next_steps: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)


class HandoverSectionAI(AIModel):
    key: HandoverSectionKey
    content: str
    evidence_kind: EvidenceKind
    source_ids: list[str] = Field(default_factory=list)


class HandoverBriefAI(AIModel):
    """Capability 3 — handover synthesis."""

    sections: list[HandoverSectionAI] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class RiskExplanationAI(AIModel):
    """Capability 4 — explaining a rules-engine finding in plain language."""

    explanation: str
    statements: list[AIStatementOut] = Field(default_factory=list)
