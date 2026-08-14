"""SIEM alerts connector tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from security_lakehouse import connector_runner, connector_state
from security_lakehouse.connectors_siem import (
    SiemClient,
    SiemFixtureClient,
    collect_siem_evidence,
    discover_siem_scope,
    probe_siem_access,
)
from security_lakehouse.ingestion.watermark import read_watermark, write_watermark
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "siem-alerts"


def test_collect_siem_fixture_evidence_validates() -> None:
    rows = collect_siem_evidence(
        SiemFixtureClient(FIXTURE_DIR),
        collected_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )

    assert len(rows) == 2
    assert validate_raw_events(rows) == []
    assert {row["source"] for row in rows} == {"siem-alerts"}
    assert {row["event_type"] for row in rows} == {"detection.alert"}
    assert any(row["status"] == "open" and row["severity"] == "high" for row in rows)


def test_siem_fixture_client_incremental_since() -> None:
    client = SiemFixtureClient(FIXTURE_DIR)
    rows = collect_siem_evidence(client, since="2026-05-20T17:00:00Z")
    assert len(rows) == 1
    assert rows[0]["event_id"] == "siem-alert-010"


def test_siem_sync_writes_raw_evidence_and_materializes(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="siem-alerts",
        state="enabled",
        actor="alice",
    )

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="siem-alerts",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.result == "ok"
    assert result.evidence_count == 2
    assert result.watermark_cursor == "2026-05-20T17:30:00Z"
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 2
    assert validate_raw_events(raw_rows) == []
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    run = connector_state.latest_run(tmp_path, "siem-alerts", kind="sync")
    assert run is not None
    assert run["result"] == "ok"
    assert run["evidence_count"] == 2


def test_siem_sync_resumes_from_watermark(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="siem-alerts",
        state="enabled",
        actor="alice",
    )
    write_watermark(tmp_path, "siem-alerts", "2026-05-20T17:00:00Z")

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="siem-alerts",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.evidence_count == 1
    assert result.watermark_cursor == "2026-05-20T17:30:00Z"
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 1
    assert read_watermark(tmp_path, "siem-alerts") == "2026-05-20T17:30:00Z"


def test_siem_live_query_parses_json_list() -> None:
    body = json.dumps(
        [
            {
                "alert_id": "live-1",
                "event_time": "2026-06-01T10:00:00Z",
                "severity": "low",
                "status": "observed",
            }
        ]
    )
    response = MagicMock()
    response.read.return_value = body.encode("utf-8")
    response.__enter__.return_value = response

    with patch("security_lakehouse.netguard.open_public", return_value=response):
        rows = SiemClient("https://siem.example", token="secret").alerts()

    assert len(rows) == 1
    assert rows[0]["alert_id"] == "live-1"


def test_siem_retries_on_rate_limit_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single 429 must be retried (honoring Retry-After), not fail the whole sync."""
    import urllib.error

    monkeypatch.setattr("security_lakehouse.ingestion.backoff.time.sleep", lambda *_: None)
    response = MagicMock()
    response.read.return_value = json.dumps([{"alert_id": "a1", "event_time": "2026-06-01T10:00:00Z"}]).encode("utf-8")
    response.__enter__.return_value = response
    sequence: list[object] = [
        urllib.error.HTTPError("https://siem.example", 429, "slow down", {"Retry-After": "0"}, None),
        response,
    ]

    def flaky(*_args: object, **_kwargs: object) -> object:
        item = sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch("security_lakehouse.netguard.open_public", side_effect=flaky):
        rows = SiemClient("https://siem.example", token="secret").alerts()

    assert [row["alert_id"] for row in rows] == ["a1"]
    assert sequence == []  # both the 429 and the success were consumed → retried once


def test_siem_does_not_retry_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 404 is terminal — surfaced as a sanitized error, never retried."""
    import urllib.error

    calls = {"n": 0}

    def always_404(*_args: object, **_kwargs: object) -> object:
        calls["n"] += 1
        raise urllib.error.HTTPError("https://siem.example", 404, "missing", {}, None)

    with patch("security_lakehouse.netguard.open_public", side_effect=always_404), pytest.raises(ValueError):
        SiemClient("https://siem.example", token="secret").alerts()

    assert calls["n"] == 1  # no retry on a 4xx


def test_siem_probe_and_discovery_with_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTOPS_SIEM_TOKEN", "secret-token")

    with patch.object(
        SiemClient,
        "probe",
        return_value={"ok": True, "index": "alerts", "alert_count": 4, "error": None},
    ):
        probe = probe_siem_access(
            credentials={
                "host": "https://siem.example",
                "credential_ref": "TRUSTOPS_SIEM_TOKEN",
            },
            options={"index": "alerts"},
        )
    assert probe["ok"] is True
    assert probe["alert_count"] == 4

    with patch.object(
        SiemClient,
        "discover_scope",
        return_value={
            "ok": True,
            "selection_mode": "visible_indexes",
            "selectors": [{"kind": "index", "name": "alerts"}],
            "recommended_options": {"index": "alerts"},
        },
    ):
        scope = discover_siem_scope(
            credentials={
                "host": "https://siem.example",
                "credential_ref": "TRUSTOPS_SIEM_TOKEN",
            },
            options={},
        )
    assert scope["ok"] is True
    assert scope["recommended_options"]["index"] == "alerts"


def test_siem_probe_requires_host() -> None:
    with pytest.raises(ValueError, match="requires host"):
        probe_siem_access(credentials={}, options={})


def test_siem_fixture_discovery_lists_indexes() -> None:
    scope = SiemFixtureClient(FIXTURE_DIR).discover_scope()
    assert scope["ok"] is True
    assert any(item["name"] == "alerts" for item in scope["selectors"])
