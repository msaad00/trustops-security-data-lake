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

import os
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
