"""Versioned API contract tests for headless humans and agents."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from security_lakehouse import api_v1
from security_lakehouse.connector_state import append_config_event, append_run_event
from security_lakehouse.server import _Handler


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _seed_lake(lake: Path) -> None:
    (lake / "console.html").write_bytes(b"<!doctype html>")
    _write_jsonl(
        lake / "gold" / "control_posture.jsonl",
        [
            {
                "control_id": "SOC2-CC6.1",
                "framework": "SOC 2",
                "owner": "security-platform",
                "risk_score": 80,
                "status": "fail",
                "title": "Access evidence is current",
            },
            {
                "control_id": "NIST-AI-RMF-MAP-1.5",
                "framework": "NIST AI RMF",
                "owner": "ai-security",
                "risk_score": 20,
                "status": "pass",
                "title": "AI inventory is maintained",
            },
        ],
    )
    _write_jsonl(
        lake / "gold" / "control_tests.jsonl",
        [
            {
                "test_id": "test-soc2",
                "control_id": "SOC2-CC6.1",
                "framework": "SOC 2",
                "owner": "security-platform",
                "result": "fail",
                "confidence_score": 71,
            },
            {
                "test_id": "test-ai",
                "control_id": "NIST-AI-RMF-MAP-1.5",
                "framework": "NIST AI RMF",
                "owner": "ai-security",
                "result": "pass",
                "confidence_score": 96,
            },
        ],
    )
    _write_jsonl(
        lake / "silver" / "normalized_events.jsonl",
        [
            {
                "event_id": "evt-001",
                "event_time": "2026-05-20T13:01:00Z",
                "event_type": "identity.access_review",
                "control_ids": ["SOC2-CC6.1"],
                "asset_id": "aws:iam:role/admin",
                "asset_owner": "security-platform",
                "asset_type": "iam_role",
                "environment": "prod",
                "source": "okta",
                "status": "open",
                "severity": "high",
                "severity_score": 80,
                "evidence_ref": "s3://evidence/evt-001.json",
                "raw_sha256": "abc",
            },
            {
                "event_id": "evt-002",
                "event_time": "2026-05-20T14:00:00Z",
                "event_type": "model.inventory",
                "control_ids": ["NIST-AI-RMF-MAP-1.5"],
                "asset_id": "model:reranker",
                "asset_owner": "ai-security",
                "asset_type": "model",
                "environment": "prod",
                "source": "model-registry",
                "status": "resolved",
                "severity": "low",
                "severity_score": 10,
                "evidence_ref": "s3://evidence/evt-002.json",
                "raw_sha256": "def",
            },
        ],
    )
    _write_jsonl(
        lake / "gold" / "evidence_freshness.jsonl",
        [
            {
                "event_id": "evt-001",
                "evidence_id": "evidence-001",
                "evidence_ref": "s3://evidence/evt-001.json",
                "source": "okta",
                "connector_id": "okta",
                "event_type": "identity.access_review",
                "asset_id": "aws:iam:role/admin",
                "control_ids": ["SOC2-CC6.1"],
                "evidence_collected_at": "2026-05-20T13:01:00Z",
                "evaluated_at": "2026-05-22T13:01:00Z",
                "freshness_slo_minutes": 1440,
                "status": "expired",
                "score": 0,
                "age_minutes": 2880,
                "expires_at": "2026-05-21T13:01:00Z",
                "reason": "evidence is outside the freshness SLO",
                "next_action": "request updated access review evidence",
            },
            {
                "event_id": "evt-002",
                "evidence_id": "evidence-002",
                "evidence_ref": "s3://evidence/evt-002.json",
                "source": "model-registry",
                "connector_id": "model-registry",
                "event_type": "model.inventory",
                "asset_id": "model:reranker",
                "control_ids": ["NIST-AI-RMF-MAP-1.5"],
                "evidence_collected_at": "2026-05-20T14:00:00Z",
                "evaluated_at": "2026-05-20T15:00:00Z",
                "freshness_slo_minutes": 1440,
                "status": "fresh",
                "score": 100,
                "age_minutes": 60,
                "expires_at": "2026-05-21T14:00:00Z",
                "reason": "evidence is within the freshness SLO",
                "next_action": "no action required",
            },
        ],
    )
    _write_jsonl(
        lake / "gold" / "asset_risk.jsonl",
        [
            {
                "asset_id": "aws:iam:role/admin",
                "asset_owner": "security-platform",
                "asset_type": "iam_role",
                "environment": "prod",
                "risk_score": 80,
            },
            {
                "asset_id": "model:reranker",
                "asset_owner": "ai-security",
                "asset_type": "model",
                "environment": "prod",
                "risk_score": 10,
            },
        ],
    )


def _spin(lake: Path) -> ThreadingHTTPServer:
    _seed_lake(lake)

    class Handler(_Handler):
        lake_dir = lake
        dashboard_path = lake / "console.html"
        web_dist = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _request(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    host, port = server.server_address
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"http://{host}:{port}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def test_v1_collections_are_enveloped_and_paginated(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/controls?sort=-risk_score&limit=1&offset=0")
        assert status == HTTPStatus.OK
        assert set(body) == {"data", "meta", "errors"}
        assert body["errors"] == []
        assert body["meta"]["api_version"] == "v1"
        assert body["meta"]["resource"] == "controls"
        assert body["meta"]["count"] == 2
        assert body["meta"]["returned"] == 1
        assert body["data"][0]["control_id"] == "SOC2-CC6.1"
    finally:
        server.shutdown()


def test_v1_all_read_routes_use_envelope(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        for path, resource in [
            ("/api/v1/healthz", "healthz"),
            ("/api/v1/ingestion/status", "ingestion.status"),
            ("/api/v1/posture/current", "posture.current"),
            ("/api/v1/connectors", "connectors"),
            ("/api/v1/controls", "controls"),
            ("/api/v1/control-tests", "control-tests"),
            ("/api/v1/evidence", "evidence"),
            ("/api/v1/evidence/freshness", "evidence.freshness"),
            ("/api/v1/assets", "assets"),
            ("/api/v1/violations", "violations"),
            ("/api/v1/snapshots", "snapshots"),
        ]:
            status, body = _request(server, "GET", path)
            assert status == HTTPStatus.OK
            assert set(body) == {"data", "meta", "errors"}
            assert body["meta"]["api_version"] == "v1"
            assert body["meta"]["resource"] == resource
            assert body["errors"] == []
    finally:
        server.shutdown()


def test_v1_crosswalk_and_mappings_match_their_pre_v1_payloads(tmp_path: Path) -> None:
    """The v1 routes must serve the same bytes as the routes they replace.

    These five moved to /v1 so api_legacy can eventually be retired. If a
    payload drifts, the console silently renders different data depending on
    which route it happens to call, so parity is the property worth pinning.
    """
    server = _spin(tmp_path)
    try:
        for legacy, v1 in [
            ("/api/crosswalk", "/api/v1/crosswalk"),
            ("/api/crosswalk/reviewed", "/api/v1/crosswalk/reviewed"),
            ("/api/mappings/equivalence", "/api/v1/mappings/equivalence"),
            ("/api/repo-graph", "/api/v1/repo-graph"),
        ]:
            legacy_status, legacy_body = _request(server, "GET", legacy)
            v1_status, v1_body = _request(server, "GET", v1)
            assert legacy_status == HTTPStatus.OK
            assert v1_status == HTTPStatus.OK
            assert set(v1_body) == {"data", "meta", "errors"}
            assert v1_body["data"] == legacy_body, f"{v1} drifted from {legacy}"

        # /mappings is a collection, so v1 paginates where the pre-v1 route
        # returned everything. The rows must still agree page for page.
        _, legacy_body = _request(server, "GET", "/api/mappings")
        _, v1_body = _request(server, "GET", "/api/v1/mappings?limit=500&offset=0")
        assert v1_body["meta"]["count"] == legacy_body["count"]
        assert v1_body["data"] == legacy_body["mappings"][: len(v1_body["data"])]
    finally:
        server.shutdown()


def test_v1_resource_catalog_advertises_connector_actions(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1")
        assert status == HTTPStatus.OK
        by_path = {item["path"]: item for item in body["data"]["resources"]}
        assert by_path["/api/v1/ingestion/status"]["resource"] == "ingestion.status"
        assert by_path["/api/v1/connectors"]["methods"] == ["GET"]
        assert by_path["/api/v1/connectors/{connector_id}/runs"]["methods"] == ["GET"]
        assert by_path["/api/v1/connectors/{connector_id}/discover"]["scopes"] == ["connector_manage"]
        assert by_path["/api/v1/connectors/{connector_id}/probe"]["scopes"] == ["connector_manage"]
        assert by_path["/api/v1/connectors/{connector_id}/configure"]["scopes"] == ["connector_manage"]
        assert by_path["/api/v1/connectors/{connector_id}/sync"]["methods"] == ["POST"]
        assert by_path["/api/v1/connectors/{connector_id}/sync"]["scopes"] == ["connector_manage"]
    finally:
        server.shutdown()


def test_v1_connector_sync_failure_is_generic_and_does_not_leak(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        # Syncing a connector that is not enabled fails; the endpoint must return
        # a generic error envelope with no exception detail crossing the boundary.
        status, body = _request(server, "POST", "/api/v1/connectors/aws-posture/sync", {})
        assert status == HTTPStatus.BAD_REQUEST
        assert body["errors"][0]["code"] == "sync_failed"
        assert "see the connector runs" in body["errors"][0]["detail"]
        assert "Traceback" not in json.dumps(body)
    finally:
        server.shutdown()


def test_v1_ingestion_status_summarizes_live_runs_and_proof_pack(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        append_config_event(
            tmp_path,
            connector_id="snowflake-evidence-lake",
            state="enabled",
            actor="test",
            credentials={"account": "acct", "user": "TRUSTOPS_INGEST_SVC", "private_key_ref": "SNOWFLAKE_KEY"},
            options={
                "warehouse": "TRUSTOPS_READ_WH",
                "database": "TRUSTOPS_SECURITY_LAKE",
                "schema": "EVIDENCE",
                "audit_events": "TRUSTOPS_AUDIT_EVENTS",
                "control_posture": "TRUSTOPS_CONTROL_POSTURE",
                "asset_risk": "TRUSTOPS_ASSET_RISK",
                "evidence_bundles": "TRUSTOPS_EVIDENCE_BUNDLES",
            },
        )
        append_run_event(
            tmp_path,
            connector_id="snowflake-evidence-lake",
            kind="sync",
            result="ok",
            actor="scheduler",
            evidence_count=2,
            duration_ms=42,
        )
        (tmp_path / "gold" / "evidence_integrity.json").write_text(
            json.dumps({"ok": True, "evidence_count": 2, "unique_event_ids": 2, "duplicate_event_ids": 0}),
            encoding="utf-8",
        )
        (tmp_path / "gold" / "current_posture.json").write_text(
            json.dumps({"posture": {"score": 75, "state": "attention_required", "open_violation_count": 1}}),
            encoding="utf-8",
        )
        report_dir = tmp_path / "gold" / "scenario_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "live-cloud-posture.json").write_text(
            json.dumps(
                {
                    "scenario": "live-cloud-posture",
                    "summary": {
                        "ok": True,
                        "proof_state": "needs_review",
                        "evidence_count": 2,
                        "sources": ["okta", "model-registry"],
                        "open_violations": 1,
                        "recommended_actions": [
                            {
                                "priority": "p1",
                                "action": "triage_open_findings",
                                "reason": "1 open violation needs an owner.",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        (report_dir / "live-cloud-posture.md").write_text("# Proof\n", encoding="utf-8")

        status, body = _request(server, "GET", "/api/v1/ingestion/status")
        assert status == HTTPStatus.OK
        assert body["meta"]["resource"] == "ingestion.status"
        data = body["data"]
        assert data["state"] in {"active", "attention_required"}
        assert data["summary"]["enabled_connectors"] == 1
        assert data["summary"]["evidence_count"] == 2
        assert data["sources"] == [
            {"source": "model-registry", "evidence_count": 1},
            {"source": "okta", "evidence_count": 1},
        ]
        snowflake = next(row for row in data["connectors"] if row["connector_id"] == "snowflake-evidence-lake")
        assert snowflake["latest_sync"]["result"] == "ok"
        assert data["integrity"]["ok"] is True
        assert data["proof"]["proof_pack_exists"] is True
        assert data["proof"]["proof_state"] == "needs_review"
        assert any(action["action"] == "triage_open_findings" for action in data["recommended_actions"])
    finally:
        server.shutdown()


def test_v1_connector_discovery_is_enveloped_and_history_safe(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/aws-posture/discover",
            body={
                "actor": "agent-harness",
                "credentials": {"account_id": "123456789012"},
                "options": {"region": "us-west-2"},
            },
        )
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "connector.discover"
        assert body["data"]["kind"] == "discover"
        assert body["data"]["result"] == "ok"
        assert body["data"]["metadata"]["selection_mode"] == "account"
        assert body["data"]["metadata"]["selectors"][0]["name"] == "123456789012"

        status, body = _request(server, "GET", "/api/v1/connectors/aws-posture/runs")
        assert status == HTTPStatus.OK
        assert body["meta"]["resource"] == "connector.runs"
        assert body["meta"]["connector_id"] == "aws-posture"
        assert body["meta"]["count"] == 1
        assert body["data"][0]["kind"] == "discover"
        assert body["data"][0]["metadata"]["selection_mode"] == "account"
        assert body["data"][0]["metadata"]["selectors"][0]["name"] == "123456789012"
    finally:
        server.shutdown()


def test_v1_connector_configure_requires_matching_ok_probe(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/github-security/configure",
            body={"state": "enabled", "credentials": {"token": "abc"}, "options": {"repo": "x/repo"}},
        )
        assert status == HTTPStatus.BAD_REQUEST
        assert body["meta"]["resource"] == "connector.configure"
        assert "Test connection" in body["errors"][0]["detail"]

        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/github-security/probe",
            body={"credentials": {"token": "abc"}, "options": {"repo": "x/repo"}},
        )
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "connector.probe"
        assert body["data"]["result"] == "ok"
        assert body["data"]["access_fingerprint"]

        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/github-security/configure",
            body={"state": "enabled", "credentials": {"token": "abc"}, "options": {"repo": "x/repo"}},
        )
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "connector.configure"
        assert body["data"]["state"] == "enabled"
        assert body["data"]["credentials"]["token"].startswith("***")
    finally:
        server.shutdown()


def test_v1_aws_connector_enable_reuses_verified_role_after_disable(tmp_path: Path, monkeypatch) -> None:
    def fake_probe_aws_access(*, credentials: dict[str, object], options: dict[str, object]) -> dict[str, object]:
        assert credentials["account_id"] == "123456789012"
        assert credentials["role_arn"] == "arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole"
        assert credentials["external_id"] == "external-demo"
        assert options["region"] == "us-east-1"
        return {"ok": True, "capabilities": ["sts:AssumeRole", "iam:ListUsers"], "principal_count": 4}

    monkeypatch.setattr("security_lakehouse.connector_state.probe_aws_access", fake_probe_aws_access)
    credentials = {
        "account_id": "123456789012",
        "role_arn": "arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole",
        "external_id": "external-demo",
    }
    options = {"region": "us-east-1", "sync_schedule": "every 15m", "eval_schedule": "every 6h"}
    server = _spin(tmp_path)
    try:
        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/aws-posture/probe",
            body={"credentials": credentials, "options": options},
        )
        assert status == HTTPStatus.CREATED
        assert body["data"]["result"] == "ok"
        verified_fingerprint = body["data"]["access_fingerprint"]

        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/aws-posture/configure",
            body={"state": "enabled", "credentials": credentials, "options": options},
        )
        assert status == HTTPStatus.CREATED
        assert body["data"]["state"] == "enabled"

        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/aws-posture/configure",
            body={"state": "disabled", "actor": "console"},
        )
        assert status == HTTPStatus.CREATED
        assert body["data"]["state"] == "disabled"
        assert body["data"]["credentials"]["account_id"] == "123456789012"
        assert body["data"]["credential_fingerprint"] == verified_fingerprint

        status, body = _request(
            server,
            "POST",
            "/api/v1/connectors/aws-posture/configure",
            body={"state": "enabled", "actor": "console"},
        )
        assert status == HTTPStatus.CREATED
        assert body["data"]["state"] == "enabled"
        assert body["data"]["credentials"]["account_id"] == "123456789012"
        assert body["data"]["options"]["region"] == "us-east-1"
        assert body["data"]["credential_fingerprint"] == verified_fingerprint
    finally:
        server.shutdown()


def test_v1_posture_separates_violation_and_test_counts(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/posture/current")
        assert status == HTTPStatus.OK
        posture = body["data"]["posture"]
        assert posture["critical_violation_count"] == 0
        assert posture["high_violation_count"] == 1
        assert posture["failed_control_test_count"] == 1
        assert posture["warning_control_test_count"] == 0
    finally:
        server.shutdown()


def test_v1_filters_list_fields_and_scalar_fields(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/evidence?control_ids=SOC2-CC6.1")
        assert status == HTTPStatus.OK
        assert body["meta"]["count"] == 1
        assert body["data"][0]["event_id"] == "evt-001"

        status, body = _request(server, "GET", "/api/v1/control-tests?result=pass")
        assert status == HTTPStatus.OK
        assert body["meta"]["count"] == 1
        assert body["data"][0]["control_id"] == "NIST-AI-RMF-MAP-1.5"
    finally:
        server.shutdown()


def test_v1_evidence_freshness_lists_stale_evidence_for_agents(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(
            server, "GET", "/api/v1/evidence/freshness?status=stale,expired,missing&sort=-age_minutes"
        )
        assert status == HTTPStatus.OK
        assert body["meta"]["resource"] == "evidence.freshness"
        assert body["meta"]["count"] == 1
        assert body["meta"]["filters"] == {"status": ["stale", "expired", "missing"]}
        assert body["data"][0]["event_id"] == "evt-001"
        assert body["data"][0]["status"] == "expired"
        assert body["data"][0]["next_action"] == "request updated access review evidence"
    finally:
        server.shutdown()


def test_v1_violations_are_filterable_for_agents(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/violations?severity=high&sort=-severity_score")
        assert status == HTTPStatus.OK
        assert body["meta"]["resource"] == "violations"
        assert body["meta"]["count"] == 1
        assert body["data"][0]["violation_id"] == "SOC2-CC6.1:evt-001"
    finally:
        server.shutdown()


def test_v1_snapshot_post_uses_envelope(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "POST", "/api/v1/snapshots", {"reason": "vendor_review"})
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "snapshots"
        assert body["data"]["reason"] == "vendor_review"
        assert Path(body["data"]["snapshot_path"]).is_file()
    finally:
        server.shutdown()


def test_v1_snapshot_post_requires_snapshot_scope() -> None:
    assert api_v1.required_post_scope("/api/v1/snapshots") == "snapshot"


def test_v1_errors_use_contract_envelope(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/controls?limit=0")
        assert status == HTTPStatus.BAD_REQUEST
        assert body["data"] is None
        assert body["errors"][0]["code"] == "bad_request"

        status, body = _request(server, "GET", "/api/v1/not-real")
        assert status == HTTPStatus.NOT_FOUND
        assert body["errors"][0]["code"] == "not_found"
    finally:
        server.shutdown()


def test_v1_ingestion_eval_and_scheduler_tick(tmp_path: Path) -> None:
    import shutil

    from security_lakehouse.pipeline import run_pipeline
    from test_pipeline import RAW

    server = _spin(tmp_path)
    try:
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        shutil.copy(RAW, raw_dir / "connector_events.jsonl")
        run_pipeline(raw_dir / "connector_events.jsonl", tmp_path)
        status, body = _request(server, "POST", "/api/v1/ingestion/eval", {"actor": "test"})
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "ingestion.eval"
        assert body["data"]["result"] == "ok"
        assert body["data"]["mode"] in {"local_full", "local_incremental"}

        status, body = _request(server, "POST", "/api/v1/scheduler/tick", {})
        assert status == HTTPStatus.CREATED
        assert body["meta"]["resource"] == "scheduler.tick"
        assert "fired" in body["data"]

        status, body = _request(server, "GET", "/api/v1/ingestion/status")
        assert status == HTTPStatus.OK
        assert "scale" in body["data"]
        assert body["data"]["scale"]["mode"]
    finally:
        server.shutdown()


def test_v1_ingestion_status_includes_scale(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/v1/ingestion/status")
        assert status == HTTPStatus.OK
        scale = body["data"]["scale"]
        assert "mode" in scale
        assert "eval_schedule" in scale
        assert "warehouse_row_threshold" in scale
        assert "next_eval_at" in scale
        assert "eval_overdue" in scale
        assert "eval_accuracy" in body["data"]
        assert "catalog_coverage" in body["data"]
        assert body["data"]["catalog_coverage"]["total"] >= 1
    finally:
        server.shutdown()
