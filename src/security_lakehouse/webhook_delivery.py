"""Outbound event webhook signing + delivery (transport-agnostic, no DB).

TrustOps's API is otherwise pull-only. A registered subscription (see
``db.webhooks``) lets a tenant receive a push the moment something happens —
a new finding, a completed assessment, a control transitioning to failing —
instead of polling. This module is the sending half: build the signed
envelope and POST it, with the same SSRF guard every other outbound egress
path in this codebase uses (:mod:`security_lakehouse.netguard`).

Signing follows the GitHub/Stripe convention: the raw JSON body is HMAC-SHA256
signed with the subscriber's registered secret, and the hex digest travels in
an ``X-TrustOps-Signature: sha256=<hex>`` header so a receiver can verify the
delivery actually came from this TrustOps instance and was not tampered with
in transit. See ``docs/WEBHOOKS.md`` for the receiver-side verification code.

Delivery never raises: every failure (non-2xx, timeout, DNS, SSRF-blocked
target) is caught and returned as ``{"ok": False, ...}`` so a slow or dead
receiver can never fail the caller's write path. Retries once by default with
a short backoff, matching "at least one retry" — this is intentionally a
synchronous call, not a queue: the codebase has no background job worker
today, and adding one is out of scope for this slice (see docs/WEBHOOKS.md).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from security_lakehouse import netguard

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MAX_RETRIES = 1
DEFAULT_BACKOFF_SECONDS = 0.5

SIGNATURE_HEADER = "X-TrustOps-Signature"
EVENT_HEADER = "X-TrustOps-Event"
DELIVERY_HEADER = "X-TrustOps-Delivery"


def _backoff_sleep(seconds: float) -> None:
    """Indirection point so tests can monkeypatch the retry sleep to a no-op."""
    if seconds > 0:
        time.sleep(seconds)


def sign_payload(secret: str, body: bytes) -> str:
    """Return the ``sha256=<hex>`` signature a receiver can independently recompute."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    """Constant-time check that ``signature`` matches ``body`` signed with ``secret``."""
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, signature)


def build_envelope(*, event_type: str, tenant_id: str, occurred_at: str, data: dict[str, Any]) -> dict[str, Any]:
    """The event envelope every delivery carries; ``event_id`` is the delivery's idempotency key."""
    return {
        "event": event_type,
        "event_id": str(uuid.uuid4()),
        "occurred_at": occurred_at,
        "tenant_id": tenant_id,
        "data": data,
    }


def deliver_webhook(
    url: str,
    *,
    secret: str,
    event_type: str,
    envelope: dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> dict[str, Any]:
    """POST ``envelope`` to ``url``, HMAC-signed with ``secret``. Never raises.

    Returns ``{"ok", "status_code", "attempts", "error"}``. A non-2xx response
    or a network/timeout error is retried up to ``max_retries`` additional
    times with a short backoff; an SSRF-blocked or malformed URL fails
    immediately without an attempt (there is nothing safe to retry).
    """
    body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: sign_payload(secret, body),
        EVENT_HEADER: event_type,
        DELIVERY_HEADER: envelope.get("event_id", ""),
    }

    try:
        netguard.assert_url_is_public(url, label="webhook")
    except ValueError as exc:
        return {"ok": False, "status_code": None, "attempts": 0, "error": str(exc)}

    attempts = 0
    last_error: str | None = None
    status_code: int | None = None
    max_retries = max(0, int(max_retries))
    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")  # noqa: S310 (scheme + SSRF guarded above)
        try:
            with netguard.open_guarded(
                request,
                timeout=timeout,
                validate=lambda target: netguard.assert_url_is_public(target, label="webhook"),
            ) as response:
                status_code = int(getattr(response, "status", 0) or 0)
                if 200 <= status_code < 300:
                    return {"ok": True, "status_code": status_code, "attempts": attempts, "error": None}
                last_error = f"HTTP {status_code}"
        except urllib.error.HTTPError as exc:
            status_code = int(exc.code)
            last_error = f"HTTP {status_code}"
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
            status_code = None
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < max_retries:
            _backoff_sleep(backoff_seconds * (2**attempt))

    return {"ok": False, "status_code": status_code, "attempts": attempts, "error": last_error}


__all__ = [
    "DELIVERY_HEADER",
    "EVENT_HEADER",
    "SIGNATURE_HEADER",
    "build_envelope",
    "deliver_webhook",
    "sign_payload",
    "verify_signature",
]
