"""Browser session tokens and cookie helpers.

Sessions are opaque tokens (``tops_sess_<hex>``) delivered to the browser in an
httpOnly cookie. Only the SHA-256 hash is persisted, mirroring API keys, so a
database leak never exposes a live session.
"""

from __future__ import annotations

import hashlib
import os
import secrets

from itsdangerous import BadSignature, TimestampSigner

SESSION_COOKIE = "trustops_session"
SESSION_TOKEN_PREFIX = "tops_sess_"
DEFAULT_SESSION_TTL_HOURS = 12

_COOKIE_SIGNING_KEY = os.environ.get("TRUSTOPS_COOKIE_SIGNING_KEY", "").strip()
_SIGNER: TimestampSigner | None = TimestampSigner(_COOKIE_SIGNING_KEY) if _COOKIE_SIGNING_KEY else None


def generate_session_token() -> tuple[str, str]:
    """Return ``(token, token_hash)`` for a new browser session."""
    token = f"{SESSION_TOKEN_PREFIX}{secrets.token_hex(32)}"
    return token, hash_session_token(token)


def hash_session_token(token: str) -> str:
    """SHA-256 hex digest of a session token (the only form persisted)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def encode_session_cookie(token: str) -> str:
    """Sign a session token for cookie transport when a signing key is configured."""
    if _SIGNER is None:
        return token
    return _SIGNER.sign(token).decode("utf-8")


def decode_session_cookie(cookie_value: str) -> str | None:
    """Decode a session cookie value back to the raw session token."""
    raw = cookie_value.strip()
    if not raw:
        return None
    if _SIGNER is None:
        return raw
    try:
        return _SIGNER.unsign(raw, max_age=DEFAULT_SESSION_TTL_HOURS * 3600).decode("utf-8")
    except BadSignature:
        return None
