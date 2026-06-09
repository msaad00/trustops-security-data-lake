"""Versioned API contract tests for headless humans and agents."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

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
            ("/api/v1/posture/current", "posture.current"),
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
