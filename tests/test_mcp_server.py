"""Agent-native MCP server contract tests.

These exercise the FastMCP read tools directly against a seeded lake (no live
stdio client needed). The whole module is guarded behind ``importorskip("mcp")``
so the rest of the suite passes without the optional ``mcp`` dependency.

The async FastMCP coroutines are driven via ``anyio.run`` so the tests need no
pytest-asyncio plugin or extra configuration (``anyio`` ships with the MCP SDK).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("mcp")

import anyio  # noqa: E402

from security_lakehouse import mcp_server  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402

EXPECTED_TOOLS = {
    "get_posture",
    "posture_as_of",
    "list_controls",
    "list_control_tests",
    "list_evidence",
    "list_assets",
    "list_violations",
    "list_snapshots",
    "list_audit_log",
    "list_frameworks",
    "get_ingestion_status",
    "run_lake_eval",
    "run_scheduler_tick",
    "sync_connector",
    "list_connector_runs",
    "get_framework_detail",
    "describe_api",
    "list_agent_runs",
    "create_agent_run",
    "get_agent_run",
    "approve_agent_decision",
    "get_audit_readiness",
    "get_evidence_freshness_summary",
    "escalate_stale_evidence",
    "get_insights_timeseries",
    "get_insights_remediation",
    "get_insights_framework_trends",
    "get_insights_sla_heatmap",
    "list_vendor_assessments",
    "list_policies",
    "list_policy_templates",
    "list_access_reviews",
    "get_access_reviews_coverage",
    "list_evidence_requests",
    "list_trust_shares",
    "get_policy_attestation_summary",
    "list_tags",
    "list_tag_entities",
    "list_saved_views",
    "list_risks",
    "list_remediation_exceptions",
    "get_policies_coverage",
    "list_remediation_tasks",
    "create_remediation_task",
    "create_evidence_request",
    "get_sprs_score",
    "list_poam_items",
    "sync_poam_from_posture",
}


def _seeded_server(tmp_path: Path):
    lake = tmp_path / "lake"
    lake.mkdir(parents=True, exist_ok=True)
    _seed_lake(lake)
    return mcp_server.build_server(lake)


async def _call_async(server, name, arguments):
    result = await server.call_tool(name, arguments)
    # FastMCP returns (content_blocks, structured_result) for newer SDKs and a
    # single value for older ones; normalize to the structured payload.
    structured = result[1] if isinstance(result, tuple) else result
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    return structured


def call_tool(server, name: str, **arguments):
    """Synchronously invoke a registered FastMCP tool, returning its result."""
    return anyio.run(_call_async, server, name, arguments)


def tool_names(server) -> set[str]:
    tools = anyio.run(server.list_tools)
    return {tool.name for tool in tools}


def test_mcp_server_branding(tmp_path: Path) -> None:
    server = _seeded_server(tmp_path)
    assert server.icons
    assert len(server.icons) >= 1
    tools = anyio.run(server.list_tools)
    assert tools
    assert all(getattr(tool, "icons", None) for tool in tools)
    assert all(getattr(tool, "title", None) for tool in tools)


def test_resolve_lake_dir_defaults(monkeypatch):
    monkeypatch.delenv("TRUSTOPS_LAKE", raising=False)
    assert mcp_server.resolve_lake_dir() == Path("./lake").expanduser().resolve()
    monkeypatch.setenv("TRUSTOPS_LAKE", "/tmp/some-lake")
    assert mcp_server.resolve_lake_dir() == Path("/tmp/some-lake").resolve()


def test_resolve_api_base_url(monkeypatch):
    monkeypatch.delenv("TRUSTOPS_API_URL", raising=False)
    with pytest.raises(ValueError):
        mcp_server.resolve_api_base_url()
    monkeypatch.setenv("TRUSTOPS_API_URL", "file:///tmp/lake")
    with pytest.raises(ValueError):
        mcp_server.resolve_api_base_url()
    monkeypatch.setenv("TRUSTOPS_API_URL", "https://trustops.example.test/")
    assert mcp_server.resolve_api_base_url() == "https://trustops.example.test"


def test_expected_tools_registered(tmp_path):
    server = _seeded_server(tmp_path)
    assert tool_names(server) >= EXPECTED_TOOLS


def test_get_posture_has_score(tmp_path):
    server = _seeded_server(tmp_path)
    posture = call_tool(server, "get_posture")
    assert "posture" in posture
    assert isinstance(posture["posture"]["score"], (int, float))


def test_get_ingestion_status_includes_scale(tmp_path):
    server = _seeded_server(tmp_path)
    status = call_tool(server, "get_ingestion_status")
    assert "scale" in status
    assert status["scale"]["mode"]


def test_posture_as_of_after_snapshot(tmp_path):
    server = _seeded_server(tmp_path)
    call_tool(server, "create_snapshot", reason="mcp-as-of")
    result = call_tool(server, "posture_as_of", as_of="2030-01-01")
    assert result["found"] is True
    assert result["assessment_hash"]


def test_list_controls_returns_seeded_ids(tmp_path):
    server = _seeded_server(tmp_path)
    controls = call_tool(server, "list_controls")
    ids = {row["control_id"] for row in controls}
    assert {"SOC2-CC6.1", "NIST-AI-RMF-MAP-1.5"} <= ids


def test_list_control_tests_shapes(tmp_path):
    server = _seeded_server(tmp_path)
    tests = call_tool(server, "list_control_tests")
    assert {row["test_id"] for row in tests} == {"test-soc2", "test-ai"}


def test_list_evidence_limit(tmp_path):
    server = _seeded_server(tmp_path)
    evidence = call_tool(server, "list_evidence", limit=1)
    assert len(evidence) == 1


def test_list_assets_returns_rows(tmp_path):
    server = _seeded_server(tmp_path)
    assets = call_tool(server, "list_assets")
    assert {row["asset_id"] for row in assets} == {"aws:iam:role/admin", "model:reranker"}


def test_list_violations_open_only(tmp_path):
    server = _seeded_server(tmp_path)
    violations = call_tool(server, "list_violations")
    assert violations
    assert all(row["state"] == "open" for row in violations)
    assert any(row["control_id"] == "SOC2-CC6.1" for row in violations)


def test_list_snapshots_empty_without_snapshots(tmp_path):
    server = _seeded_server(tmp_path)
    assert call_tool(server, "list_snapshots") == []


def test_list_connector_runs_reads_lake(tmp_path):
    server = _seeded_server(tmp_path)
    runs = call_tool(server, "list_connector_runs", connector_id="aws-posture", limit=10)
    assert isinstance(runs, list)


def test_list_frameworks_non_empty(tmp_path):
    server = _seeded_server(tmp_path)
    frameworks = call_tool(server, "list_frameworks")
    assert isinstance(frameworks, list)
    assert frameworks


def test_describe_api_lists_resources(tmp_path):
    server = _seeded_server(tmp_path)
    catalog = call_tool(server, "describe_api")
    paths = {row["path"] for row in catalog}
    assert "/api/v1/posture/current" in paths
    assert "/api/v1/controls" in paths
    assert "/api/v1/audit-log" in paths
    assert "/api/v1/platform/audit-readiness" in paths
    assert "/api/v1/insights/remediation" in paths
    assert "/api/v1/vendor-assessments" in paths


def test_list_audit_log_returns_entries(tmp_path):
    server = _seeded_server(tmp_path)
    entries = call_tool(server, "list_audit_log", limit=10)
    assert isinstance(entries, list)
    if entries:
        assert "event_id" in entries[0]
        assert "occurred_at" in entries[0]


def test_get_audit_readiness_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/platform/audit-readiness"
        return {"data": {"audit_score": 88, "state": "audit_ready"}, "meta": {}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_audit_readiness")
    assert result["data"]["audit_score"] == 88


def test_get_framework_detail_soc2(tmp_path):
    server = _seeded_server(tmp_path)
    detail = call_tool(server, "get_framework_detail", framework_id="soc2")
    assert detail["framework"]["framework_id"] == "soc2"
    assert detail["summary"]["control_count"] >= 1
    assert detail["controls"]


def test_get_insights_remediation_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/insights/remediation"
        return {"data": {"open": 3, "overdue": 1}, "meta": {}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_insights_remediation")
    assert result["data"]["open"] == 3


def test_get_insights_framework_trends_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/insights/framework-trends"
        assert params.get("limit") == "30"
        return {"data": {"frameworks": ["soc2"], "points": []}, "meta": {}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_insights_framework_trends", limit=30)
    assert result["data"]["frameworks"] == ["soc2"]


def test_get_insights_sla_heatmap_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/insights/sla-heatmap"
        return {"data": {"columns": [], "rows": []}, "meta": {}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "get_insights_sla_heatmap")


def test_list_vendor_assessments_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "params": params})
        return {"data": [], "meta": {"count": 0}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "list_vendor_assessments", status="completed", limit=25)
    assert calls[0]["path"] == "/api/v1/vendor-assessments"
    assert calls[0]["params"]["status"] == "completed"
    assert calls[0]["params"]["limit"] == 25


def test_list_policy_templates_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/policy-templates"
        return {"data": [{"template_id": "acceptable-use"}], "meta": {"count": 1}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "list_policy_templates")
    assert result["data"][0]["template_id"] == "acceptable-use"


def test_list_access_reviews_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "params": params})
        return {"data": [], "meta": {"count": 0}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "list_access_reviews", status="active", limit=10)
    assert calls[0]["path"] == "/api/v1/access-reviews"
    assert calls[0]["params"]["status"] == "active"
    assert calls[0]["params"]["limit"] == 10


def test_get_access_reviews_coverage_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/access-reviews/coverage"
        return {"data": [{"control_id": "CC6.1"}], "meta": {"count": 1}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_access_reviews_coverage")
    assert result["meta"]["count"] == 1


def test_list_risks_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "params": params})
        return {"data": [], "meta": {"count": 0}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "list_risks", status="open", severity="high", owner="alice", limit=50)
    assert calls[0]["path"] == "/api/v1/risks"
    assert calls[0]["params"]["status"] == "open"
    assert calls[0]["params"]["severity"] == "high"
    assert calls[0]["params"]["owner"] == "alice"
    assert calls[0]["params"]["limit"] == 50


def test_list_remediation_exceptions_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "params": params})
        return {"data": [], "meta": {"count": 0}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "list_remediation_exceptions", active_only=True, limit=25)
    assert calls[0]["path"] == "/api/v1/remediation/exceptions"
    assert calls[0]["params"]["active"] == "true"
    assert calls[0]["params"]["limit"] == 25


def test_get_policies_coverage_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/policies/coverage"
        return {"data": [{"control_id": "SOC2-CC6.1"}], "meta": {"count": 1}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_policies_coverage")
    assert result["data"][0]["control_id"] == "SOC2-CC6.1"


def test_list_evidence_requests_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "params": params})
        return {"data": [], "meta": {"count": 0}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    call_tool(server, "list_evidence_requests", status="open", limit=5)
    assert calls[0]["path"] == "/api/v1/remediation/evidence-requests"
    assert calls[0]["params"]["status"] == "open"


def test_list_trust_shares_reads_lake(tmp_path):
    server = _seeded_server(tmp_path)
    result = call_tool(server, "list_trust_shares")
    assert isinstance(result, list)


def test_get_policy_attestation_summary_calls_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)

    def fake_request(method, path, body=None, **params):
        assert method == "GET"
        assert path == "/api/v1/policies/attestation-summary"
        return {"data": {"published": 2, "unattested": 1}, "meta": {}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)
    result = call_tool(server, "get_policy_attestation_summary")
    assert result["data"]["unattested"] == 1


def test_mcp_agent_run_tools_call_authenticated_api(tmp_path, monkeypatch):
    server = _seeded_server(tmp_path)
    calls = []

    def fake_request(method, path, body=None, **params):
        calls.append({"method": method, "path": path, "body": body, "params": params})
        return {"data": {"ok": True}, "meta": {"resource": "agent-runs"}, "errors": []}

    monkeypatch.setattr(mcp_server, "_server_api_request", fake_request)

    listed = call_tool(server, "list_agent_runs", limit=7, harness="posture_review", status="completed")
    assert listed["data"]["ok"] is True
    created = call_tool(
        server,
        "create_agent_run",
        harness="soc_triage",
        objective="triage current alerts",
        role="read_only",
        idempotency_key="mcp-run-1",
        orchestrator="sequential",
        use_model=False,
        max_fact_items=5,
    )
    assert created["meta"]["resource"] == "agent-runs"
    fetched = call_tool(server, "get_agent_run", run_id="run/id with space")
    approved = call_tool(server, "approve_agent_decision", run_id="run/id with space", decision_index=2, note="ok")
    assert fetched["data"]["ok"] is True
    assert approved["data"]["ok"] is True

    assert calls[0] == {
        "method": "GET",
        "path": "/api/v1/agent-runs",
        "body": None,
        "params": {"limit": 7, "harness": "posture_review", "status": "completed"},
    }
    assert calls[1]["method"] == "POST"
    assert calls[1]["path"] == "/api/v1/agent-runs"
    assert calls[1]["body"] == {
        "harness": "soc_triage",
        "objective": "triage current alerts",
        "role": "read_only",
        "idempotency_key": "mcp-run-1",
        "orchestrator": "sequential",
        "use_model": False,
        "max_fact_items": 5,
    }
    assert calls[2]["path"] == "/api/v1/agent-runs/run%2Fid%20with%20space"
    assert calls[3]["path"] == "/api/v1/agent-runs/run%2Fid%20with%20space/decisions/2/approve"
    assert calls[3]["body"] == {"note": "ok"}
