"""Environment-driven application configuration.

Every secret and environment-specific value is read from the environment.
Nothing sensitive is ever hardcoded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "staging", "production"]
DataBackend = Literal["memory", "firestore"]
AuthMode = Literal["dev", "firebase"]
ThinkingLevel = Literal["minimal", "low", "medium", "high", "unspecified"]


class Settings(BaseSettings):
    """Application settings.

    Resolution order: process environment, then a local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_name: str = "TeamPulse AI"
    environment: Environment = "local"
    log_level: str = "INFO"

    # --- Data access ---
    data_backend: DataBackend = "memory"
    firestore_project_id: str | None = None
    firestore_database: str = "(default)"
    firestore_collection_prefix: str = ""

    # --- Authentication ---
    auth_mode: AuthMode = "dev"
    firebase_project_id: str | None = None
    # The Firebase *web* config, handed to the SPA by GET /api/auth-config so
    # that sign-in needs no rebuild per environment. These are public client
    # identifiers, not secrets: the API key identifies the project, it does not
    # authorise anything. Authorisation is the ID token, verified server-side.
    firebase_web_api_key: str | None = None
    firebase_auth_domain: str | None = None
    # Allows the dev persona switcher. MUST be false in production.
    dev_auth_enabled: bool = True
    # Allows POST /api/admin/seed. MUST be false in production.
    seed_endpoint_enabled: bool = True

    # --- Gemini ---
    # The model id is intentionally configurable. Verify the current supported
    # list at https://ai.google.dev/gemini-api/docs/models before changing it —
    # Google deprecates ids (gemini-3.5-flash is deprecated and routed to 3.6).
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    gemini_use_vertex: bool = False
    gemini_vertex_project: str | None = None
    gemini_vertex_location: str = "us-central1"
    gemini_timeout_seconds: float = 30.0
    gemini_max_retries: int = 2
    gemini_enabled: bool = True
    # Gemini 3.x models think before answering, and thought tokens are drawn
    # from the same budget as max_output_tokens. Left uncapped, thinking
    # starves the structured reply and every call returns truncated JSON.
    # These capabilities summarise facts the rules engine already derived, so
    # they do not need deep reasoning. "unspecified" lets the model decide.
    gemini_thinking_level: ThinkingLevel = "low"
    # Generated summaries are cached this long before being considered stale.
    ai_cache_ttl_seconds: int = 900

    # --- HTTP ---
    # NoDecode: the dotenv source would otherwise try to JSON-decode a
    # list-typed field and fail before ``_split_origins`` ever runs, so a
    # plain comma-separated CORS_ALLOW_ORIGINS could not be loaded from .env.
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    serve_frontend: bool = False
    frontend_dist_dir: str = "static"

    # --- Demo data ---
    # Surfaced to the UI so synthetic records are always labelled as such.
    demo_data_mode: bool = True

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> Settings:
        """Hard-disable development affordances outside local/staging.

        This is deliberately not overridable by configuration: a misconfigured
        production deployment must not expose persona impersonation or a
        destructive seed-reset endpoint.
        """
        if self.environment == "production":
            object.__setattr__(self, "dev_auth_enabled", False)
            object.__setattr__(self, "seed_endpoint_enabled", False)
            object.__setattr__(self, "auth_mode", "firebase")
        return self

    @property
    def resolved_auth_domain(self) -> str | None:
        """Explicit auth domain, else Firebase's default for the project."""
        if self.firebase_auth_domain:
            return self.firebase_auth_domain
        if self.firebase_project_id:
            return f"{self.firebase_project_id}.firebaseapp.com"
        return None

    @property
    def sign_in_configured(self) -> bool:
        """True when the SPA has everything it needs to start a sign-in."""
        if self.auth_mode != "firebase":
            return False
        return bool(self.firebase_web_api_key and self.resolved_auth_domain)

    @property
    def ai_configured(self) -> bool:
        """True when enough configuration exists to attempt a Gemini call."""
        if not self.gemini_enabled:
            return False
        if self.gemini_use_vertex:
            return bool(self.gemini_vertex_project)
        return bool(self.gemini_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Used by tests that need to re-read the environment."""
    get_settings.cache_clear()
