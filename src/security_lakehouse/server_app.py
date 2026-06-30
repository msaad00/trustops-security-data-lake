"""Optional FastAPI server (``trustops[server]`` extra).

Server mode serves the same assessment engine and the same
:mod:`security_lakehouse.api_v1` contract as local mode, plus the platform
surface local mode cannot provide: an application-state database, bearer-token
authentication, and role-based access control.

Authentication is required by default. Start with ``require_auth=False`` (or set
``TRUSTOPS_ALLOW_INSECURE_NO_AUTH=1``) only for local development; every request
then runs as a synthetic admin. Local mode (:mod:`security_lakehouse.server`)
remains zero-dependency and unauthenticated by design.

Import this module only when the ``server`` extra is installed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from security_lakehouse import api_legacy, api_v1, remediation_guidance, tenancy, trust_share
from security_lakehouse.demo_links import build_demo_kit
from security_lakehouse.assessment import build_current_posture, write_assessment_snapshot
from security_lakehouse.auth.dependencies import get_session, require_scope
from security_lakehouse.auth.oidc import OIDCLoginError, build_oauth, complete_oidc_login, load_oidc_config
from security_lakehouse.auth.rate_limit import RateLimitConfig, RateLimiter
from security_lakehouse.auth.rbac import Identity, scopes_for_role
from security_lakehouse.auth.request_audit import append_request_audit
from security_lakehouse.auth.saml import (
    SAMLLoginError,
    build_saml_auth,
    complete_saml_login,
    email_from_saml_assertion,
    load_saml_config,
    saml_request_data,
)
from security_lakehouse.auth.sessions import SESSION_COOKIE
from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.dashboard import render_dashboard
from security_lakehouse.data_policy import redact_payload
from security_lakehouse.db import agent_runs as agent_runs_db
from security_lakehouse.db import metrics as metrics_db
from security_lakehouse.db import migrate, remediation, repository
from security_lakehouse.db import tags as tags_db
from security_lakehouse.db.base import DEFAULT_PAGE_LIMIT, clamp_limit, create_engine_for, session_factory
from security_lakehouse.db.models import REMEDIATION_PRIORITIES, User
from security_lakehouse.ingestion_status import build_ingestion_status
from security_lakehouse.io import resolve_path
from security_lakehouse.services import NotFound, ValidationError
from security_lakehouse.services import access_reviews as access_review_services
from security_lakehouse.services import grc as grc_services
from security_lakehouse.web import web_dist_dir, web_dist_index

_COOKIE_SECURE = os.environ.get("TRUSTOPS_COOKIE_SECURE", "true").lower() in {"1", "true", "yes", "on"}

_ERROR_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited"}

# Health probes are exempt from rate limiting so a limiter trip can never hide
# liveness from an orchestrator.
_RATE_LIMIT_EXEMPT = {"/api/healthz", "/api/v1/healthz"}


def _rate_limit_key(request: Request) -> str:
    """Bucket key for a request: the presented credential, else the client host.

    The bearer token is hashed so raw key material never lands in the limiter's
    in-memory map; unauthenticated callers fall back to their source host.
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return "k:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    client = request.client.host if request.client else "unknown"
    return "h:" + client


_LEGACY_ERROR_REASONS = {
    HTTPStatus.BAD_REQUEST: "invalid request",
    HTTPStatus.FORBIDDEN: "forbidden",
    HTTPStatus.NOT_FOUND: "not found",
}

# Scope dependencies are built once (module-level) and reused as route defaults.
_require_read = require_scope("read")
_require_write = require_scope("write")
_require_admin = require_scope("auth_admin")
_require_evidence_request = require_scope("evidence_request")
_require_control_manage = require_scope("control_manage")


class _StrictModel(BaseModel):
    """Base for request bodies: reject unknown fields.

    Without this, Pydantic's default ``extra="ignore"`` silently drops a
    misnamed key, so an agent that sends the wrong field gets a ``201`` with the
    wrong persisted state and no error. Forbidding extras turns that into a
    ``422`` naming the offending field.
    """

    model_config = ConfigDict(extra="forbid")


class CreateKeyRequest(_StrictModel):
    user_email: str
    name: str = ""
    expires_in_days: int | None = None


class CreateTaskRequest(_StrictModel):
    title: str
    description: str = ""
    control_id: str | None = None
    violation_id: str | None = None
    owner: str = ""
    priority: str = "medium"
    due_at: str | None = None


class UpdateTaskRequest(_StrictModel):
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    status: str | None = None
    priority: str | None = None
    due_at: str | None = None


class CreateEvidenceRequestRequest(_StrictModel):
    control_id: str
    requested_from: str = ""
    note: str = ""
    due_at: str | None = None


class EvidenceRequestStatusRequest(_StrictModel):
    status: str


class CreateExceptionRequest(_StrictModel):
    control_id: str
    reason: str = ""
    approved_by: str = ""
    expires_at: str | None = None


class CreateRiskRequest(_StrictModel):
    title: str
    description: str = ""
    category: str = ""
    severity: str = "medium"
    likelihood: str = "medium"
    impact: str = "medium"
    status: str = "open"
    treatment: str = ""
    owner: str = ""
    control_id: str | None = None
    asset_id: str | None = None
    due_at: str | None = None


