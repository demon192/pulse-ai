"""The AI capability layer.

Each capability follows the same pipeline:

    cache lookup -> Gemini call -> schema validation -> *grounding* -> cache write

Grounding is the step that keeps the model honest: any record id the model
cites must literally exist in the facts it was given, or it is dropped. Any
failure at any stage degrades to a deterministic answer rather than an error.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai import fallback
from app.ai.client import AIInvalidOutput, AIUnavailable, GeminiClient
from app.ai.prompts import (
    HANDOVER_INSTRUCTION,
    PROJECT_BRIEFING_INSTRUCTION,
    REQUEST_INTERPRETATION_INSTRUCTION,
    RISK_EXPLANATION_INSTRUCTION,
    build_prompt,
)
from app.ai.schemas import (
    HANDOVER_SECTION_HEADINGS,
    REQUIRED_HANDOVER_SECTIONS,
    HandoverBriefAI,
    HandoverSectionAI,
    HandoverSectionKey,
    ProjectBriefingAI,
    RequestInterpretationAI,
    RiskExplanationAI,
)
from app.core.clock import utc_now
from app.core.config import Settings
from app.core.logging import get_logger
from app.models.enums import EvidenceKind
from app.repositories.database import Database
from app.schemas.domain import AISummaryCache

logger = get_logger(__name__)

PayloadT = TypeVar("PayloadT", bound=BaseModel)

SOURCE_GEMINI = "gemini"
SOURCE_CACHE = "cache"
SOURCE_FALLBACK = "deterministic_fallback"


class AIResult(BaseModel):
    """An AI payload plus the provenance a reviewer needs."""

    payload: dict
    source: str
    model: str | None = None
    generated_at: Any = None
    degraded: bool = False
    notes: list[str] = []


def fingerprint(facts: dict) -> str:
    canonical = json.dumps(facts, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def collect_ids(value: Any, into: set[str] | None = None) -> set[str]:
    """Every string that appears under an ``*id``/``*ids`` key in ``facts``.

    This is the allow-list used to ground model citations.
    """
    collected = into if into is not None else set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "id" and isinstance(item, str):
                collected.add(item)
            elif key.endswith("_id") and isinstance(item, str):
                collected.add(item)
            elif key.endswith("_ids") and isinstance(item, list):
                collected.update(entry for entry in item if isinstance(entry, str))
            else:
                collect_ids(item, collected)
    elif isinstance(value, list):
        for item in value:
            collect_ids(item, collected)
    return collected


class AIService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        client: GeminiClient | None = None,
    ) -> None:
        self._settings = settings
        self._db = database
        self._client = client or GeminiClient(settings)

    # -- cache ---------------------------------------------------------
    def _cache_get(self, kind: str, subject_id: str, digest: str) -> dict | None:
        cached = self._db.ai_cache.get(f"{kind}:{subject_id}")
        if cached is None or cached.fingerprint != digest:
            return None
        ttl = timedelta(seconds=self._settings.ai_cache_ttl_seconds)
        if utc_now() - cached.generated_at > ttl:
            return None
        return cached.payload

    def _cache_put(
        self, kind: str, subject_id: str, digest: str, payload: dict, source: str
    ) -> None:
        self._db.ai_cache.save(
            AISummaryCache(
                id=f"{kind}:{subject_id}",
                kind=kind,
                subject_id=subject_id,
                fingerprint=digest,
                payload=payload,
                generated_at=utc_now(),
                generated_by=source,
            )
        )

    def invalidate(self, kind: str, subject_id: str) -> None:
        """Drop a cached summary because its underlying data changed."""
        self._db.ai_cache.delete(f"{kind}:{subject_id}")

    # -- shared pipeline -----------------------------------------------
    def _generate(
        self,
        *,
        kind: str,
        subject_id: str,
        schema: type[PayloadT],
        instruction: str,
        facts: dict,
        untrusted: list[dict[str, str]] | None,
        fallback_builder,
        grounder,
        use_cache: bool = True,
        force_refresh: bool = False,
        max_output_tokens: int = 2048,
    ) -> AIResult:
        digest = fingerprint(facts)

        if use_cache and not force_refresh:
            cached = self._cache_get(kind, subject_id, digest)
            if cached is not None:
                return AIResult(
                    payload=cached,
                    source=SOURCE_CACHE,
                    model=self._client.model_name,
                    generated_at=utc_now(),
                    degraded=False,
                    notes=["Served from the persisted summary cache."],
                )

        notes: list[str] = []
        if not self._settings.ai_configured:
            payload = fallback_builder(facts)
            return AIResult(
                payload=payload.model_dump(mode="json"),
                source=SOURCE_FALLBACK,
                model=None,
                generated_at=utc_now(),
                degraded=True,
                notes=[
                    "Gemini is not configured in this environment "
                    "(set GEMINI_API_KEY or enable Vertex AI)."
                ],
            )

        system_instruction, user_content = build_prompt(
            task_instruction=instruction, facts=facts, untrusted=untrusted
        )
        try:
            result = self._client.generate_structured(
                schema=schema,
                system_instruction=system_instruction,
                user_content=user_content,
                max_output_tokens=max_output_tokens,
            )
        except (AIUnavailable, AIInvalidOutput) as exc:
            logger.warning("AI capability '%s' degraded: %s", kind, type(exc).__name__)
            payload = fallback_builder(facts)
            return AIResult(
                payload=payload.model_dump(mode="json"),
                source=SOURCE_FALLBACK,
                model=self._client.model_name,
                generated_at=utc_now(),
                degraded=True,
                notes=[f"Gemini output was unusable ({type(exc).__name__}); "
                       "showing a deterministic summary of the stored records."],
            )

        grounded, grounding_notes = grounder(result, facts)
        notes.extend(grounding_notes)
        payload_dict = grounded.model_dump(mode="json")
        if use_cache:
            self._cache_put(kind, subject_id, digest, payload_dict, SOURCE_GEMINI)
        return AIResult(
            payload=payload_dict,
            source=SOURCE_GEMINI,
            model=self._client.model_name,
            generated_at=utc_now(),
            degraded=False,
            notes=notes,
        )

    # -- grounding helpers ----------------------------------------------
    @staticmethod
    def _filter_source_ids(
        items: list, allowed: set[str], notes: list[str], label: str
    ) -> None:
        dropped = 0
        for item in items:
            original = list(getattr(item, "source_ids", []))
            kept = [source_id for source_id in original if source_id in allowed]
            dropped += len(original) - len(kept)
            item.source_ids = kept
        if dropped:
            notes.append(
                f"Dropped {dropped} unverifiable record reference(s) from {label}."
            )

    # -- capability 1: project briefing ----------------------------------
    def project_briefing(
        self, *, project_id: str, facts: dict, untrusted: list[dict[str, str]], force_refresh: bool = False
    ) -> AIResult:
        def ground(result: ProjectBriefingAI, facts_: dict) -> tuple[ProjectBriefingAI, list[str]]:
            allowed = collect_ids(facts_)
            notes: list[str] = []
            self._filter_source_ids(result.key_risks, allowed, notes, "key risks")
            self._filter_source_ids(result.blockers, allowed, notes, "blockers")
            # The model may only describe findings the rules engine produced.
            known_titles = {
                finding.get("title") for finding in facts_.get("risk_findings", [])
            }
            if known_titles:
                extra = [
                    note for note in result.key_risks if note.title not in known_titles
                ]
                for note in extra:
                    note.evidence_kind = EvidenceKind.HYPOTHESIS
                if extra:
                    notes.append(
                        f"{len(extra)} risk note(s) did not match a rules-engine "
                        "finding and were relabelled as hypotheses."
                    )
            return result, notes

        return self._generate(
            kind="project_briefing",
            subject_id=project_id,
            schema=ProjectBriefingAI,
            instruction=PROJECT_BRIEFING_INSTRUCTION,
            facts=facts,
            untrusted=untrusted,
            fallback_builder=fallback.project_briefing,
            grounder=ground,
            force_refresh=force_refresh,
        )

    # -- capability 2: request interpretation ----------------------------
    def interpret_request(
        self, *, request_id: str, facts: dict, untrusted: list[dict[str, str]]
    ) -> AIResult:
        def ground(
            result: RequestInterpretationAI, facts_: dict
        ) -> tuple[RequestInterpretationAI, list[str]]:
            notes: list[str] = []
            candidate_ids = {
                task.get("id") for task in facts_.get("candidate_tasks", [])
            }
            if result.suggested_task_id and result.suggested_task_id not in candidate_ids:
                notes.append(
                    "The suggested task id was not among the engineer's tasks and was discarded."
                )
                result.suggested_task_id = ""
            return result, notes

        return self._generate(
            kind="request_interpretation",
            subject_id=request_id,
            schema=RequestInterpretationAI,
            instruction=REQUEST_INTERPRETATION_INSTRUCTION,
            facts=facts,
            untrusted=untrusted,
            fallback_builder=fallback.request_interpretation,
            grounder=ground,
        )

    # -- capability 3: handover brief ------------------------------------
    def handover_brief(
        self,
        *,
        handover_id: str,
        task_id: str,
        facts: dict,
        untrusted: list[dict[str, str]],
    ) -> AIResult:
        def ground(result: HandoverBriefAI, facts_: dict) -> tuple[HandoverBriefAI, list[str]]:
            allowed = collect_ids(facts_)
            notes: list[str] = []
            self._filter_source_ids(result.sections, allowed, notes, "handover sections")

            # Every required section must be present. Fill gaps deterministically
            # rather than returning an incomplete brief.
            provided = {section.key: section for section in result.sections}
            deterministic = {
                section.key: section for section in fallback.handover_brief(facts_).sections
            }
            ordered: list[HandoverSectionAI] = []
            filled: list[str] = []
            for key in REQUIRED_HANDOVER_SECTIONS:
                section_key = HandoverSectionKey(key)
                section = provided.get(section_key)
                if section is None or not section.content.strip():
                    section = deterministic[section_key]
                    filled.append(HANDOVER_SECTION_HEADINGS[key])
                ordered.append(section)
            result.sections = ordered
            if filled:
                notes.append(
                    "Filled from stored records because the model omitted them: "
                    + ", ".join(filled)
                    + "."
                )
            if not result.missing_information:
                result.missing_information = [
                    "The model did not flag any gaps. Confirm progress directly "
                    "with the project team before relying on this brief."
                ]
            return result, notes

        return self._generate(
            kind="handover_brief",
            subject_id=f"{handover_id}:{task_id}",
            schema=HandoverBriefAI,
            instruction=HANDOVER_INSTRUCTION,
            facts=facts,
            untrusted=untrusted,
            fallback_builder=fallback.handover_brief,
            grounder=ground,
            max_output_tokens=4096,
        )

    # -- capability 4: risk explanation ----------------------------------
    def explain_risk(self, *, finding_id: str, facts: dict) -> AIResult:
        def ground(result: RiskExplanationAI, facts_: dict) -> tuple[RiskExplanationAI, list[str]]:
            allowed = collect_ids(facts_)
            notes: list[str] = []
            self._filter_source_ids(result.statements, allowed, notes, "statements")
            return result, notes

        return self._generate(
            kind="risk_explanation",
            subject_id=finding_id,
            schema=RiskExplanationAI,
            instruction=RISK_EXPLANATION_INSTRUCTION,
            facts=facts,
            untrusted=None,
            fallback_builder=fallback.risk_explanation,
            grounder=ground,
            max_output_tokens=1024,
        )
