"""Authentication.

Two modes:

* ``firebase`` — verifies a Firebase ID token and maps its email to a user.
  This is the only mode permitted in production.
* ``dev`` — a clearly labelled persona switcher for local demos. It is forced
  off whenever ``ENVIRONMENT=production`` (see :class:`app.core.config.Settings`).

Authentication only establishes *who* the caller is. What they may see is
decided separately in :mod:`app.services.authz`.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.repositories.database import Database
from app.schemas.domain import User

logger = get_logger(__name__)

DEV_USER_HEADER = "x-dev-user-id"


class AuthenticationError(Exception):
    def __init__(self, detail: str = "Not authenticated.") -> None:
        super().__init__(detail)
        self.detail = detail


class FirebaseVerifier:
    """Lazily initialised Firebase Admin token verifier."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._initialised = False

    def _ensure(self) -> None:
        if self._initialised:
            return
        try:
            import firebase_admin
            from firebase_admin import credentials  # noqa: F401
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise AuthenticationError("Firebase Admin SDK is not installed.") from exc
        if not firebase_admin._apps:
            # Application Default Credentials on Cloud Run; no key file needed.
            options = (
                {"projectId": self._settings.firebase_project_id}
                if self._settings.firebase_project_id
                else None
            )
            firebase_admin.initialize_app(options=options)
        self._initialised = True

    def verify(self, id_token: str) -> dict:
        self._ensure()
        from firebase_admin import auth as firebase_auth

        try:
            return firebase_auth.verify_id_token(id_token)
        except Exception as exc:
            # Never log the token itself.
            logger.warning("Firebase token verification failed: %s", type(exc).__name__)
            raise AuthenticationError("Invalid or expired credentials.") from exc


def resolve_user(
    *,
    settings: Settings,
    database: Database,
    headers: dict[str, str],
    verifier: FirebaseVerifier | None = None,
) -> User:
    """Identify the caller from request headers."""
    normalised = {key.lower(): value for key, value in headers.items()}

    if settings.auth_mode == "dev":
        if not settings.dev_auth_enabled:
            raise AuthenticationError("Development authentication is disabled.")
        user_id = normalised.get(DEV_USER_HEADER)
        if not user_id:
            raise AuthenticationError(
                f"Development mode requires the {DEV_USER_HEADER} header."
            )
        user = database.users.get(user_id)
        if user is None:
            raise AuthenticationError("Unknown development persona.")
        return user

    token = _bearer_token(normalised)
    if verifier is None:
        raise AuthenticationError("Token verification is not available.")
    claims = verifier.verify(token)
    email = (claims.get("email") or "").lower()
    if not email:
        raise AuthenticationError("The credential does not carry an email address.")
    user = database.users.find_one(lambda item: item.email.lower() == email)
    if user is None:
        raise AuthenticationError("No TeamPulse account exists for this identity.")
    return user


def _bearer_token(headers: dict[str, str]) -> str:
    raw = headers.get("authorization", "")
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError("A bearer token is required.")
    return token.strip()
