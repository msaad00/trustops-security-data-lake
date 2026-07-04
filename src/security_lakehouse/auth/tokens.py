"""API token generation and hashing.

Tokens look like ``tops_<48 hex chars>``. Only a derived lookup digest is
persisted; the plaintext is returned once at creation and never stored.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_PREFIX = "tops_"
_TOKEN_HASH_SALT = b"trustops-api-token-v2"
_TOKEN_HASH_ITERATIONS = 210_000


def generate_token() -> tuple[str, str, str]:
    """Return ``(token, prefix, key_hash)`` for a freshly minted credential."""
    token = f"{TOKEN_PREFIX}{secrets.token_hex(24)}"
    return token, display_prefix(token), hash_token(token)


def hash_token(token: str) -> str:
    """PBKDF2-HMAC lookup digest of a token (the only form persisted)."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        _TOKEN_HASH_SALT,
        _TOKEN_HASH_ITERATIONS,
    ).hex()


def display_prefix(token: str) -> str:
    """Non-secret handle shown in listings (e.g. ``tops_ab12cd34``)."""
    return token[:12]
