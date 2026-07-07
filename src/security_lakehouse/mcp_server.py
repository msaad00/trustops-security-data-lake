"""Agent-native MCP server exposing the TrustOps read surface.

This is the headless front door for autonomous agents. Rather than driving the
HTTP API, an agent speaks the Model Context Protocol (MCP) over stdio and calls
typed tools to inspect compliance posture, controls, evidence, assets, and
violations.

The tools are thin adapters over the existing assessment engine
(:mod:`security_lakehouse.api_v1`, :mod:`security_lakehouse.assessment`,
:mod:`security_lakehouse.io`) — no compliance logic is reimplemented here, so the
agent contract cannot drift from the HTTP API contract.

The optional ``mcp`` dependency is imported lazily inside :func:`build_server`
so that importing this module (and the rest of the package) never requires the
SDK to be installed. Install it with ``pip install 'trustops[mcp]'`` and run the
``trustops-mcp`` console script.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

from security_lakehouse import api_v1, workflows
from security_lakehouse.assessment import build_current_posture
from security_lakehouse.brand_assets import (
    MCP_INSTRUCTIONS,
    MCP_SERVER_NAME,
    MCP_WEBSITE_URL,
    human_tool_title,
    mcp_icons,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.server.fastmcp import FastMCP

DEFAULT_LAKE = "./lake"
JsonObject = dict[str, Any]


def resolve_lake_dir() -> Path:
    """Resolve the lake directory once from ``TRUSTOPS_LAKE`` (default ``./lake``)."""
    return Path(os.environ.get("TRUSTOPS_LAKE", DEFAULT_LAKE)).expanduser().resolve()


def resolve_api_base_url() -> str:
    """Resolve the authenticated TrustOps API base URL for remote MCP tools."""
    base_url = os.environ.get("TRUSTOPS_API_URL", "").strip().rstrip("/")
    if not base_url:
        raise ValueError("TRUSTOPS_API_URL is required for authenticated TrustOps MCP tools")
    scheme = urllib.parse.urlparse(base_url).scheme
    if scheme not in {"http", "https"}:
        raise ValueError("TRUSTOPS_API_URL must use http or https")
    return base_url


def _api_key() -> str:
    token = os.environ.get("TRUSTOPS_API_KEY", "").strip()
    if not token:
        raise ValueError("TRUSTOPS_API_KEY is required for authenticated TrustOps MCP tools")
    return token


def _get(path: str, lake: Path, **params: str) -> Any:
    """Run a v1 GET through the existing engine and unwrap the envelope ``data``.

    Collection query params (``limit``, ``offset``, ``sort``, filters) are passed
    through to :func:`security_lakehouse.api_v1.handle_get`, so pagination and
    filtering behave exactly as they do over HTTP.
    """
    query = {key: [value] for key, value in params.items() if value is not None}
    status, body = api_v1.handle_get(path, query, lake)
    if status != HTTPStatus.OK:
        errors = body.get("errors") or [{"detail": "request failed"}]
        raise ValueError(errors[0].get("detail", "request failed"))
    return body["data"]


def _api_error_detail(payload: bytes) -> str:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "request failed"
    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors and isinstance(errors[0], dict):
        return str(errors[0].get("detail") or errors[0].get("code") or "request failed")
    detail = body.get("detail") if isinstance(body, dict) else None
    return str(detail or "request failed")


def _server_api_request(method: str, path: str, body: dict[str, Any] | None = None, **params: Any) -> JsonObject:
    """Call the authenticated server API for DB-backed/headless MCP tools."""
    query = {
        key: str(value)
        for key, value in params.items()
        if value is not None and not (isinstance(value, str) and value == "")
    }
    url = f"{resolve_api_base_url()}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = json.dumps(body or {}).encode("utf-8") if method.upper() != "GET" else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={
            "accept": "application/json",
            "authorization": f"Bearer {_api_key()}",
            **({"content-type": "application/json"} if data is not None else {}),
        },
    )
    timeout = float(os.environ.get("TRUSTOPS_API_TIMEOUT_SECONDS", "30"))
    try:
        with urllib.request.urlopen(request, timeout=max(1.0, min(timeout, 120.0))) as response:  # noqa: S310
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"TrustOps API request failed ({exc.code}): {_api_error_detail(exc.read())}") from exc
    except urllib.error.URLError as exc:
        raise ValueError("TrustOps API request failed: unreachable") from exc
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("TrustOps API request failed: invalid JSON response") from exc
    if not isinstance(decoded, dict):
        raise ValueError("TrustOps API request failed: invalid response shape")
    return decoded


def build_server(lake_dir: Path | None = None) -> FastMCP:
    """Construct the FastMCP server with the read tools bound to a lake directory.

    Importing ``mcp`` is deferred to here so the module stays import-safe without
    the optional dependency installed.
    """
    from mcp.server.fastmcp import FastMCP

    lake = (lake_dir or resolve_lake_dir()).resolve()
    tool_icons = mcp_icons()
    mcp = FastMCP(
        MCP_SERVER_NAME,
        instructions=MCP_INSTRUCTIONS,
        website_url=MCP_WEBSITE_URL,
        icons=tool_icons,
    )

    def trustops_tool(**kwargs):  # noqa: ANN003
        """Register an MCP tool with TrustOps display title and brand icon."""
        title = kwargs.pop("title", None)
        icons = kwargs.pop("icons", tool_icons)

        def decorator(fn):  # noqa: ANN001
            display_title = title or human_tool_title(fn.__name__)
            return mcp.tool(title=display_title, icons=icons, **kwargs)(fn)

        return decorator

    @trustops_tool()
    def get_posture() -> JsonObject:
        """Return the current compliance posture summary.

        Includes the overall score and state, per-framework scores, open
        violations, top risk assets, and evidence-freshness rollups — the
        continuously refreshed answer to "are we compliant right now?".
        """
        return _get("/api/v1/posture/current", lake)

    @trustops_tool()
    def posture_as_of(as_of: str) -> JsonObject:
        """Return the compliance posture as of a point in time.

        Selects the newest snapshot whose ``evaluated_at`` is at or before
        ``as_of`` (an ISO date or datetime, e.g. ``2026-04-15``). Use this to
        answer "were we compliant on date X?" against immutable snapshots
        rather than the live posture.
        """
        return _get("/api/v1/posture/as-of", lake, as_of=as_of)

    @trustops_tool()
    def list_controls(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List control posture rows (one per framework control, with pass/fail status)."""
        return _get("/api/v1/controls", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_control_tests(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List control-test results that produced the control posture."""
        return _get("/api/v1/control-tests", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_evidence(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List normalized evidence events backing the assessment.

        Use ``limit`` to cap the number of rows returned (1-1000, default 100).
        """
        return _get("/api/v1/evidence", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_assets(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List assets with their computed risk scores."""
        return _get("/api/v1/assets", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_violations(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List open control/asset violations requiring owner action, highest severity first."""
        return _get("/api/v1/violations", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_snapshots(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List point-in-time assessment snapshots written to the gold zone (for audit/JIT review)."""
        return _get("/api/v1/snapshots", lake, limit=str(limit), offset=str(offset))

    @trustops_tool()
    def list_audit_log(category: str = "", limit: int = 100, include_requests: bool = False) -> list[JsonObject]:
        """List unified activity log entries from the lake (connectors, triage, workflows).

        Each row includes stable ``event_id`` and UTC ``occurred_at``. Set
        ``include_requests=true`` only when request audit JSONL is present locally.
        """
        from security_lakehouse.audit_log import build_audit_log

        capped = max(1, min(limit, 1000))
        return build_audit_log(
            lake,
            category=category or None,
            limit=capped,
            include_requests=include_requests,
        )

    @trustops_tool()
    def list_frameworks() -> list[JsonObject]:
        """List the compliance frameworks in the registry (id, name, version, source, status).

        Falls back to the framework scores observed in the current posture if the
        static registry cannot be loaded.
        """
        try:
            from security_lakehouse.catalog import load_framework_registry

            return list(load_framework_registry().values())
        except Exception:  # noqa: BLE001 - registry is optional; degrade gracefully
            posture = build_current_posture(lake)
            return posture.get("frameworks", [])

    @trustops_tool(title="Ingestion Status")
    def get_ingestion_status() -> JsonObject:
        """Return live ingestion health, scale tier, schedules, and recommended actions.

        Includes connector freshness, pipeline artifact counts, split ingest/eval
        schedules, warehouse tier (local incremental vs warehouse-required), and the
        latest lake evaluation run — the same payload as ``GET /api/v1/ingestion/status``.
        """
        return _get("/api/v1/ingestion/status", lake)

    @trustops_tool(title="List Eval Runs")
    def list_eval_runs(limit: int = 25) -> list[JsonObject]:
        """Return recent lake-wide evaluation runs from split ingest/eval schedules."""
        return _get("/api/v1/ingestion/eval/runs", lake, limit=str(limit))

    @trustops_tool(title="Run Lake Eval")
    def run_lake_eval(actor: str = "mcp") -> JsonObject:
        """Materialize and evaluate the lake on the scale-appropriate path.

        Uses incremental materialize below 100k events, or projects to a configured
        warehouse sink above that threshold. This is the lake-wide eval step that
        split schedules run separately from connector ingest syncs.
        """
        status, body = api_v1.handle_post("/api/v1/ingestion/eval", {"actor": actor}, lake)
        if status not in {HTTPStatus.CREATED, HTTPStatus.OK}:
            errors = body.get("errors") or [{"detail": "lake eval failed"}]
            raise ValueError(errors[0].get("detail", "lake eval failed"))
        return body["data"]

    @trustops_tool(title="Scheduler Tick")
    def run_scheduler_tick() -> JsonObject:
        """Fire every due connector sync, lake eval, and cron workflow once.

        Mirrors ``security-lakehouse scheduler tick`` and the production CronJob:
        ingest-only connector syncs on ``sync_schedule``, lake eval on
        ``eval_schedule``, with advisory locking to prevent double-fires.
        """
        status, body = api_v1.handle_post("/api/v1/scheduler/tick", {}, lake)
        if status not in {HTTPStatus.CREATED, HTTPStatus.OK}:
            errors = body.get("errors") or [{"detail": "scheduler tick failed"}]
            raise ValueError(errors[0].get("detail", "scheduler tick failed"))
        return body["data"]

    @trustops_tool(title="Sync Connector")
    def sync_connector(connector_id: str, materialize: bool | None = None, actor: str = "mcp") -> JsonObject:
        """Run one connector sync into the managed raw lake.

        When ``materialize`` is omitted, split ingest/eval defaults apply
        (ingest-only if ``split_ingest_eval`` is enabled on the connector).
        """
        payload: dict[str, Any] = {"actor": actor}
        if materialize is not None:
            payload["materialize"] = materialize
        path = f"/api/v1/connectors/{urllib.parse.quote(connector_id, safe='')}/sync"
        status, body = api_v1.handle_post(path, payload, lake)
        if status != HTTPStatus.CREATED:
            errors = body.get("errors") or [{"detail": "connector sync failed"}]
            raise ValueError(errors[0].get("detail", "connector sync failed"))
        return body["data"]

    @trustops_tool(title="List Connector Runs")
    def list_connector_runs(connector_id: str = "", limit: int = 50) -> list[JsonObject]:
        """List probe, discover, and sync run history from the lake."""
        from security_lakehouse.connector_state import list_runs

        return list_runs(lake, connector_id or None, limit=limit)

    @trustops_tool(title="Describe API")
    def describe_api() -> list[JsonObject]:
        """Describe the available v1 resources so an agent can discover the surface.

        Returns the self-describing resource catalog (paths, kinds, methods, query
        params) used by the HTTP API — the same contract these MCP tools wrap.
        """
        return api_v1.resource_catalog()

    # ------------------------------------------------------------------
    # Authenticated server tools — DB-backed harness operations.
    #
    # These call the deployed TrustOps server over HTTPS/HTTP using
    # TRUSTOPS_API_URL and TRUSTOPS_API_KEY. They intentionally do not access
    # the local lake directly, because persisted harness runs, approvals, RBAC,
    # tenant isolation, and audit events live behind the server API boundary.
    # ------------------------------------------------------------------

    @trustops_tool()
    def list_agent_runs(limit: int = 100, harness: str = "", status: str = "") -> JsonObject:
        """List persisted human/headless agent harness runs through the authenticated API.

        Requires ``TRUSTOPS_API_URL`` and ``TRUSTOPS_API_KEY``. Returns the full
        v1 envelope so the caller can inspect `meta.count`, filters, and errors.
        """
        return _server_api_request("GET", "/api/v1/agent-runs", limit=limit, harness=harness, status=status)

    @trustops_tool()
    def create_agent_run(
        harness: str = "posture_review",
        objective: str = "",
        role: str = "",
        idempotency_key: str = "",
        orchestrator: str = "sequential",
        use_model: bool = False,
        max_context_chars: int | None = None,
        max_fact_items: int | None = None,
        max_output_tokens: int | None = None,
    ) -> JsonObject:
        """Run and persist a governed agent harness through the authenticated API.

        The server resolves the tenant/account lake, provider configuration, RBAC,
        data-readiness preflight, and idempotency. Raw model keys are never sent
        through this tool.
        """
        payload: dict[str, Any] = {
            "harness": harness,
            "objective": objective,
            "orchestrator": orchestrator,
            "use_model": use_model,
        }
        if role:
            payload["role"] = role
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        if max_context_chars is not None:
            payload["max_context_chars"] = max_context_chars
        if max_fact_items is not None:
            payload["max_fact_items"] = max_fact_items
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens
        return _server_api_request("POST", "/api/v1/agent-runs", payload)

    @trustops_tool()
    def get_agent_run(run_id: str) -> JsonObject:
        """Inspect one persisted agent harness run through the authenticated API."""
        return _server_api_request("GET", f"/api/v1/agent-runs/{urllib.parse.quote(run_id, safe='')}")

    @trustops_tool(title="Approve Agent Decision")
    def approve_agent_decision(run_id: str, decision_index: int, note: str = "") -> JsonObject:
        """Approve one stored harness decision and execute its allowlisted TrustOps write.

        Execution is idempotent server-side: retrying an already executed
        decision returns the stored execution result instead of duplicating work.
        """
        encoded_run = urllib.parse.quote(run_id, safe="")
        return _server_api_request(
            "POST",
            f"/api/v1/agent-runs/{encoded_run}/decisions/{decision_index}/approve",
            {"note": note},
        )

    @trustops_tool(title="Audit Readiness")
    def get_audit_readiness() -> JsonObject:
        """Return audit score, blocking gaps, and workflow coverage checklist.

        Requires ``TRUSTOPS_API_URL`` and ``TRUSTOPS_API_KEY`` — tenant-scoped
        fields (evidence requests, access reviews, trust shares) live in the app DB.
        """
        return _server_api_request("GET", "/api/v1/platform/audit-readiness")

    @trustops_tool(title="Evidence Freshness Summary")
    def get_evidence_freshness_summary() -> JsonObject:
        """Return SLA breach rollups: fresh rate, stale counts, and top breaches by source."""
        return _server_api_request("GET", "/api/v1/evidence/freshness/summary")

    @trustops_tool(title="Escalate Stale Evidence")
    def escalate_stale_evidence(limit: int = 10) -> JsonObject:
        """Create remediation tasks for stale, expired, or missing evidence rows."""
        return _server_api_request(
            "POST",
            "/api/v1/evidence/freshness/escalate",
            body={"limit": limit, "statuses": ["stale", "expired", "missing"]},
        )

    @trustops_tool(title="Insights Timeseries")
    def get_insights_timeseries(limit: int = 14) -> JsonObject:
        """Return captured posture trend points (score, fresh rate, violations)."""
        return _server_api_request("GET", "/api/v1/insights/timeseries", limit=str(limit))

    @trustops_tool(title="Insights Remediation")
    def get_insights_remediation() -> JsonObject:
        """Return remediation SLA rollups: open/overdue counts, MTTR, attainment."""
        return _server_api_request("GET", "/api/v1/insights/remediation")

    @trustops_tool(title="Insights Framework Trends")
    def get_insights_framework_trends(limit: int = 90) -> JsonObject:
        """Return per-framework readiness scores over time from snapshots and live posture."""
        return _server_api_request("GET", "/api/v1/insights/framework-trends", limit=str(limit))

    @trustops_tool(title="Insights SLA Heatmap")
    def get_insights_sla_heatmap() -> JsonObject:
        """Return remediation task counts by priority and SLA state for exec dashboards."""
        return _server_api_request("GET", "/api/v1/insights/sla-heatmap")

    @trustops_tool(title="List Vendor Assessments")
    def list_vendor_assessments(status: str = "", limit: int = 100) -> JsonObject:
        """List tenant vendor diligence questionnaires (requires server API auth)."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return _server_api_request("GET", "/api/v1/vendor-assessments", **params)

    @trustops_tool(title="List Policies")
    def list_policies(status: str = "", limit: int = 100) -> JsonObject:
        """List tenant policy documents adopted from bundled templates."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return _server_api_request("GET", "/api/v1/policies", **params)

    @trustops_tool(title="List Policy Templates")
    def list_policy_templates() -> JsonObject:
        """List bundled policy templates available for adoption."""
        return _server_api_request("GET", "/api/v1/policy-templates")

    @trustops_tool(title="List Access Reviews")
    def list_access_reviews(status: str = "", limit: int = 100) -> JsonObject:
        """List periodic access-review campaigns (requires server API auth)."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return _server_api_request("GET", "/api/v1/access-reviews", **params)

    @trustops_tool(title="Access Review Coverage")
    def get_access_reviews_coverage() -> JsonObject:
        """Return control coverage rows for active access-review campaigns."""
        return _server_api_request("GET", "/api/v1/access-reviews/coverage")

    @trustops_tool(title="List Evidence Requests")
    def list_evidence_requests(status: str = "", limit: int = 100) -> JsonObject:
        """List open or historical evidence requests tied to controls."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return _server_api_request("GET", "/api/v1/remediation/evidence-requests", **params)

    @trustops_tool(title="List Trust Shares")
    def list_trust_shares(include_revoked: bool = False) -> list[JsonObject]:
        """List auditor trust-center shares issued from this lake (tokens never returned)."""
        from security_lakehouse.trust_share import list_shares

        return list_shares(lake, include_revoked=include_revoked)

    @trustops_tool(title="Policy Attestation Summary")
    def get_policy_attestation_summary() -> JsonObject:
        """Return published vs acknowledged policy counts for audit prep."""
        return _server_api_request("GET", "/api/v1/policies/attestation-summary")

    @trustops_tool(title="List Tags")
    def list_tags() -> JsonObject:
        """List tenant tags for cross-entity navigation and filtering."""
        return _server_api_request("GET", "/api/v1/tags")

    @trustops_tool(title="List Tag Entities")
    def list_tag_entities(tag_id: str, entity_type: str = "") -> JsonObject:
        """List entity ids attached to a tag, optionally filtered by entity type."""
        params: dict[str, Any] = {"tag_id": tag_id}
        if entity_type:
            params["entity_type"] = entity_type
        return _server_api_request("GET", "/api/v1/tags/entities", **params)

    @trustops_tool(title="List Saved Views")
    def list_saved_views(surface: str = "") -> JsonObject:
        """List saved filter views for a console surface (e.g. controls, violations)."""
        params: dict[str, Any] = {}
        if surface:
            params["surface"] = surface
        return _server_api_request("GET", "/api/v1/saved-views", **params)

    @trustops_tool(title="List Risks")
    def list_risks(limit: int = 100, status: str = "", severity: str = "", owner: str = "") -> JsonObject:
        """List tenant risk register entries (requires server API auth)."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if owner:
            params["owner"] = owner
        return _server_api_request("GET", "/api/v1/risks", **params)

    @trustops_tool(title="List Remediation Exceptions")
    def list_remediation_exceptions(limit: int = 100, active_only: bool = False) -> JsonObject:
        """List control exceptions (compensating controls) with optional active-only filter."""
        params: dict[str, Any] = {"limit": limit}
        if active_only:
            params["active"] = "true"
        return _server_api_request("GET", "/api/v1/remediation/exceptions", **params)

    @trustops_tool(title="Policy Coverage")
    def get_policies_coverage() -> JsonObject:
        """Return control coverage rows for adopted policy documents."""
        return _server_api_request("GET", "/api/v1/policies/coverage")

    @trustops_tool(title="List Remediation Tasks")
    def list_remediation_tasks(
        limit: int = 100, status: str = "", owner: str = "", overdue: bool = False
    ) -> JsonObject:
        """List tenant remediation tasks (requires server API auth)."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if owner:
            params["owner"] = owner
        if overdue:
            params["overdue"] = "true"
        return _server_api_request("GET", "/api/v1/remediation/tasks", **params)

    @trustops_tool(title="Create Remediation Task")
    def create_remediation_task(
        title: str,
        description: str = "",
        control_id: str = "",
        violation_id: str = "",
        owner: str = "",
        priority: str = "medium",
        due_at: str = "",
    ) -> JsonObject:
        """Create a remediation task to close a control or violation gap."""
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "owner": owner,
            "priority": priority,
        }
        if control_id:
            payload["control_id"] = control_id
        if violation_id:
            payload["violation_id"] = violation_id
        if due_at:
            payload["due_at"] = due_at
        return _server_api_request("POST", "/api/v1/remediation/tasks", payload)

    @trustops_tool(title="Create Evidence Request")
    def create_evidence_request(
        control_id: str,
        requested_from: str = "",
        note: str = "",
        due_at: str = "",
    ) -> JsonObject:
        """Request fresh evidence from a control owner."""
        payload: dict[str, Any] = {
            "control_id": control_id,
            "requested_from": requested_from,
            "note": note,
        }
        if due_at:
            payload["due_at"] = due_at
        return _server_api_request("POST", "/api/v1/remediation/evidence-requests", payload)

    @trustops_tool(title="SPRS Score")
    def get_sprs_score() -> JsonObject:
        """Return CMMC Level 2 SPRS score from failing NIST SP 800-171 Rev 2 practices."""
        return _server_api_request("GET", "/api/v1/gov-compliance/sprs")

    @trustops_tool(title="List POA&M Items")
    def list_poam_items(framework_id: str = "cmmc-2-level2", status: str = "", limit: int = 100) -> JsonObject:
        """List Plan of Action & Milestones rows for gov/defense programs."""
        params: dict[str, Any] = {"limit": limit, "framework_id": framework_id}
        if status:
            params["status"] = status
        return _server_api_request("GET", "/api/v1/gov-compliance/poam", **params)

    @trustops_tool(title="Sync POA&M From Posture")
    def sync_poam_from_posture() -> JsonObject:
        """Auto-create POA&M rows from failing CMMC control tests and refresh SPRS."""
        return _server_api_request("POST", "/api/v1/gov-compliance/poam/sync", {})

    @trustops_tool(title="Framework Drill-Down")
    def get_framework_detail(framework_id: str) -> JsonObject:
        """Return control → rule → evidence → datasource detail for one framework."""
        from security_lakehouse.framework_detail import build_framework_detail

        detail = build_framework_detail(framework_id, lake)
        if detail is None:
            raise ValueError(f"unknown framework_id {framework_id!r}")
        return detail

    # ------------------------------------------------------------------
    # Write tools — lake-backed actions an agent can take, not just read.
    #
    # Each of these mutates the lake directory (gold zone) only: writing a
    # snapshot, persisting a workflow, or executing one. None of them touch
    # the application-state DB or require tenant auth, so they are safe over
    # the local stdio transport. DB-backed writes (tasks, POA&M, evidence requests)
    # use authenticated server API tools (TRUSTOPS_API_URL + TRUSTOPS_API_KEY).
    # ------------------------------------------------------------------

    @trustops_tool()
    def create_snapshot(reason: str = "mcp_request") -> JsonObject:
        """Write a point-in-time assessment snapshot to the gold zone.

        Captures the current posture, controls, violations, and evidence
        rollups as an immutable record (for audit trails / just-in-time
        review). Returns the snapshot file path and the recorded reason.

        This is a WRITE: it appends a new snapshot file to the lake.
        """
        status, body = api_v1.handle_post("/api/v1/snapshots", {"reason": reason}, lake)
        if status != HTTPStatus.CREATED:
            errors = body.get("errors") or [{"detail": "snapshot failed"}]
            raise ValueError(errors[0].get("detail", "snapshot failed"))
        return body["data"]

    @trustops_tool()
    def list_workflows() -> list[JsonObject]:
        """List saved automation workflows (latest version per workflow, newest first).

        Each row carries the workflow id, name, description, version, and its
        node/edge graph — the automations an agent can run via ``run_workflow``.
        """
        return workflows.list_workflows(lake)

    @trustops_tool()
    def get_workflow(workflow_id: str) -> JsonObject:
        """Fetch a single saved workflow (latest version) by its id.

        Returns the full record including its node/edge graph, or raises if no
        workflow with that id exists.
        """
        workflow = workflows.get_workflow(lake, workflow_id)
        if workflow is None:
            raise ValueError(f"unknown workflow_id {workflow_id!r}")
        return workflow

    @trustops_tool(title="List Workflow Actions")
    def list_workflow_actions() -> list[JsonObject]:
        """List the available workflow action node types (the automation building blocks).

        Returns each node type with its kind, label, description, and input/output
        schemas — so an agent can discover what steps a workflow can be built from
        before saving or running one.
        """
        return workflows.action_catalog()

    @trustops_tool()
    def run_workflow(workflow_id: str) -> JsonObject:
        """Execute a saved workflow end-to-end and return the run result.

        Runs every node in topological order against the lake, substituting
        ``{{nodeId.output.field}}`` references and honoring conditional edges,
        then persists the run to the gold zone. Returns the run record with a
        per-node ``node_results`` list and an overall ``result`` ("ok"/"error").

        WARNING: this EXECUTES the workflow. Action nodes can have side effects,
        including assigning owners and sending allowlisted outbound webhooks
        (network egress). Only run workflows you intend to fire.
        """
        return workflows.run_workflow(lake, workflow_id=workflow_id, actor="api")

    return mcp


def main() -> None:
    """Run the MCP server over stdio (FastMCP default transport)."""
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
