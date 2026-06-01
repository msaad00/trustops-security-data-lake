"""Connector configuration + probe + framework provenance tests."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from security_lakehouse.connector_state import (
    append_config_event,
    build_catalog_view,
    latest_config,
    latest_run,
    list_runs,
    run_probe,
)
from security_lakehouse.framework_provenance import build_framework_view
from security_lakehouse.server import _Handler

# --- pure-Python connector_state ------------------------------------------------


def test_configure_records_state_and_redacts_credentials(tmp_path: Path) -> None:
    record = append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        credentials={"token": "ghp_supersecret", "username": "alice"},
        options={"org": "acme"},
    )
    assert record["state"] == "enabled"
    # credentials are redacted (token → fingerprint), username left alone
    assert record["credentials"]["token"].startswith("***")
    assert record["credentials"]["username"] == "alice"
    # fingerprint deterministic
    again = append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        credentials={"token": "ghp_supersecret", "username": "alice"},
    )
    assert again["credential_fingerprint"] == record["credential_fingerprint"]


def test_latest_config_returns_most_recent(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="github-security", state="disabled", actor="a")
    append_config_event(tmp_path, connector_id="github-security", state="enabled", actor="a")
    assert latest_config(tmp_path, "github-security")["state"] == "enabled"


def test_probe_requires_enabled_connector(tmp_path: Path) -> None:
    skipped = run_probe(tmp_path, connector_id="github-security")
    assert skipped["result"] == "skipped"
    assert "not enabled" in skipped["error"]
    append_config_event(tmp_path, connector_id="github-security", state="enabled", actor="a")
    ok = run_probe(tmp_path, connector_id="github-security")
    assert ok["result"] == "ok"
    # The probe validates configuration; it does not collect or fabricate a count.
    assert ok["evidence_count"] is None


def test_probe_without_adapter_is_skipped_not_fabricated(tmp_path: Path) -> None:
    # A connector with no collection adapter must report contract-validated only,
    # never a synthetic evidence_count implying live collection.
    append_config_event(tmp_path, connector_id="snowflake-evidence-lake", state="enabled", actor="a")
    rec = run_probe(tmp_path, connector_id="snowflake-evidence-lake")
    assert rec["result"] == "skipped"
    assert rec["evidence_count"] is None
    assert "no collection adapter" in rec["error"]


def test_probe_unknown_connector_returns_error(tmp_path: Path) -> None:
    rec = run_probe(tmp_path, connector_id="not-a-real-connector")
    assert rec["result"] == "error"
    assert "unknown connector_id" in rec["error"]


def test_build_catalog_view_joins_config_and_runs(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="github-security", state="enabled", actor="a")
    run_probe(tmp_path, connector_id="github-security")
    view = build_catalog_view(tmp_path)
    by_id = {c["connector_id"]: c for c in view}
    assert by_id["github-security"]["state"] == "enabled"
    assert by_id["github-security"]["last_probe"]["result"] == "ok"
    # connectors that have not been configured fall back to disabled
    assert by_id["snowflake-evidence-lake"]["state"] == "disabled"


def test_list_runs_returns_newest_first(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="github-security", state="enabled", actor="a")
    a = run_probe(tmp_path, connector_id="github-security")
    b = run_probe(tmp_path, connector_id="github-security")
    rows = list_runs(tmp_path, "github-security")
    assert len(rows) == 2
    assert rows[0]["occurred_at"] >= rows[1]["occurred_at"]
    assert latest_run(tmp_path, "github-security", kind="probe")["occurred_at"] == max(
        a["occurred_at"], b["occurred_at"]
    )


# --- framework provenance -------------------------------------------------------


def test_framework_view_computes_freshness_state() -> None:
    view = build_framework_view()
    assert len(view) >= 1
    for framework in view:
        # Freshness must be one of the known states; current registry has
        # pulled_at=null so every framework is "never_pulled".
        assert framework["freshness_state"] in {"fresh", "stale", "expired", "never_pulled"}
        # Each framework reports its control count + mapping coverage.
        assert "control_count" in framework
        assert "mapping_coverage_pct" in framework


def test_framework_view_marks_pulled_recently_as_fresh(tmp_path: Path) -> None:
    registry = {
        "frameworks": [
            {
                "framework_id": "demo",
                "name": "Demo",
                "version": "1.0",
                "official_source_url": "https://example.com/demo",
                "official_source_name": "Demo Source",
                "implementation_status": "implemented",
                "effective_date": "2026-01-01",
                "superseded_by": None,
                "pulled_at": ((datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z")),
                "source_sha256": "abc",
                "sync_cadence_days": 30,
            }
        ]
    }
    catalog = {
        "catalog_version": "test",
        "scope": "test",
        "controls": [
            {
                "control_id": "DEMO-1",
                "framework_id": "demo",
                "framework": "Demo",
                "title": "t",
                "risk_domain": "x",
                "owner": "team",
                "evidence_requirement": "e",
                "evaluation_rule": "r",
                "frequency": "continuous",
                "implementation_status": "implemented",
                "official_source_ref": "demo",
            }
        ],
    }
    reg_path = tmp_path / "registry.json"
    cat_path = tmp_path / "catalog.json"
    reg_path.write_text(json.dumps(registry), encoding="utf-8")
    cat_path.write_text(json.dumps(catalog), encoding="utf-8")
    view = build_framework_view(reg_path, cat_path)
    assert view[0]["freshness_state"] == "fresh"
    assert view[0]["control_count"] == 1
    assert view[0]["mapping_coverage_pct"] == 100.0


# --- HTTP integration -----------------------------------------------------------


def _spin_handler(lake: Path) -> ThreadingHTTPServer:
    (lake / "gold").mkdir(parents=True, exist_ok=True)
    (lake / "silver").mkdir(parents=True, exist_ok=True)
    (lake / "console.html").write_bytes(b"<!doctype html>")

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
    *,
    body: dict | None = None,
    role: str | None = None,
) -> tuple[int, dict]:
    host, port = server.server_address
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(  # noqa: S310 (local test url)
        f"http://{host}:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    if role:
        req.add_header("X-Trust-Role", role)
    try:
        with urllib.request.urlopen(req) as resp:
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def test_connector_endpoints_round_trip(tmp_path: Path) -> None:
    server = _spin_handler(tmp_path)
    try:
        status, body = _request(server, "GET", "/api/connectors")
        assert status == HTTPStatus.OK
        assert body["count"] >= 1

        status, body = _request(
            server,
            "POST",
            "/api/connectors/github-security/configure",
            body={"state": "enabled", "credentials": {"token": "abc"}, "options": {"org": "x"}},
        )
        assert status == HTTPStatus.CREATED
        assert body["event"]["state"] == "enabled"
        assert body["event"]["credentials"]["token"].startswith("***")

        status, body = _request(server, "POST", "/api/connectors/github-security/probe", body={})
        assert status == HTTPStatus.CREATED
        assert body["run"]["result"] == "ok"

        status, body = _request(server, "GET", "/api/connectors/github-security/runs")
        assert status == HTTPStatus.OK
        assert len(body["runs"]) == 1

        status, body = _request(server, "GET", "/api/frameworks")
        assert status == HTTPStatus.OK
        assert body["count"] >= 1
    finally:
        server.shutdown()


def test_connector_configure_unknown_id_returns_400(tmp_path: Path) -> None:
    server = _spin_handler(tmp_path)
    try:
        status, body = _request(
            server,
            "POST",
            "/api/connectors/does-not-exist/configure",
            body={"state": "enabled"},
        )
        assert status == HTTPStatus.BAD_REQUEST
        assert body["reason"] == "invalid request"
    finally:
        server.shutdown()


def test_connector_post_blocked_in_auditor_mode(tmp_path: Path) -> None:
    server = _spin_handler(tmp_path)
    try:
        status, body = _request(
            server,
            "POST",
            "/api/connectors/github-security/configure",
            body={"state": "enabled"},
            role="auditor",
        )
        assert status == HTTPStatus.FORBIDDEN
        assert body["error"] == "forbidden"

        status, body = _request(
            server,
            "POST",
            "/api/connectors/github-security/probe",
            body={},
            role="auditor",
        )
        assert status == HTTPStatus.FORBIDDEN
    finally:
        server.shutdown()