class UpdateRiskRequest(_StrictModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    likelihood: str | None = None
    impact: str | None = None
    status: str | None = None
    treatment: str | None = None
    owner: str | None = None
    control_id: str | None = None
    asset_id: str | None = None
    due_at: str | None = None


class CreateCampaignRequest(_StrictModel):
    name: str
    description: str = ""
    scope: str = "all"
    control_id: str | None = None
    due_at: str | None = None


class CampaignStatusRequest(_StrictModel):
    status: str


class AddReviewItemRequest(_StrictModel):
    subject_id: str
    subject_name: str = ""
    source: str = ""
    access_summary: str = ""


class ReviewDecisionRequest(_StrictModel):
    decision: str
    note: str = ""


class CreateTagRequest(_StrictModel):
    name: str
    color: str = ""


class AttachTagRequest(_StrictModel):
    tag_id: str
    entity_type: str
    entity_id: str


class CreateSavedViewRequest(_StrictModel):
    surface: str
    name: str
    filters: dict = {}


class CreateAgentRunRequest(_StrictModel):
    harness: str
    objective: str = ""
    role: str | None = None
    idempotency_key: str | None = None
    orchestrator: str = "sequential"
    use_model: bool = False
    max_context_chars: int | None = None
    max_fact_items: int | None = None
    max_output_tokens: int | None = None


class ApproveAgentDecisionRequest(_StrictModel):
    note: str = ""


def _parse_dt(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid datetime: {value!r}") from exc


def _params(request: Request) -> dict[str, list[str]]:
    """Convert Starlette's query multidict into the ``api_v1`` param shape."""
    params: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        params.setdefault(key, []).append(value)
    return params


def _pagination(params: dict[str, list[str]]) -> tuple[int, int]:
    """Read ``limit``/``offset`` query params, clamped to a safe page window.

    A missing/invalid ``limit`` defaults to ``DEFAULT_PAGE_LIMIT`` so list
    endpoints are always bounded; an oversized one is capped server-side.
    """
    limit_raw = (params.get("limit") or [None])[0]
    offset_raw = (params.get("offset") or [None])[0]
    limit = clamp_limit(int(limit_raw)) if limit_raw and limit_raw.lstrip("-").isdigit() else DEFAULT_PAGE_LIMIT
    offset = int(offset_raw) if offset_raw and offset_raw.isdigit() else 0
    return limit, max(0, offset)


def _page_meta(limit: int, offset: int, count: int) -> dict[str, int]:
    """Envelope ``meta`` fields describing the returned page."""
    return {"count": count, "limit": limit, "offset": offset}


def _insecure_requested() -> bool:
    return os.environ.get("TRUSTOPS_ALLOW_INSECURE_NO_AUTH", "").lower() in {"1", "true", "yes"}


def _redact_payload(payload: object, identity: Identity) -> object:
    return redact_payload(payload, role=identity.role)


def _role_allowed_for_actor(requested_role: str, identity: Identity) -> bool:
    """Allow same or narrower read visibility, never role escalation."""
    visibility_rank = {"auditor": 0, "read_only": 1, "contributor": 1, "security_admin": 2, "admin": 2}
    return visibility_rank.get(requested_role, 99) <= visibility_rank.get(identity.role, -1)


def _safe_agent_lake_path(root_lake: Path, tenant_lake: Path) -> Path:
    """Resolve the tenant/account lake and ensure it stays under the server root."""
    root = root_lake.resolve()
    target = tenant_lake.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant lake is outside server root") from exc
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant lake is not a directory")
    return target


def _decision_payload(decision: dict[str, Any]) -> dict[str, Any]:
    payload = decision.get("payload")
    return payload if isinstance(payload, dict) else {}


def _payload_text(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key)
    return str(value).strip() if value is not None else default


def _decision_reason(decision: dict[str, Any], *, note: str = "") -> str:
    reason = str(decision.get("reason") or "").strip()
    extra = note.strip()
    if reason and extra:
        return f"{reason}\n\nApproval note: {extra}"
    return reason or extra or "Approved agent harness proposal."


def _decision_priority(payload: dict[str, Any], default: str = "medium") -> str:
    value = str(payload.get("priority") or payload.get("severity") or default).lower()
    return value if value in REMEDIATION_PRIORITIES else default


def _execute_agent_decision(
    session: Session,
    *,
    lake: Path,
    identity: Identity,
    decision: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    """Execute an allowlisted agent decision through TrustOps-native writes only."""
    action = str(decision.get("action") or "")
    payload = _decision_payload(decision)
    reason = _decision_reason(decision, note=note)

    if action == "create_evidence_request":
        control_id = _payload_text(payload, "control_id")
        requested_from = _payload_text(payload, "requested_from") or _payload_text(payload, "owner")
        try:
            req = remediation.create_evidence_request(
                session,
                tenant_id=identity.tenant_id,
                control_id=control_id,
                requested_from=requested_from,
                note=reason,
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "type": "evidence_request",
            "id": req.id,
            "control_id": req.control_id,
            "status": req.status,
        }

    if action == "create_remediation_task":
        control_id: str | None = _payload_text(payload, "control_id") or None
        title = _payload_text(payload, "title") or f"Remediate {control_id or 'agent finding'}"
        try:
            task = remediation.create_task(
                session,
                tenant_id=identity.tenant_id,
                title=title,
                description=reason,
                control_id=control_id,
                violation_id=_payload_text(payload, "violation_id") or None,
                owner=_payload_text(payload, "owner"),
                priority=_decision_priority(payload),
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {"type": "remediation_task", "id": task.id, "control_id": task.control_id, "status": task.status}

    if action == "create_soc_case":
        event_id = _payload_text(payload, "event_id") or _payload_text(payload, "alert_id") or "unknown-event"
        severity = _decision_priority(payload, default="high")
        try:
            task = remediation.create_task(
                session,
                tenant_id=identity.tenant_id,
                title=f"SOC case: {event_id}",
                description=reason,
                violation_id=event_id,
                owner=_payload_text(payload, "owner"),
                priority=severity,
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {"type": "remediation_task", "id": task.id, "violation_id": task.violation_id, "status": task.status}

    if action == "assign_owner":
        event_id = _payload_text(payload, "event_id") or _payload_text(payload, "control_id") or "agent finding"
        owner = _payload_text(payload, "owner")
        try:
            task = remediation.create_task(
                session,
                tenant_id=identity.tenant_id,
                title=f"Assign owner: {event_id}",
                description=reason,
                control_id=_payload_text(payload, "control_id") or None,
                violation_id=_payload_text(payload, "violation_id") or _payload_text(payload, "event_id") or None,
                owner=owner,
                priority=_decision_priority(payload),
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {"type": "remediation_task", "id": task.id, "owner": task.owner, "status": task.status}

    if action == "freeze_snapshot":
        if not identity.has_scope("snapshot"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="snapshot scope required")
        snapshot_path = write_assessment_snapshot(lake, reason=reason)
        return {"type": "snapshot", "snapshot_path": str(snapshot_path)}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"agent decision action is not executable: {action or 'missing'}",
    )


def _public_trust_summary(lake: Path, share: dict[str, object]) -> dict[str, object]:
    """Build the redacted, read-only posture an external token holder may see.

    Starts from the full posture, applies the *same* auditor-lens redaction the
    ``auditor`` role gets (owners/notes/actor/credentials → ``[redacted]``), then
    trims to a public summary: posture score/state and per-framework readiness
    with control counts only. Raw violations, asset/evidence internals, and any
    owner fields never reach the wire — only this summary leaves the lake.
    """
    posture = build_current_posture(lake)
    auditor = Identity(
        user_id="public-trust-share",
        tenant_id="public",
        email="anonymous",
        role="auditor",
        scopes=scopes_for_role("auditor"),
    )
    redacted = _redact_payload(posture, auditor)
    if not isinstance(redacted, dict):
        redacted = {}
    posture_block = redacted.get("posture")
    posture_block = posture_block if isinstance(posture_block, dict) else {}
    frameworks_raw = redacted.get("frameworks")
    frameworks: list[dict[str, object]] = []
    if isinstance(frameworks_raw, list):
        for row in frameworks_raw:
            if not isinstance(row, dict):
                continue
            frameworks.append(
                {
                    "framework": row.get("framework"),
                    "score": row.get("score"),
                    "state": row.get("state"),
                    "control_count": row.get("control_count"),
                    "failing_control_count": row.get("failing_control_count"),
                    "stale_control_count": row.get("stale_control_count"),
                }
            )
    return {
        "schema_version": "trustops.public_trust.v1",
        "sensitivity": "public",
        "visibility": "external_reviewer",
        "redaction_policy": "trustops.public_summary.v1",
        "data_residency": "evidence never leaves this lake; only this summary is shared",
        "issued_by": share.get("created_by"),
        "scope": share.get("scope"),
        "role": share.get("role"),
        "sensitivity_ceiling": share.get("sensitivity_ceiling", "public"),
        "expires_at": share.get("expires_at"),
        "evaluated_at": redacted.get("evaluated_at"),
        "posture": {
            "score": posture_block.get("score"),
            "state": posture_block.get("state"),
            "framework_count": posture_block.get("framework_count"),
            "control_count": posture_block.get("control_count"),
            "open_violation_count": posture_block.get("open_violation_count"),
            "critical_violation_count": posture_block.get("critical_violation_count"),
            "high_violation_count": posture_block.get("high_violation_count"),
            "stale_control_count": posture_block.get("stale_control_count"),
        },
        "frameworks": frameworks,
    }


def _poc_step(
    *,
    step_id: str,
    label: str,
    ready: bool,
    detail: str,
    href: str | None = None,
    blocking: bool = True,
) -> dict[str, object]:
    return {
        "id": step_id,
        "label": label,
        "status": "ready" if ready else "needs_setup",
        "detail": detail,
        "href": href,
        "blocking": blocking,
    }


def _build_poc_readiness(
    *,
    app: FastAPI,
    lake: Path,
    identity: Identity,
    session: Session,
) -> dict[str, object]:
    """Return the tenant's readiness to host a shareable POC."""
    now = datetime.now(UTC)
    public_url = (
        os.environ.get("TRUSTOPS_PUBLIC_URL")
        or os.environ.get("TRUSTOPS_BASE_URL")
        or os.environ.get("TRUSTOPS_APP_URL")
        or ""
    ).rstrip("/")
    sso_configured = app.state.oauth is not None or app.state.saml_config is not None
    keys = repository.list_api_keys(session, tenant_id=identity.tenant_id)
    active_keys = [key for key in keys if key.is_active(now=now)]
    role_counts = {
        str(role): int(count)
        for role, count in session.execute(
            select(User.role, func.count())
            .where(User.tenant_id == identity.tenant_id, User.is_active.is_(True))
            .group_by(User.role)
        ).all()
    }
    ingestion = build_ingestion_status(lake)
    ingestion_summary = ingestion.get("summary") or {}
    active_shares = [share for share in trust_share.list_shares(lake) if not share.get("expired")]
    enabled_connectors = int(ingestion_summary.get("enabled_connectors") or 0)
    evidence_count = int(ingestion_summary.get("evidence_count") or 0)
    failed_connectors = int(ingestion_summary.get("failed_connectors") or 0)
    silent_connectors = int(ingestion_summary.get("silent_connectors") or 0)
    source_ready = enabled_connectors > 0 and evidence_count > 0 and failed_connectors == 0 and silent_connectors == 0
    human_access_ready = (not bool(app.state.require_auth)) or sso_configured
    headless_access_ready = len(active_keys) > 0
    agent_run_rows = agent_runs_db.list_agent_runs(session, tenant_id=identity.tenant_id, limit=100)
    completed_agent_runs = [row for row in agent_run_rows if row.status == "completed"]
    pending_agent_decisions = sum(
        1
        for row in agent_run_rows
        for decision in agent_runs_db.agent_run_decisions(row)
        if decision.get("status") == "proposed"
    )
    latest_agent_run_at = agent_run_rows[0].created_at.isoformat() if agent_run_rows else None

    steps = [
        _poc_step(
            step_id="public_url",
            label="Public URL",
            ready=bool(public_url),
            detail=public_url or "Set TRUSTOPS_PUBLIC_URL for invite links.",
        ),
        _poc_step(
            step_id="human_access",
            label="Human access",
            ready=human_access_ready,
            detail="SSO configured" if sso_configured else "Configure OIDC or SAML for browser login.",
            href="/console/login",
        ),
        _poc_step(
            step_id="headless_access",
            label="Agent/API access",
            ready=headless_access_ready,
            detail=f"{len(active_keys)} active API key(s)" if active_keys else "Issue an API key for headless clients.",
            href="/api/v1/auth/keys",
            blocking=False,
        ),
        _poc_step(
            step_id="source_sync",
            label="Source sync",
            ready=source_ready,
            detail=(
                f"{evidence_count} evidence row(s) from {enabled_connectors} enabled source(s)"
                if source_ready
                else "Connect, test, enable, and sync at least one source."
            ),
            href="/console/connectors",
        ),
        _poc_step(
            step_id="trust_share",
            label="Trust share",
            ready=bool(active_shares),
            detail=f"{len(active_shares)} active share link(s)"
            if active_shares
            else "Create a scoped trust-center share.",
            href="/console/trust-center",
        ),
        _poc_step(
            step_id="agent_review",
            label="Agent review",
            ready=bool(completed_agent_runs),
            detail=(
                f"{len(completed_agent_runs)} completed run(s), {pending_agent_decisions} pending decision(s)"
                if completed_agent_runs
                else "Run a governed review to propose approval-gated next actions."
            ),
            href="/console/agents",
            blocking=False,
        ),
    ]
    blocking_ready = all(step["status"] == "ready" for step in steps if step["blocking"])
    any_access_ready = human_access_ready or headless_access_ready
    state = "ready" if blocking_ready else ("internal_ready" if source_ready and any_access_ready else "needs_setup")
    next_step = next((step for step in steps if step["status"] != "ready"), None)
    demo_kit = build_demo_kit(
        public_url=public_url or None,
        sso_configured=sso_configured,
        require_auth=bool(app.state.require_auth),
        ingestion=ingestion,
        active_share_count=len(active_shares),
        shareable=state == "ready",
    )
    return {
        "state": state,
        "shareable": state == "ready",
        "public_url": public_url or None,
        "demo_kit": demo_kit,
        "workspace": {
            "tenant_id": identity.tenant_id,
            "workspace_id": identity.workspace_id or identity.tenant_id,
            "current_user": identity.email,
            "current_role": identity.role,
        },
        "access": {
            "require_auth": bool(app.state.require_auth),
            "browser_sso_configured": sso_configured,
            "active_api_keys": len(active_keys),
            "users_by_role": role_counts,
        },
        "connectors": {
            "enabled": enabled_connectors,
            "failed": failed_connectors,
            "silent": silent_connectors,
            "evidence_count": evidence_count,
            "source_count": int(ingestion_summary.get("source_count") or 0),
        },
        "trust_shares": {
            "active": len(active_shares),
        },
        "agents": {
            "runs": len(agent_run_rows),
            "completed": len(completed_agent_runs),
            "pending_decisions": pending_agent_decisions,
            "latest_run_at": latest_agent_run_at,
        },
        "ingestion": {
            "state": ingestion.get("state"),
            "posture_score": ingestion_summary.get("posture_score"),
            "open_violations": ingestion_summary.get("open_violations"),
            "recommended_actions": ingestion.get("recommended_actions") or [],
        },
        "steps": steps,
        "next_step": next_step,
    }


def _legacy_error_payload(status_code: HTTPStatus) -> dict[str, str]:
    """Return generic server-mode legacy API errors.

    The legacy dispatcher is shared with local mode and may call file, workflow,
    connector, or trust-share helpers. Server mode must not echo exception text
    or handler-produced error details to authenticated clients.
    """
    if status_code == HTTPStatus.BAD_REQUEST:
        error = "bad_request"
    elif status_code == HTTPStatus.FORBIDDEN:
        error = "forbidden"
    elif status_code == HTTPStatus.NOT_FOUND:
        error = "not_found"
    else:
        error = "internal_error"
    return {"error": error, "reason": _LEGACY_ERROR_REASONS.get(status_code, "internal server error")}


def _legacy_post_response(path: str, body: dict[str, object], lake: Path, identity: Identity) -> JSONResponse:
    """Dispatch a legacy POST with a fail-closed server-mode error boundary."""
    try:
        status_code, payload = api_legacy.handle_post(path, body, lake, role=identity.role)
    except Exception:  # noqa: BLE001 - do not expose internal exception text at the HTTP boundary
        return JSONResponse(_legacy_error_payload(HTTPStatus.INTERNAL_SERVER_ERROR), status_code=500)
    if status_code >= HTTPStatus.BAD_REQUEST:
        return JSONResponse(_legacy_error_payload(status_code), status_code=int(status_code))
    return JSONResponse(payload, status_code=int(status_code))


async def posture_event_stream(lake: Path, request: Request, *, interval: float = 10.0) -> AsyncIterator[str]:
    """SSE frames for continuous eval: a ``posture`` event on change, else a keep-alive ping.

    Stops when the client disconnects. Module-level (not a closure) so it is unit-testable.
    """
    last = ""
    while not await request.is_disconnected():
        # Posture is rebuilt from lake files; offload so the per-tick read does
        # not block the event loop for other connections.
        _status, body = await run_in_threadpool(api_v1.handle_get, "/api/v1/posture/current", {}, lake)
        payload = json.dumps(body.get("data", {}), default=str)
        if payload != last:
            last = payload
            yield f"event: posture\ndata: {payload}\n\n"
        else:
            yield ": ping\n\n"
        await asyncio.sleep(interval)


def create_app(lake_dir: str | Path, *, require_auth: bool = True) -> FastAPI:
    """Build the server-mode ASGI app bound to a security data lake directory."""
    lake = resolve_path(lake_dir)
    dashboard = lake / "console.html"
    render_dashboard(lake, dashboard)
    web_dist = web_dist_dir() if web_dist_index() else None

    migrate.upgrade(lake)
    engine = create_engine_for(lake)

    app = FastAPI(
        title="TrustOps Security Data Lake",
        version=api_v1.API_VERSION,
        description=(
            "Continuous compliance assessment for security data lakes. The same "
            "engine serves a human console and a headless `/api/v1` surface for "
            "agents. Discover the contract at `GET /api/v1`; browse it at `/docs`."
        ),
        openapi_tags=[
            {"name": "discovery", "description": "Self-describing index + health."},
            {"name": "auth", "description": "API keys, SSO (OIDC/SAML), sessions, RBAC."},
            {"name": "assessment", "description": "Posture, controls, evidence, violations, snapshots."},
            {"name": "agents", "description": "Human/headless agent harness runs and evaluations."},
            {"name": "remediation", "description": "Tasks, evidence requests, control exceptions."},
            {"name": "insights", "description": "Posture time-series and remediation metrics."},
            {"name": "tags", "description": "Cross-entity tags and saved views."},
        ],
    )
    app.state.sessionmaker = session_factory(engine)
    app.state.require_auth = require_auth and not _insecure_requested()
    app.state.rate_limiter = RateLimiter(RateLimitConfig.from_env(dict(os.environ)))

    def lake_for(identity: Identity) -> Path:
        """Resolve the per-request lake for ``identity`` so one tenant can never
        read another tenant's compliance evidence.

        Each tenant reads ``<root>/tenants/<id>``; a flat lake at the root (the
        CLI/fixtures layout) is served only to the single tenant of a
        single-tenant deployment (or the synthetic insecure tenant). Resolved per
        request — not snapshotted at startup — so a tenant provisioned after the
        server boots still binds correctly, and a second tenant fails closed.
        """
        if app.state.require_auth:
            with app.state.sessionmaker() as session:
                tenant_ids = repository.list_tenant_ids(session)
        else:
            tenant_ids = []
        bound = tenancy.resolve_bound_tenant(lake, require_auth=app.state.require_auth, tenant_ids=tenant_ids)
        return tenancy.tenant_lake(lake, identity.tenant_id, bound_tenant=bound)

    # OIDC SSO is optional; the OAuth client + signed session middleware are only
    # wired when an identity provider is configured via the environment.
    app.state.oidc_config = load_oidc_config()
    app.state.oauth = None
    app.state.saml_config = load_saml_config()
    app.state.saml_auth_factory = build_saml_auth
    if app.state.oidc_config is not None:
        from starlette.middleware.sessions import SessionMiddleware

        secret = os.environ.get("TRUSTOPS_SESSION_SECRET") or secrets.token_hex(32)
        app.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax", https_only=_COOKIE_SECURE)
        app.state.oauth = build_oauth(app.state.oidc_config)

    @app.middleware("http")
    async def _record_request_audit(request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        response = await call_next(request)
        path = request.url.path
        # Audit authorization decisions on the secured API surfaces only; health is open.
        if path.startswith("/api/") and path not in {"/api/healthz", "/api/v1/healthz"}:
            # Offload the synchronous append so the audit write never blocks the
            # event loop on every authenticated request.
            await run_in_threadpool(
                append_request_audit,
                lake,
                method=request.method,
                route=path,
                status_code=response.status_code,
                decision="allow" if response.status_code < 400 else "deny",
                correlation_id=correlation_id,
                identity=getattr(request.state, "identity", None),
            )
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Registered last so it wraps outermost: a throttled request is shed here
    # before it reaches the audit threadpool write or a route handler.
    @app.middleware("http")
    async def _rate_limit(request: Request, call_next):
        limiter: RateLimiter = app.state.rate_limiter
        path = request.url.path
        if limiter.enabled and path.startswith("/api/") and path not in _RATE_LIMIT_EXEMPT:
            allowed, retry_after = limiter.check(_rate_limit_key(request))
            if not allowed:
                response = JSONResponse(
                    api_v1.error_envelope("rate_limited", "rate limit exceeded; slow down and retry"),
                    status_code=int(HTTPStatus.TOO_MANY_REQUESTS),
                )
                response.headers["Retry-After"] = str(max(1, math.ceil(retry_after)))
                return response
        return await call_next(request)

    @app.exception_handler(StarletteHTTPException)
    async def _error_envelope(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _ERROR_CODES.get(exc.status_code, "error")
        return JSONResponse(
            api_v1.error_envelope(code, str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_envelope(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Body/query validation (incl. unknown fields) returns the same v1 error
        # envelope as the rest of the surface, naming each offending field, so an
        # agent gets one consistent, machine-parsable error shape.
        parts = [f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg')}" for err in exc.errors()]
        detail = "; ".join(parts) or "invalid request"
        return JSONResponse(
            api_v1.error_envelope("unprocessable_entity", detail),
            status_code=422,
        )

    # --- open health checks (registered before the authenticated catch-all) ---
    @app.get("/api/healthz")
    def healthz() -> dict[str, object]:
        return {"ok": True, "service": "trustops-assessment"}

    @app.get("/api/v1/healthz", tags=["discovery"])
    def v1_healthz() -> JSONResponse:
        _status, body = api_v1.handle_get("/api/v1/healthz", {}, lake)
        return JSONResponse(body, status_code=int(_status))

    # --- public trust center (UNAUTHENTICATED, token-scoped) ---
    # The consumption side of trust shares: an external reviewer holding a
    # scoped/expiring/revocable token reaches a redacted, read-only posture
    # without any internal-grade access. Registered before the authenticated
    # catch-alls so it is never shadowed, and carries NO auth dependency. A
    # miss/expired/revoked token returns a generic 404 (no detail leak). The
    # request-audit middleware records the access as anonymous public.
    @app.get("/api/public/trust/{token}", tags=["discovery"])
    def public_trust(token: str) -> JSONResponse:
        share = trust_share.resolve_share(lake, token)
        if share is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        return JSONResponse(_public_trust_summary(lake, share))

    @app.get("/api/v1", tags=["discovery"])
    def v1_index(_identity: Identity = Depends(_require_read)) -> JSONResponse:
        # Self-describing contract so headless agents can enumerate the surface.
        return JSONResponse(
            api_v1.envelope(
                "index",
                api_v1.index_payload(),
            )
        )

    # --- continuous-eval live stream (SSE) ---
    # Pushes posture updates so the console is live without client polling.
    # EventSource carries only cookies, so this is the session-authenticated
    # (human app) surface; headless agents poll /api/v1/posture/current instead.
    @app.get("/api/v1/stream")
    async def stream(request: Request, identity: Identity = Depends(_require_read)) -> StreamingResponse:
        return StreamingResponse(
            posture_event_stream(lake_for(identity), request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    # --- SSO (OIDC) ---
    @app.get("/api/v1/auth/login")
    async def sso_login(request: Request):
        if app.state.oauth is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC SSO is not configured")
        redirect_uri = os.environ.get("TRUSTOPS_OIDC_REDIRECT_URL") or str(request.url_for("sso_callback"))
        return await app.state.oauth.oidc.authorize_redirect(request, redirect_uri)

    @app.get("/api/v1/auth/callback", name="sso_callback")
    async def sso_callback(request: Request, session: Session = Depends(get_session)):
        if app.state.oauth is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC SSO is not configured")
        try:
            token = await app.state.oauth.oidc.authorize_access_token(request)
        except Exception:  # noqa: BLE001 - authlib surfaces several OAuth error types
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC token exchange failed") from None
        email = (token.get("userinfo") or {}).get("email", "")
        try:
            _user, sess_token = complete_oidc_login(session, config=app.state.oidc_config, email=email)
        except OIDCLoginError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OIDC login rejected") from None
        session.commit()
        response = RedirectResponse(url="/console", status_code=status.HTTP_302_FOUND)
        response.set_cookie(SESSION_COOKIE, sess_token, httponly=True, secure=_COOKIE_SECURE, samesite="lax", path="/")
        return response

    @app.post("/api/v1/auth/logout")
    def sso_logout(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
        cookie = request.cookies.get(SESSION_COOKIE)
        if cookie:
            repository.revoke_user_session(session, cookie, now=datetime.now(UTC))
            session.commit()
        response = JSONResponse(api_v1.envelope("auth.logout", {"ok": True}))
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    # --- SSO (SAML) ---
    @app.get("/api/v1/auth/saml/login")
    def saml_login(request: Request):
        if app.state.saml_config is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SAML SSO is not configured")
        auth = app.state.saml_auth_factory(
            app.state.saml_config,
            saml_request_data(
                scheme=request.url.scheme,
                host=request.url.netloc,
                port=request.url.port,
                path=request.url.path,
                query=dict(request.query_params),
            ),
        )
        return RedirectResponse(url=auth.login(), status_code=status.HTTP_302_FOUND)

    @app.get("/api/v1/auth/saml/metadata")
    def saml_metadata(request: Request):
        if app.state.saml_config is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SAML SSO is not configured")
        auth = app.state.saml_auth_factory(
            app.state.saml_config,
            saml_request_data(
                scheme=request.url.scheme,
                host=request.url.netloc,
                port=request.url.port,
                path=request.url.path,
                query=dict(request.query_params),
            ),
        )
        metadata = auth.get_settings().get_sp_metadata()
        errors = auth.get_settings().validate_metadata(metadata)
        if errors:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid SAML metadata")
        return HTMLResponse(metadata, media_type="application/xml")

    @app.post("/api/v1/auth/saml/acs")
    async def saml_acs(request: Request, session: Session = Depends(get_session)):
        if app.state.saml_config is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SAML SSO is not configured")
        body = await request.body()
        auth = app.state.saml_auth_factory(
            app.state.saml_config,
            saml_request_data(
                scheme=request.url.scheme,
                host=request.url.netloc,
                port=request.url.port,
                path=request.url.path,
                query=dict(request.query_params),
                body=body,
            ),
        )
        auth.process_response()
        errors = auth.get_errors()
        if errors or not auth.is_authenticated():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SAML response rejected")
        try:
            _user, sess_token = complete_saml_login(
                session,
                config=app.state.saml_config,
                email=email_from_saml_assertion(auth),
            )
        except SAMLLoginError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SAML login rejected") from None
        session.commit()
        response = RedirectResponse(url="/console", status_code=status.HTTP_302_FOUND)
        response.set_cookie(SESSION_COOKIE, sess_token, httponly=True, secure=_COOKIE_SECURE, samesite="lax", path="/")
        return response

    # --- auth surface ---
    @app.get("/api/v1/auth/methods")
    def auth_methods() -> JSONResponse:
        return JSONResponse(
            api_v1.envelope(
                "auth.methods",
                {
                    "require_auth": bool(app.state.require_auth),
                    "methods": [
                        {
                            "id": "oidc",
                            "label": "OIDC SSO",
                            "configured": app.state.oauth is not None,
                            "login_url": "/api/v1/auth/login",
                        },
                        {
                            "id": "saml",
                            "label": "SAML SSO",
                            "configured": app.state.saml_config is not None,
                            "login_url": "/api/v1/auth/saml/login",
                        },
                    ],
                },
            )
        )

    @app.get("/api/v1/auth/whoami")
    def whoami(identity: Identity = Depends(_require_read)) -> JSONResponse:
        return JSONResponse(
            api_v1.envelope(
                "auth.whoami",
                {
                    "user_id": identity.user_id,
                    "tenant_id": identity.tenant_id,
                    "email": identity.email,
                    "role": identity.role,
                    "scopes": sorted(identity.scopes),
                },
            )
        )

    @app.get("/api/v1/auth/keys")
    def list_keys(
        identity: Identity = Depends(_require_admin),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        keys = repository.list_api_keys(session, tenant_id=identity.tenant_id)
        rows = [
            {
                "id": key.id,
                "name": key.name,
                "prefix": key.prefix,
                "user_email": key.user.email,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "revoked": key.revoked_at is not None,
            }
            for key in keys
        ]
        return JSONResponse(api_v1.envelope("auth.keys", rows, meta={"count": len(rows)}))

    @app.post("/api/v1/auth/keys", status_code=status.HTTP_201_CREATED)
    def create_key(
        body: CreateKeyRequest,
        identity: Identity = Depends(_require_admin),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        user = repository.get_user_by_email(session, tenant_id=identity.tenant_id, email=body.user_email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"no user {body.user_email!r} in tenant")
        expires_at = None
        if body.expires_in_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)
        key, token = repository.create_api_key(
            session, tenant_id=identity.tenant_id, user_id=user.id, name=body.name, expires_at=expires_at
        )
        session.commit()
        return JSONResponse(
            api_v1.envelope(
                "auth.keys",
                {"id": key.id, "prefix": key.prefix, "user_email": user.email, "token": token},
            ),
            status_code=status.HTTP_201_CREATED,
        )

    @app.delete("/api/v1/auth/keys/{key_id}")
    def revoke_key(
        key_id: str,
        identity: Identity = Depends(_require_admin),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        revoked = repository.revoke_api_key(session, tenant_id=identity.tenant_id, key_id=key_id, now=datetime.now(UTC))
        if not revoked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="key not found or already revoked")
        session.commit()
        return JSONResponse(api_v1.envelope("auth.keys", {"id": key_id, "revoked": True}))

    @app.get("/api/v1/platform/poc-readiness")
    def poc_readiness(
        identity: Identity = Depends(_require_admin),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        data = _build_poc_readiness(app=app, lake=lake_for(identity), identity=identity, session=session)
        return JSONResponse(api_v1.envelope("platform.poc-readiness", data))

    # --- agent harness runs ---
    @app.get("/api/v1/agent-runs", tags=["agents"])
    def list_agent_runs(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit_raw = (params.get("limit") or ["100"])[0]
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 100
        harness_filter = (params.get("harness") or [""])[0] or None
        status_filter = (params.get("status") or [""])[0] or None
        rows = agent_runs_db.list_agent_runs(
            session,
            tenant_id=identity.tenant_id,
            harness=harness_filter,
            status=status_filter,
            limit=limit,
        )
        data = [agent_runs_db.agent_run_to_dict(row) for row in rows]
        return JSONResponse(api_v1.envelope("agent-runs", _redact_payload(data, identity), meta={"count": len(data)}))

    @app.post("/api/v1/agent-runs", status_code=status.HTTP_201_CREATED, tags=["agents"])
    def create_agent_run(
        body: CreateAgentRunRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        from security_lakehouse.agents import AgentBudgetPolicy
        from security_lakehouse.agents.providers import ModelProviderConfig, provider_from_env

        role = body.role or identity.role
        if not _role_allowed_for_actor(role, identity):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="requested agent role exceeds caller")
        provider_base = provider_from_env()
        provider = ModelProviderConfig(
            provider=provider_base.provider,
            model=provider_base.model,
            base_url=provider_base.base_url,
            api_key_env=provider_base.api_key_env,
            use_model=bool(body.use_model and provider_base.enabled),
            timeout_seconds=provider_base.timeout_seconds,
        )
        budget_base = AgentBudgetPolicy.from_env()
        budget = AgentBudgetPolicy(
            max_context_chars=body.max_context_chars
            if body.max_context_chars is not None
            else budget_base.max_context_chars,
            max_fact_items=body.max_fact_items if body.max_fact_items is not None else budget_base.max_fact_items,
            max_output_tokens=body.max_output_tokens
            if body.max_output_tokens is not None
            else budget_base.max_output_tokens,
            max_string_chars=budget_base.max_string_chars,
        )
        try:
            row, created = agent_runs_db.run_and_persist_agent(
                session,
                tenant_id=identity.tenant_id,
                lake_dir=_safe_agent_lake_path(lake, lake_for(identity)),
                harness=body.harness,
                objective=body.objective or f"Run {body.harness} harness.",
                role=role,
                created_by=identity.email,
                idempotency_key=body.idempotency_key,
                provider=provider,
                budget=budget,
                orchestrator=body.orchestrator,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return JSONResponse(
            api_v1.envelope(
                "agent-runs",
                _redact_payload(agent_runs_db.agent_run_to_dict(row, include_state=True), identity),
                meta={"created": created},
            ),
            status_code=response_status,
        )

    @app.get("/api/v1/agent-runs/{run_id}", tags=["agents"])
    def get_agent_run(
        run_id: str, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        row = agent_runs_db.get_agent_run(session, tenant_id=identity.tenant_id, run_id=run_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
        return JSONResponse(
            api_v1.envelope(
                "agent-runs", _redact_payload(agent_runs_db.agent_run_to_dict(row, include_state=True), identity)
            )
        )

    @app.post("/api/v1/agent-runs/{run_id}/decisions/{decision_index}/approve", tags=["agents"])
    def approve_agent_decision(
        run_id: str,
        decision_index: int,
        body: ApproveAgentDecisionRequest | None = None,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        row = agent_runs_db.get_agent_run(session, tenant_id=identity.tenant_id, run_id=run_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
        if row.status != "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent run is not executable")
        decisions = agent_runs_db.agent_run_decisions(row)
        if decision_index < 0 or decision_index >= len(decisions):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent decision not found")
        decision = decisions[decision_index]
        existing_result = decision.get("execution_result")
        if decision.get("status") == "executed" and isinstance(existing_result, dict):
            return JSONResponse(
                api_v1.envelope(
                    "agent-runs.decisions",
                    _redact_payload(agent_runs_db.agent_run_to_dict(row, include_state=True), identity),
                    meta={"executed": False, "decision_index": decision_index, "execution_result": existing_result},
                )
            )

        result = _execute_agent_decision(
            session,
            lake=_safe_agent_lake_path(lake, lake_for(identity)),
            identity=identity,
            decision=decision,
            note=body.note if body is not None else "",
        )
        agent_runs_db.mark_decision_executed(
            row,
            decision_index=decision_index,
            approved_by=identity.email,
            execution_result=result,
        )
        session.commit()
        return JSONResponse(
            api_v1.envelope(
                "agent-runs.decisions",
                _redact_payload(agent_runs_db.agent_run_to_dict(row, include_state=True), identity),
                meta={"executed": True, "decision_index": decision_index, "execution_result": result},
            )
        )

    # --- remediation workflow (tasks, evidence requests, exceptions) ---
    @app.get("/api/v1/remediation/tasks")
    def list_tasks(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        overdue_raw = (params.get("overdue") or [None])[0]
        overdue = None if overdue_raw is None else overdue_raw.lower() in {"1", "true", "yes"}
        rows = grc_services.list_tasks(
            session,
            identity.tenant_id,
            status=(params.get("status") or [None])[0],
            owner=(params.get("owner") or [None])[0],
            overdue=overdue,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(
            api_v1.envelope(
                "remediation.tasks", _redact_payload(rows, identity), meta=_page_meta(limit, offset, len(rows))
            )
        )

    @app.post("/api/v1/remediation/tasks", status_code=status.HTTP_201_CREATED)
    def create_task(
        body: CreateTaskRequest, identity: Identity = Depends(_require_write), session: Session = Depends(get_session)
    ) -> JSONResponse:
        try:
            task = grc_services.create_task(
                session,
                identity.tenant_id,
                title=body.title,
                description=body.description,
                control_id=body.control_id,
                violation_id=body.violation_id,
                owner=body.owner,
                priority=body.priority,
                due_at=_parse_dt(body.due_at),
                created_by=identity.email,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("remediation.tasks", task), status_code=status.HTTP_201_CREATED)

    @app.get("/api/v1/remediation/tasks/{task_id}")
    def get_task(
        task_id: str, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        task = remediation.get_task(session, tenant_id=identity.tenant_id, task_id=task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return JSONResponse(
            api_v1.envelope("remediation.tasks", _redact_payload(remediation.task_to_dict(task), identity))
        )

    @app.patch("/api/v1/remediation/tasks/{task_id}")
    def update_task(
        task_id: str,
        body: UpdateTaskRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        changes = body.model_dump(exclude_unset=True)
        if "due_at" in changes:
            changes["due_at"] = _parse_dt(changes["due_at"])
        try:
            task = grc_services.update_task(session, identity.tenant_id, task_id, changes=changes)
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("remediation.tasks", task))

    @app.get("/api/v1/remediation/evidence-requests")
    def list_evidence_requests(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        rows = remediation.list_evidence_requests(
            session,
            tenant_id=identity.tenant_id,
            status=(params.get("status") or [None])[0],
            limit=limit,
            offset=offset,
        )
        data = [remediation.evidence_request_to_dict(row) for row in rows]
        return JSONResponse(
            api_v1.envelope(
                "remediation.evidence_requests",
                _redact_payload(data, identity),
                meta=_page_meta(limit, offset, len(data)),
            )
        )

    @app.post("/api/v1/remediation/evidence-requests", status_code=status.HTTP_201_CREATED)
    def create_evidence_request(
        body: CreateEvidenceRequestRequest,
        identity: Identity = Depends(_require_evidence_request),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            req = remediation.create_evidence_request(
                session,
                tenant_id=identity.tenant_id,
                control_id=body.control_id,
                requested_from=body.requested_from,
                note=body.note,
                due_at=_parse_dt(body.due_at),
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(
            api_v1.envelope("remediation.evidence_requests", remediation.evidence_request_to_dict(req)),
            status_code=status.HTTP_201_CREATED,
        )

    @app.patch("/api/v1/remediation/evidence-requests/{request_id}")
    def update_evidence_request(
        request_id: str,
        body: EvidenceRequestStatusRequest,
        identity: Identity = Depends(_require_evidence_request),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            req = remediation.set_evidence_request_status(
                session, tenant_id=identity.tenant_id, request_id=request_id, status=body.status
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if req is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence request not found")
        session.commit()
        return JSONResponse(api_v1.envelope("remediation.evidence_requests", remediation.evidence_request_to_dict(req)))

    @app.get("/api/v1/remediation/exceptions")
    def list_exceptions(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        active_raw = (params.get("active") or [None])[0]
        rows = remediation.list_exceptions(
            session,
            tenant_id=identity.tenant_id,
            active_only=bool(active_raw and active_raw.lower() in {"1", "true", "yes"}),
            limit=limit,
            offset=offset,
        )
        data = [remediation.exception_to_dict(row) for row in rows]
        return JSONResponse(
            api_v1.envelope(
                "remediation.exceptions", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data))
            )
        )

    @app.post("/api/v1/remediation/exceptions", status_code=status.HTTP_201_CREATED)
    def create_exception(
        body: CreateExceptionRequest,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            exc_row = remediation.create_exception(
                session,
                tenant_id=identity.tenant_id,
                control_id=body.control_id,
                reason=body.reason,
                approved_by=body.approved_by or identity.email,
                expires_at=_parse_dt(body.expires_at),
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(
            api_v1.envelope("remediation.exceptions", remediation.exception_to_dict(exc_row)),
            status_code=status.HTTP_201_CREATED,
        )

    @app.delete("/api/v1/remediation/exceptions/{exception_id}")
    def revoke_exception(
        exception_id: str,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        revoked = remediation.revoke_exception(session, tenant_id=identity.tenant_id, exception_id=exception_id)
        if revoked is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="exception not found or not active")
        session.commit()
        return JSONResponse(api_v1.envelope("remediation.exceptions", remediation.exception_to_dict(revoked)))

    # --- risk register (GRC) ---
    @app.get("/api/v1/risks")
    def list_risks(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        data = grc_services.list_risks(
            session,
            identity.tenant_id,
            status=(params.get("status") or [None])[0],
            severity=(params.get("severity") or [None])[0],
            owner=(params.get("owner") or [None])[0],
            limit=limit,
            offset=offset,
        )
        return JSONResponse(
            api_v1.envelope("risks", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data)))
        )

    @app.post("/api/v1/risks", status_code=status.HTTP_201_CREATED)
    def create_risk(
        body: CreateRiskRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            risk = grc_services.create_risk(
                session,
                identity.tenant_id,
                title=body.title,
                description=body.description,
                category=body.category,
                severity=body.severity,
                likelihood=body.likelihood,
                impact=body.impact,
                status=body.status,
                treatment=body.treatment,
                owner=body.owner,
                control_id=body.control_id,
                asset_id=body.asset_id,
                due_at=_parse_dt(body.due_at),
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("risks", risk), status_code=status.HTTP_201_CREATED)

    @app.patch("/api/v1/risks/{risk_id}")
    def update_risk(
        risk_id: str,
        body: UpdateRiskRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        changes = body.model_dump(exclude_unset=True)
        if "due_at" in changes:
            changes["due_at"] = _parse_dt(changes["due_at"])
        try:
            risk = grc_services.update_risk(session, identity.tenant_id, risk_id, changes=changes)
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("risks", risk))

    @app.delete("/api/v1/risks/{risk_id}")
    def delete_risk(
        risk_id: str,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            result = grc_services.delete_risk(session, identity.tenant_id, risk_id)
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("risks", result))

    # --- access reviews (GRC) ---
    @app.get("/api/v1/access-reviews")
    def list_access_reviews(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        data = access_review_services.list_campaigns(
            session,
            identity.tenant_id,
            status=(params.get("status") or [None])[0],
            limit=limit,
            offset=offset,
        )
        return JSONResponse(
            api_v1.envelope(
                "access-reviews", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data))
            )
        )

    @app.post("/api/v1/access-reviews", status_code=status.HTTP_201_CREATED)
    def create_access_review(
        body: CreateCampaignRequest,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            campaign = access_review_services.create_campaign(
                session,
                identity.tenant_id,
                name=body.name,
                description=body.description,
                scope=body.scope,
                control_id=body.control_id,
                due_at=_parse_dt(body.due_at),
                created_by=identity.email,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews", campaign), status_code=status.HTTP_201_CREATED)

    # Registered before the ``/{campaign_id}`` route so the static segment wins.
    @app.get("/api/v1/access-reviews/coverage")
    def access_review_coverage(
        identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        data = access_review_services.control_coverage(session, identity.tenant_id)
        return JSONResponse(
            api_v1.envelope("access-reviews.coverage", _redact_payload(data, identity), meta={"count": len(data)})
        )

    @app.get("/api/v1/access-reviews/{campaign_id}")
    def get_access_review(
        campaign_id: str, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        try:
            data = access_review_services.get_campaign(session, identity.tenant_id, campaign_id)
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews", _redact_payload(data, identity)))

    @app.patch("/api/v1/access-reviews/{campaign_id}")
    def update_access_review_status(
        campaign_id: str,
        body: CampaignStatusRequest,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            campaign = access_review_services.set_campaign_status(
                session, identity.tenant_id, campaign_id, status=body.status
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews", campaign))

    @app.get("/api/v1/access-reviews/{campaign_id}/items")
    def list_access_review_items(
        campaign_id: str,
        request: Request,
        identity: Identity = Depends(_require_read),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        try:
            data = access_review_services.list_items(
                session,
                identity.tenant_id,
                campaign_id,
                decision=(params.get("decision") or [None])[0],
                limit=limit,
                offset=offset,
            )
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(
            api_v1.envelope(
                "access-reviews.items", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data))
            )
        )

    @app.post("/api/v1/access-reviews/{campaign_id}/items", status_code=status.HTTP_201_CREATED)
    def add_access_review_item(
        campaign_id: str,
        body: AddReviewItemRequest,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            item = access_review_services.add_item(
                session,
                identity.tenant_id,
                campaign_id,
                subject_id=body.subject_id,
                subject_name=body.subject_name,
                source=body.source,
                access_summary=body.access_summary,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews.items", item), status_code=status.HTTP_201_CREATED)

    @app.post("/api/v1/access-reviews/{campaign_id}/seed")
    def seed_access_review(
        campaign_id: str,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            result = access_review_services.seed_campaign_from_evidence(
                session, lake_for(identity), identity.tenant_id, campaign_id
            )
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews", result))

    @app.post("/api/v1/access-reviews/items/{item_id}/decision")
    def decide_access_review_item(
        item_id: str,
        body: ReviewDecisionRequest,
        identity: Identity = Depends(_require_control_manage),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            item = access_review_services.record_decision(
                session,
                identity.tenant_id,
                item_id,
                decision=body.decision,
                reviewer=identity.email,
                note=body.note,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except NotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse(api_v1.envelope("access-reviews.items", _redact_payload(item, identity)))

    # --- remediation guidance ---
    @app.get("/api/v1/controls/{control_id}/remediation")
    def control_remediation(
        control_id: str, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        control = load_control_catalog().get(control_id)
        if control is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="control not found")
        data = remediation_guidance.guidance_for_control(control)
        return JSONResponse(api_v1.envelope("controls.remediation", data))

    # --- tags ---
    @app.get("/api/v1/tags")
    def list_tags(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        limit, offset = _pagination(_params(request))
        rows = tags_db.list_tags(session, tenant_id=identity.tenant_id, limit=limit, offset=offset)
        data = [tags_db.tag_to_dict(t) for t in rows]
        return JSONResponse(
            api_v1.envelope("tags", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data)))
        )

    @app.post("/api/v1/tags", status_code=status.HTTP_201_CREATED)
    def create_tag(
        body: CreateTagRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            tag = tags_db.create_tag(session, tenant_id=identity.tenant_id, name=body.name, color=body.color)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(api_v1.envelope("tags", tags_db.tag_to_dict(tag)), status_code=status.HTTP_201_CREATED)

    @app.delete("/api/v1/tags/{tag_id}")
    def delete_tag(
        tag_id: str,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        deleted = tags_db.delete_tag(session, tenant_id=identity.tenant_id, tag_id=tag_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")
        session.commit()
        return JSONResponse(api_v1.envelope("tags", {"id": tag_id, "deleted": True}))

    @app.post("/api/v1/tags/attach", status_code=status.HTTP_201_CREATED)
    def attach_tag(
        body: AttachTagRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            et = tags_db.attach_tag(
                session,
                tenant_id=identity.tenant_id,
                tag_id=body.tag_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(
            api_v1.envelope("tags.attach", tags_db.entity_tag_to_dict(et)), status_code=status.HTTP_201_CREATED
        )

    @app.post("/api/v1/tags/detach")
    def detach_tag(
        body: AttachTagRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            removed = tags_db.detach_tag(
                session,
                tenant_id=identity.tenant_id,
                tag_id=body.tag_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="association not found")
        session.commit()
        return JSONResponse(api_v1.envelope("tags.detach", {"detached": True}))

    @app.get("/api/v1/tags/for")
    def tags_for_entity(
        request: Request,
        identity: Identity = Depends(_require_read),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        params = _params(request)
        entity_type = (params.get("entity_type") or [None])[0]
        entity_id = (params.get("entity_id") or [None])[0]
        if not entity_type or not entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="entity_type and entity_id are required"
            )
        rows = tags_db.tags_for_entity(
            session, tenant_id=identity.tenant_id, entity_type=entity_type, entity_id=entity_id
        )
        data = [tags_db.tag_to_dict(t) for t in rows]
        return JSONResponse(api_v1.envelope("tags.for", data, meta={"count": len(data)}))

    # --- saved views ---
    @app.get("/api/v1/saved-views")
    def list_saved_views(
        request: Request,
        identity: Identity = Depends(_require_read),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        params = _params(request)
        limit, offset = _pagination(params)
        surface = (params.get("surface") or [None])[0]
        rows = tags_db.list_saved_views(
            session, tenant_id=identity.tenant_id, surface=surface, limit=limit, offset=offset
        )
        data = [tags_db.saved_view_to_dict(v) for v in rows]
        return JSONResponse(
            api_v1.envelope("saved_views", _redact_payload(data, identity), meta=_page_meta(limit, offset, len(data)))
        )

    @app.post("/api/v1/saved-views", status_code=status.HTTP_201_CREATED)
    def create_saved_view(
        body: CreateSavedViewRequest,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        try:
            view = tags_db.create_saved_view(
                session,
                tenant_id=identity.tenant_id,
                surface=body.surface,
                name=body.name,
                filters=body.filters,
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(
            api_v1.envelope("saved_views", tags_db.saved_view_to_dict(view)), status_code=status.HTTP_201_CREATED
        )

    @app.delete("/api/v1/saved-views/{view_id}")
    def delete_saved_view(
        view_id: str,
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        deleted = tags_db.delete_saved_view(session, tenant_id=identity.tenant_id, view_id=view_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="saved view not found")
        session.commit()
        return JSONResponse(api_v1.envelope("saved_views", {"id": view_id, "deleted": True}))

    # --- metrics & insights ---
    @app.get("/api/v1/insights/timeseries")
    def insights_timeseries(
        request: Request,
        identity: Identity = Depends(_require_read),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        raw_limit = (_params(request).get("limit") or [None])[0]
        limit = int(raw_limit) if raw_limit and raw_limit.isdigit() else 90
        limit = min(max(limit, 1), 1000)
        points = metrics_db.list_metric_points(session, tenant_id=identity.tenant_id, limit=limit)
        rows = [metrics_db.metric_point_to_dict(p) for p in points]
        return JSONResponse(
            api_v1.envelope("insights.timeseries", _redact_payload(rows, identity), meta={"count": len(rows)})
        )

    @app.get("/api/v1/insights/remediation")
    def insights_remediation(
        identity: Identity = Depends(_require_read),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        data = metrics_db.remediation_insights(session, tenant_id=identity.tenant_id)
        return JSONResponse(api_v1.envelope("insights.remediation", _redact_payload(data, identity)))

    @app.post("/api/v1/insights/capture", status_code=status.HTTP_201_CREATED)
    def insights_capture(
        identity: Identity = Depends(_require_write),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        point = metrics_db.capture_metric_point(session, tenant_id=identity.tenant_id, lake_dir=lake_for(identity))
        session.commit()
        return JSONResponse(
            api_v1.envelope("insights.timeseries", metrics_db.metric_point_to_dict(point)),
            status_code=status.HTTP_201_CREATED,
        )

    @app.get("/api/v1/frameworks/{framework_id}/detail", tags=["data"])
    def v1_framework_detail(framework_id: str, identity: Identity = Depends(_require_read)) -> JSONResponse:
        _status, body = api_v1.handle_get(f"/api/v1/frameworks/{framework_id}/detail", {}, lake_for(identity))
        return JSONResponse(_redact_payload(body, identity), status_code=int(_status))

    # --- versioned data surface (authenticated) ---
    @app.get("/api/v1/{rest:path}")
    def v1_get(rest: str, request: Request, identity: Identity = Depends(_require_read)) -> JSONResponse:
        _status, body = api_v1.handle_get(f"/api/v1/{rest}", _params(request), lake_for(identity))
        return JSONResponse(_redact_payload(body, identity), status_code=int(_status))

    @app.post("/api/v1/{rest:path}")
    async def v1_post(rest: str, request: Request, identity: Identity = Depends(_require_read)) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - empty/invalid body is treated as no body
            body = {}
        v1_path = f"/api/v1/{rest}"
        required_scope = api_v1.required_post_scope(v1_path)
        if not identity.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires scope: {required_scope}",
            )
        # handle_post rebuilds posture and writes a snapshot; offload so it does
        # not block the event loop.
        _status, payload = await run_in_threadpool(api_v1.handle_post, v1_path, body, lake_for(identity))
        return JSONResponse(payload, status_code=int(_status))

    # --- legacy console surface (authenticated; same handlers as local mode) ---
    # Registered after the v1 routes so /api/v1/* and /api/healthz keep priority.
    @app.get("/api/{rest:path}")
    def legacy_get(rest: str, request: Request, identity: Identity = Depends(_require_read)) -> JSONResponse:
        _status, body = api_legacy.handle_get(f"/api/{rest}", _params(request), lake_for(identity))
        return JSONResponse(_redact_payload(body, identity), status_code=int(_status))

    @app.post("/api/{rest:path}")
    async def legacy_post(rest: str, request: Request, identity: Identity = Depends(_require_read)) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - empty/invalid body is treated as no body
            body = {}
        legacy_path = f"/api/{rest}"
        required_scope = api_legacy.required_post_scope(legacy_path)
        if not identity.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires scope: {required_scope}",
            )
        if request.headers.get("Idempotency-Key") and "idempotency_key" not in body:
            body = {**body, "idempotency_key": request.headers["Idempotency-Key"]}
        # Legacy POSTs run workflows, connector syncs (full pipeline + network),
        # and scheduler ticks; offload so they do not block the event loop.
        return await run_in_threadpool(_legacy_post_response, legacy_path, body, lake_for(identity), identity)

    @app.get("/", response_class=HTMLResponse)
    @app.get("/console", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        return HTMLResponse(dashboard.read_text(encoding="utf-8"))

    if web_dist is not None:
        # The public trust page is a static export under a dynamic segment, so
        # only one placeholder is prebuilt. Serve that prebuilt HTML for any
        # token path (the client reads the real token from the URL); registered
        # before the StaticFiles mount so arbitrary tokens are not a 404. No
        # auth — this is the unauthenticated reviewer surface.
        trust_page = web_dist / "trust" / "share" / "index.html"

        @app.get("/console/trust/{token}", response_class=HTMLResponse)
        def public_trust_page(token: str) -> HTMLResponse:  # noqa: ARG001 - token read client-side
            if not trust_page.is_file():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
            return HTMLResponse(trust_page.read_text(encoding="utf-8"))

        # Next.js static export; html=True resolves /console/<route>/ to index.html.
        app.mount("/console", StaticFiles(directory=str(web_dist), html=True), name="console")

    return app


def serve(lake_dir: str | Path, *, host: str = "127.0.0.1", port: int = 8787, require_auth: bool = True) -> None:
    """Run the server-mode app under uvicorn."""
    import uvicorn

    uvicorn.run(create_app(lake_dir, require_auth=require_auth), host=host, port=port)
