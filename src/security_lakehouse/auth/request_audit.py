"""Append-only request audit events for server-mode auth boundaries."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.auth.rbac import Identity

REQUEST_AUDIT_FILE = "request_audit.jsonl"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def append_request_audit(
    lake_dir: str | Path,
    *,
    method: str,
    route: str,
    status_code: int,
    decision: str,
    correlation_id: str,
    identity: Identity | None = None,
) -> dict[str, Any]:
    """Persist a single request authorization decision.

    Each row gets a unique ``event_id``. ``correlation_id`` ties one HTTP
    request/response pair for tracing; it is **not** an idempotency key — client
    retries may append multiple rows with the same correlation id.
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "category": "request",
        "actor": identity.email if identity else "anonymous",
        "actor_user_id": identity.user_id if identity else None,
        "tenant_id": identity.tenant_id if identity else None,
        "workspace_id": identity.workspace_id if identity else None,
        "role": identity.role if identity else None,
        "route": route,
        "method": method,
        "decision": decision,
        "status_code": status_code,
        "correlation_id": correlation_id,
        "occurred_at": _now(),
    }
    path = Path(lake_dir) / "gold" / REQUEST_AUDIT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    return event
