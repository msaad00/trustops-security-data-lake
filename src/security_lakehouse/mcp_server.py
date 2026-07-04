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
    mcp = FastMCP("trustops")

    @mcp.tool()
    def get_posture() -> JsonObject:
        """Return the current compliance posture summary.

        Includes the overall score and state, per-framework scores, open
        violations, top risk assets, and evidence-freshness rollups — the
        continuously refreshed answer to "are we compliant right now?".
        """
        return _get("/api/v1/posture/current", lake)

    @mcp.tool()
    def posture_as_of(as_of: str) -> JsonObject:
        """Return the compliance posture as of a point in time.

        Selects the newest snapshot whose ``evaluated_at`` is at or before
        ``as_of`` (an ISO date or datetime, e.g. ``2026-04-15``). Use this to
        answer "were we compliant on date X?" against immutable snapshots
        rather than the live posture.
        """
        return _get("/api/v1/posture/as-of", lake, as_of=as_of)

    @mcp.tool()
    def list_controls(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List control posture rows (one per framework control, with pass/fail status)."""
        return _get("/api/v1/controls", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
    def list_control_tests(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List control-test results that produced the control posture."""
        return _get("/api/v1/control-tests", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
    def list_evidence(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List normalized evidence events backing the assessment.

        Use ``limit`` to cap the number of rows returned (1-1000, default 100).
        """
        return _get("/api/v1/evidence", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
    def list_assets(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List assets with their computed risk scores."""
        return _get("/api/v1/assets", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
    def list_violations(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List open control/asset violations requiring owner action, highest severity first."""
        return _get("/api/v1/violations", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
    def list_snapshots(limit: int = 100, offset: int = 0) -> list[JsonObject]:
        """List point-in-time assessment snapshots written to the gold zone (for audit/JIT review)."""
        return _get("/api/v1/snapshots", lake, limit=str(limit), offset=str(offset))

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    def list_agent_runs(limit: int = 100, harness: str = "", status: str = "") -> JsonObject:
        """List persisted human/headless agent harness runs through the authenticated API.

        Requires ``TRUSTOPS_API_URL`` and ``TRUSTOPS_API_KEY``. Returns the full
        v1 envelope so the caller can inspect `meta.count`, filters, and errors.
        """
        return _server_api_request("GET", "/api/v1/agent-runs", limit=limit, harness=harness, status=status)

    @mcp.tool()
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

    @mcp.tool()
    def get_agent_run(run_id: str) -> JsonObject:
        """Inspect one persisted agent harness run through the authenticated API."""
        return _server_api_request("GET", f"/api/v1/agent-runs/{urllib.parse.quote(run_id, safe='')}")

    @mcp.tool()
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

    @mcp.tool()
    def get_audit_readiness() -> JsonObject:
        """Return audit score, blocking gaps, and workflow coverage checklist.

        Requires ``TRUSTOPS_API_URL`` and ``TRUSTOPS_API_KEY`` — tenant-scoped
        fields (evidence requests, access reviews, trust shares) live in the app DB.
        """
        return _server_api_request("GET", "/api/v1/platform/audit-readiness")

    # ------------------------------------------------------------------
    # Write tools — lake-backed actions an agent can take, not just read.
    #
    # Each of these mutates the lake directory (gold zone) only: writing a
    # snapshot, persisting a workflow, or executing one. None of them touch
    # the application-state DB or require tenant auth, so they are safe over
    # the local stdio transport. DB-backed writes (risks, tasks, assignments)
    # are intentionally NOT exposed here — they belong behind a shared
    # services layer and an authenticated MCP transport.
    # ------------------------------------------------------------------

    @mcp.tool()
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

    @mcp.tool()
    def list_workflows() -> list[JsonObject]:
        """List saved automation workflows (latest version per workflow, newest first).

        Each row carries the workflow id, name, description, version, and its
        node/edge graph — the automations an agent can run via ``run_workflow``.
        """
        return workflows.list_workflows(lake)

    @mcp.tool()
    def get_workflow(workflow_id: str) -> JsonObject:
        """Fetch a single saved workflow (latest version) by its id.

        Returns the full record including its node/edge graph, or raises if no
        workflow with that id exists.
        """
        workflow = workflows.get_workflow(lake, workflow_id)
        if workflow is None:
            raise ValueError(f"unknown workflow_id {workflow_id!r}")
        return workflow

    @mcp.tool()
    def list_workflow_actions() -> list[JsonObject]:
        """List the available workflow action node types (the automation building blocks).

        Returns each node type with its kind, label, description, and input/output
        schemas — so an agent can discover what steps a workflow can be built from
        before saving or running one.
        """
        return workflows.action_catalog()

    @mcp.tool()
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
