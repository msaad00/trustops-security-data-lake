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
import json
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from security_lakehouse import api_legacy, api_v1, tenancy
from security_lakehouse.auth.dependencies import get_session, require_scope
from security_lakehouse.auth.oidc import OIDCLoginError, build_oauth, complete_oidc_login, load_oidc_config
from security_lakehouse.auth.rbac import Identity
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
from security_lakehouse.dashboard import render_dashboard
from security_lakehouse.db import metrics as metrics_db
from security_lakehouse.db import migrate, remediation, repository
from security_lakehouse.db import tags as tags_db
from security_lakehouse.db.base import create_engine_for, session_factory
from security_lakehouse.web import web_dist_dir, web_dist_index

_COOKIE_SECURE = os.environ.get("TRUSTOPS_COOKIE_SECURE", "true").lower() in {"1", "true", "yes", "on"}

_ERROR_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found"}
_LEGACY_ERROR_REASONS = {
    HTTPStatus.BAD_REQUEST: "invalid request",
    HTTPStatus.FORBIDDEN: "forbidden",
    HTTPStatus.NOT_FOUND: "not found",
}

# Scope dependencies are built once (module-level) and reused as route defaults.
_require_read = require_scope("read")
_require_write = require_scope("write")
_require_snapshot = require_scope("snapshot")
_require_admin = require_scope("auth_admin")
_require_evidence_request = require_scope("evidence_request")
_require_control_manage = require_scope("control_manage")
_REDACTED_FIELDS = {"owner", "asset_owner", "actor", "assignee", "note", "credentials"}


class CreateKeyRequest(BaseModel):
    user_email: str
    name: str = ""
    expires_in_days: int | None = None


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    control_id: str | None = None
    violation_id: str | None = None
    owner: str = ""
    priority: str = "medium"
    due_at: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    status: str | None = None
    priority: str | None = None
    due_at: str | None = None


class CreateEvidenceRequestRequest(BaseModel):
    control_id: str
    requested_from: str = ""
    note: str = ""
    due_at: str | None = None


class EvidenceRequestStatusRequest(BaseModel):
    status: str


class CreateExceptionRequest(BaseModel):
    control_id: str
    reason: str = ""
    approved_by: str = ""
    expires_at: str | None = None


class CreateTagRequest(BaseModel):
    name: str
    color: str = ""


class AttachTagRequest(BaseModel):
    tag_id: str
    entity_type: str
    entity_id: str


class CreateSavedViewRequest(BaseModel):
    surface: str
    name: str
    filters: dict = {}


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


def _insecure_requested() -> bool:
    return os.environ.get("TRUSTOPS_ALLOW_INSECURE_NO_AUTH", "").lower() in {"1", "true", "yes"}


