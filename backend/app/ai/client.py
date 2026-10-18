"""Thin, defensive wrapper around the Gemini SDK.

Responsibilities kept here on purpose: client construction, timeouts, retries,
JSON extraction and schema validation. Business meaning lives in
:mod:`app.ai.service`.
"""

from __future__ import annotations

import json
import random
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Substrings that indicate a retry may succeed.
_TRANSIENT_MARKERS = (
    "429",
    "resource_exhausted",
    "rate limit",
    "deadline",
    "timeout",
    "unavailable",
    "503",
    "500",
    "internal error",
)


class AIUnavailable(RuntimeError):
    """The model could not be reached, or refused, after all retries."""


class AIInvalidOutput(ValueError):
    """The model replied, but the payload did not satisfy the schema."""


class AIOutputTruncated(AIInvalidOutput):
    """The reply was cut off by the output-token limit, so the JSON is partial.

    Distinct from a malformed reply: the same call can succeed with a larger
    budget, so the retry loop raises the limit rather than giving up.
    """


def _is_transient(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of a model reply, tolerating code fences."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise AIInvalidOutput("Model reply contained no JSON object") from exc
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as inner:
            raise AIInvalidOutput("Model reply was not valid JSON") from inner
    if not isinstance(parsed, dict):
        raise AIInvalidOutput("Model reply was not a JSON object")
    return parsed


class GeminiClient:
    """Generates schema-validated structured output."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._types = None

    @property
    def model_name(self) -> str:
        return self._settings.gemini_model

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._settings.ai_configured:
            raise AIUnavailable("Gemini is not configured for this environment")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise AIUnavailable("google-genai is not installed") from exc

        try:
            if self._settings.gemini_use_vertex:
                self._client = genai.Client(
                    vertexai=True,
                    project=self._settings.gemini_vertex_project,
                    location=self._settings.gemini_vertex_location,
                )
            else:
                self._client = genai.Client(api_key=self._settings.gemini_api_key)
        except Exception as exc:
            raise AIUnavailable(f"Could not initialise the Gemini client: {type(exc).__name__}") from exc
        self._types = types
        return self._client

    def _thinking_config(self):
        """Cap thinking so it cannot consume the structured-output budget."""
        level = self._settings.gemini_thinking_level
        if level == "unspecified":
            return None
        return self._types.ThinkingConfig(thinking_level=level.upper())

    @staticmethod
    def _was_truncated(response) -> bool:
        for candidate in getattr(response, "candidates", None) or []:
            reason = getattr(candidate, "finish_reason", None)
            if reason is not None and str(getattr(reason, "name", reason)).upper() == (
                "MAX_TOKENS"
            ):
                return True
        return False

    def generate_structured(
        self,
        *,
        schema: type[SchemaT],
        system_instruction: str,
        user_content: str,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> SchemaT:
        """Call Gemini and return a validated ``schema`` instance.

        Raises :class:`AIUnavailable` for transport problems and
        :class:`AIInvalidOutput` when the reply cannot be validated.
        """
        client = self._ensure_client()
        types = self._types

        def build_config(token_budget: int):
            return types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
                max_output_tokens=token_budget,
                thinking_config=self._thinking_config(),
                http_options=types.HttpOptions(
                    timeout=int(self._settings.gemini_timeout_seconds * 1000)
                ),
            )

        attempts = max(1, self._settings.gemini_max_retries + 1)
        budget = max_output_tokens
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=user_content,
                    config=build_config(budget),
                )
            except Exception as exc:
                last_error = exc
                # Log the type only: messages can carry request content.
                logger.warning(
                    "Gemini call failed (attempt %s/%s): %s",
                    attempt + 1,
                    attempts,
                    type(exc).__name__,
                )
                if attempt + 1 < attempts and _is_transient(exc):
                    time.sleep(min(4.0, (2**attempt) * 0.5 + random.uniform(0, 0.25)))
                    continue
                raise AIUnavailable(
                    f"Gemini request failed: {type(exc).__name__}"
                ) from exc

            if self._was_truncated(response):
                last_error = AIOutputTruncated(
                    "Gemini stopped at the output-token limit before completing the JSON"
                )
                logger.warning(
                    "Gemini reply truncated at %s output tokens (attempt %s/%s)",
                    budget,
                    attempt + 1,
                    attempts,
                )
                if attempt + 1 < attempts:
                    # Thinking and content share this budget, so widen it.
                    budget = min(budget * 2, 8192)
                    continue
                raise last_error

            # Prefer the SDK's own parsed object, fall back to raw JSON.
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            try:
                payload = parsed if isinstance(parsed, dict) else _extract_json(
                    getattr(response, "text", "") or ""
                )
                return schema.model_validate(payload)
            except (AIInvalidOutput, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Gemini returned output that failed validation (attempt %s/%s): %s",
                    attempt + 1,
                    attempts,
                    type(exc).__name__,
                )
                if attempt + 1 < attempts:
                    continue
                raise AIInvalidOutput(
                    "Gemini output did not match the required schema"
                ) from exc

        raise AIUnavailable(f"Gemini request failed: {type(last_error).__name__}")
