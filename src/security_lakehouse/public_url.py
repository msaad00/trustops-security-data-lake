"""Validate operator-supplied public base URLs for invite and demo links."""

from __future__ import annotations

from urllib.parse import urlparse

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def normalize_public_url(value: str | None) -> str | None:
    """Return a normalized ``https://host`` base URL, or ``None`` when invalid.

    Rejects schemes other than ``http``/``https``, missing hosts, embedded
    credentials, and non-HTTPS URLs outside local development hosts.
    """
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.fragment:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if parsed.scheme == "http" and host not in _LOCAL_HOSTS:
        return None
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{host}{port}{path}"
