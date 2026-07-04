"""Browser session tokens and cookie helpers.

Sessions are opaque tokens (``tops_sess_<hex>``) delivered to the browser in an
httpOnly cookie. Only the SHA-256 hash is persisted, mirroring API keys, so a
database leak never exposes a live session. Cookie values are always signed with
``TRUSTOPS_COOKIE_SIGNING_KEY`` when authentication is enabled.
"""

from __future__ import annotations

import hashlib
import os
import secrets

from itsdangerous import BadData, URLSafeTimedSerializer

SESSION_COOKIE = "trustops_session"
SESSION_TOKEN_PREFIX = "tops_sess_"
DEFAULT_SESSION_TTL_HOURS = 12
_COOKIE_SIGNING_SALT = "trustops-session-cookie"


def generate_session_token() -> tuple[str, str]:
    """Return ``(token, token_hash)`` for a new browser session."""
    token = f"{SESSION_TOKEN_PREFIX}{secrets.token_hex(32)}"
    return token, hash_session_token(token)


def hash_session_token(token: str) -> str:
    """SHA-256 hex digest of a session token (the only form persisted)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def cookie_signing_key() -> str:
    """Return the configured cookie signing secret (empty when unset)."""
    return os.environ.get("TRUSTOPS_COOKIE_SIGNING_KEY", "").strip()


def ensure_cookie_signing_configured() -> None:
    """Fail fast when auth is enabled but the signing key is missing."""
    if not cookie_signing_key():
        raise RuntimeError(
            "TRUSTOPS_COOKIE_SIGNING_KEY is required when authentication is enabled "
            "(generate with: openssl rand -hex 32)"
        )


def _serializer() -> URLSafeTimedSerializer:
    key = cookie_signing_key()
    if not key:
        raise RuntimeError("TRUSTOPS_COOKIE_SIGNING_KEY is required for signed session cookies")
    return URLSafeTimedSerializer(key, salt=_COOKIE_SIGNING_SALT)


def encode_session_cookie(token: str) -> str:
    """Return a signed cookie value for ``token``."""
    return _serializer().dumps(token)


def decode_session_cookie(cookie_value: str) -> str | None:
    """Decode a signed session cookie value back to the raw session token."""
    raw = cookie_value.strip()
    if not raw:
        return None
    if not cookie_signing_key():
        return None
    try:
        data = _serializer().loads(raw, max_age=DEFAULT_SESSION_TTL_HOURS * 3600)
    except BadData:
        return None
    return data if isinstance(data, str) and data.startswith(SESSION_TOKEN_PREFIX) else None