def _redact_payload(payload: object, identity: Identity) -> object:
    if identity.role != "auditor":
        return payload
    if isinstance(payload, dict):
        return {
            key: ("[redacted]" if key in _REDACTED_FIELDS else _redact_payload(value, identity))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_redact_payload(item, identity) for item in payload]
    return payload


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
    lake = Path(lake_dir)
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
            {"name": "remediation", "description": "Tasks, evidence requests, control exceptions."},
            {"name": "insights", "description": "Posture time-series and remediation metrics."},
            {"name": "tags", "description": "Cross-entity tags and saved views."},
        ],
    )
    app.state.sessionmaker = session_factory(engine)
    app.state.require_auth = require_auth and not _insecure_requested()

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

    @app.exception_handler(StarletteHTTPException)
    async def _error_envelope(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _ERROR_CODES.get(exc.status_code, "error")
        return JSONResponse(
            api_v1.error_envelope(code, str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    # --- open health checks (registered before the authenticated catch-all) ---
    @app.get("/api/healthz")
    def healthz() -> dict[str, object]:
        return {"ok": True, "service": "trustops-assessment"}

    @app.get("/api/v1/healthz", tags=["discovery"])
    def v1_healthz() -> JSONResponse:
        _status, body = api_v1.handle_get("/api/v1/healthz", {}, lake)
        return JSONResponse(body, status_code=int(_status))

    @app.get("/api/v1", tags=["discovery"])
    def v1_index(_identity: Identity = Depends(_require_read)) -> JSONResponse:
        # Self-describing contract so headless agents can enumerate the surface.
        return JSONResponse(
            api_v1.envelope(
                "index",
                {
                    "api_version": api_v1.API_VERSION,
                    "resources": api_v1.resource_catalog(),
                    "collection_controls": {
                        "limit": "1-1000 (default 100)",
                        "offset": ">= 0",
                        "sort": "field, or -field for descending",
                        "filters": "any field=value (comma-separated values = OR)",
                    },
                    "auth": {
                        "api_key": "Authorization: Bearer <token>",
                        "session": "httpOnly cookie via OIDC/SAML SSO",
                        "methods_endpoint": "/api/v1/auth/methods",
                    },
                    "streams": ["/api/v1/stream"],
                    "openapi": "/openapi.json",
                    "docs": "/docs",
                },
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

    # --- remediation workflow (tasks, evidence requests, exceptions) ---
    @app.get("/api/v1/remediation/tasks")
    def list_tasks(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        params = _params(request)
        overdue_raw = (params.get("overdue") or [None])[0]
        overdue = None if overdue_raw is None else overdue_raw.lower() in {"1", "true", "yes"}
        tasks = remediation.list_tasks(
            session,
            tenant_id=identity.tenant_id,
            status=(params.get("status") or [None])[0],
            owner=(params.get("owner") or [None])[0],
            overdue=overdue,
        )
        rows = [remediation.task_to_dict(task) for task in tasks]
        return JSONResponse(
            api_v1.envelope("remediation.tasks", _redact_payload(rows, identity), meta={"count": len(rows)})
        )

    @app.post("/api/v1/remediation/tasks", status_code=status.HTTP_201_CREATED)
    def create_task(
        body: CreateTaskRequest, identity: Identity = Depends(_require_write), session: Session = Depends(get_session)
    ) -> JSONResponse:
        try:
            task = remediation.create_task(
                session,
                tenant_id=identity.tenant_id,
                title=body.title,
                description=body.description,
                control_id=body.control_id,
                violation_id=body.violation_id,
                owner=body.owner,
                priority=body.priority,
                due_at=_parse_dt(body.due_at),
                created_by=identity.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        session.commit()
        return JSONResponse(
            api_v1.envelope("remediation.tasks", remediation.task_to_dict(task)), status_code=status.HTTP_201_CREATED
        )

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
            task = remediation.update_task(session, tenant_id=identity.tenant_id, task_id=task_id, changes=changes)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        session.commit()
        return JSONResponse(api_v1.envelope("remediation.tasks", remediation.task_to_dict(task)))

    @app.get("/api/v1/remediation/evidence-requests")
    def list_evidence_requests(
        request: Request, identity: Identity = Depends(_require_read), session: Session = Depends(get_session)
    ) -> JSONResponse:
        rows = remediation.list_evidence_requests(
            session, tenant_id=identity.tenant_id, status=(_params(request).get("status") or [None])[0]
        )
        data = [remediation.evidence_request_to_dict(row) for row in rows]
        return JSONResponse(
            api_v1.envelope("remediation.evidence_requests", _redact_payload(data, identity), meta={"count": len(data)})
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
        active_raw = (_params(request).get("active") or [None])[0]
        rows = remediation.list_exceptions(
            session,
            tenant_id=identity.tenant_id,
            active_only=bool(active_raw and active_raw.lower() in {"1", "true", "yes"}),
        )
        data = [remediation.exception_to_dict(row) for row in rows]
        return JSONResponse(
            api_v1.envelope("remediation.exceptions", _redact_payload(data, identity), meta={"count": len(data)})
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

    # --- tags ---
    @app.get("/api/v1/tags")
    def list_tags(identity: Identity = Depends(_require_read), session: Session = Depends(get_session)) -> JSONResponse:
        rows = tags_db.list_tags(session, tenant_id=identity.tenant_id)
        data = [tags_db.tag_to_dict(t) for t in rows]
        return JSONResponse(api_v1.envelope("tags", _redact_payload(data, identity), meta={"count": len(data)}))

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
        surface = (_params(request).get("surface") or [None])[0]
        rows = tags_db.list_saved_views(session, tenant_id=identity.tenant_id, surface=surface)
        data = [tags_db.saved_view_to_dict(v) for v in rows]
        return JSONResponse(api_v1.envelope("saved_views", _redact_payload(data, identity), meta={"count": len(data)}))

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
        _status, body = api_v1.handle_get(f"/api/v1/frameworks/{framework_id}/detail", {}, lake)
        return JSONResponse(_redact_payload(body, identity), status_code=int(_status))

    # --- versioned data surface (authenticated) ---
    @app.get("/api/v1/{rest:path}")
    def v1_get(rest: str, request: Request, identity: Identity = Depends(_require_read)) -> JSONResponse:
        _status, body = api_v1.handle_get(f"/api/v1/{rest}", _params(request), lake_for(identity))
        return JSONResponse(_redact_payload(body, identity), status_code=int(_status))

    @app.post("/api/v1/{rest:path}")
    async def v1_post(rest: str, request: Request, identity: Identity = Depends(_require_snapshot)) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - empty/invalid body is treated as no body
            body = {}
        # handle_post rebuilds posture and writes a snapshot; offload so it does
        # not block the event loop.
        _status, payload = await run_in_threadpool(api_v1.handle_post, f"/api/v1/{rest}", body, lake_for(identity))
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
        # Legacy POSTs run workflows, connector syncs (full pipeline + network),
        # and scheduler ticks; offload so they do not block the event loop.
        return await run_in_threadpool(_legacy_post_response, legacy_path, body, lake_for(identity), identity)

    @app.get("/", response_class=HTMLResponse)
    @app.get("/console", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        return HTMLResponse(dashboard.read_text(encoding="utf-8"))

    if web_dist is not None:
        # Next.js static export; html=True resolves /console/<route>/ to index.html.
        app.mount("/console", StaticFiles(directory=str(web_dist), html=True), name="console")

    return app


def serve(lake_dir: str | Path, *, host: str = "127.0.0.1", port: int = 8787, require_auth: bool = True) -> None:
    """Run the server-mode app under uvicorn."""
    import uvicorn

    uvicorn.run(create_app(lake_dir, require_auth=require_auth), host=host, port=port)
