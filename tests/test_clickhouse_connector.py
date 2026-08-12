"""ClickHouse telemetry-lake connector tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from security_lakehouse import connector_runner, connector_state
from security_lakehouse.connectors_clickhouse import (
    ClickHouseClient,
    ClickHouseFixtureClient,
    collect_clickhouse_evidence,
    discover_clickhouse_scope,
    probe_clickhouse_access,
)
from security_lakehouse.ingestion.watermark import read_watermark, write_watermark
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "clickhouse-telemetry-lake"


def test_collect_clickhouse_fixture_evidence_validates() -> None:
    rows = collect_clickhouse_evidence(
        ClickHouseFixtureClient(FIXTURE_DIR),
        collected_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )

    assert len(rows) == 3
    assert validate_raw_events(rows) == []
    assert {row["source"] for row in rows} == {"clickhouse"}
    assert {row["event_type"] for row in rows} == {
        "runtime.detection",
        "runtime.policy.violation",
        "telemetry.metric",
    }
    assert any(row["status"] == "open" and row["severity"] == "high" for row in rows)


def test_clickhouse_fixture_client_incremental_since() -> None:
    client = ClickHouseFixtureClient(FIXTURE_DIR)
    rows = collect_clickhouse_evidence(client, since="2026-06-01T11:00:00.000Z")
    assert len(rows) == 2
    assert all(row["event_id"] != "ch-evt-001" for row in rows)


def test_clickhouse_sync_writes_raw_evidence_and_materializes(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="clickhouse-telemetry-lake",
        state="enabled",
        actor="alice",
    )

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="clickhouse-telemetry-lake",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.result == "ok"
    assert result.evidence_count == 3
    assert result.watermark_cursor == "2026-06-01T12:15:00Z"
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 3
    assert validate_raw_events(raw_rows) == []
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    run = connector_state.latest_run(tmp_path, "clickhouse-telemetry-lake", kind="sync")
    assert run is not None
    assert run["result"] == "ok"
    assert run["evidence_count"] == 3


def test_clickhouse_sync_resumes_from_watermark(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="clickhouse-telemetry-lake",
        state="enabled",
        actor="alice",
    )
    write_watermark(tmp_path, "clickhouse-telemetry-lake", "2026-06-01T11:00:00.000Z")

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="clickhouse-telemetry-lake",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.evidence_count == 2
    assert result.watermark_cursor == "2026-06-01T12:15:00Z"
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 2
    assert read_watermark(tmp_path, "clickhouse-telemetry-lake") == "2026-06-01T12:15:00Z"


def test_clickhouse_live_query_parses_json_each_row() -> None:
    body = "\n".join(
        [
            json.dumps({"event_id": "live-1", "event_time": "2026-06-01T10:00:00Z"}),
            json.dumps({"event_id": "live-2", "event_time": "2026-06-01T11:00:00Z"}),
        ]
    )
    response = MagicMock()
    response.read.return_value = body.encode("utf-8")
    response.__enter__.return_value = response

    with patch("security_lakehouse.netguard.open_public", return_value=response):
        rows = ClickHouseClient("https://ch.example:8443", user="reader", password="secret").normalized_events()

    assert len(rows) == 2
    assert rows[0]["event_id"] == "live-1"


def test_clickhouse_probe_and_discovery_with_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTOPS_CLICKHOUSE_TOKEN", "secret-token")

    with patch.object(
        ClickHouseClient,
        "probe",
        return_value={"ok": True, "table": "security.normalized_events", "row_count": 4, "error": None},
    ):
        probe = probe_clickhouse_access(
            credentials={
                "host": "https://ch.example:8443",
                "credential_ref": "TRUSTOPS_CLICKHOUSE_TOKEN",
            },
            options={},
        )
    assert probe["ok"] is True
    assert probe["row_count"] == 4

    with patch.object(
        ClickHouseClient,
        "discover_scope",
        return_value={
            "ok": True,
            "selection_mode": "visible_tables",
            "selectors": [{"kind": "table", "name": "normalized_events"}],
            "recommended_options": {"database": "security", "table": "normalized_events"},
        },
    ):
        scope = discover_clickhouse_scope(
            credentials={
                "host": "https://ch.example:8443",
                "credential_ref": "TRUSTOPS_CLICKHOUSE_TOKEN",
            },
            options={},
        )
    assert scope["ok"] is True
    assert scope["recommended_options"]["table"] == "normalized_events"


def test_clickhouse_probe_requires_host() -> None:
    with pytest.raises(ValueError, match="requires host"):
        probe_clickhouse_access(credentials={}, options={})


class _FakeClickHouseDiscoveryClient:
    def show_tables(self) -> list[str]:
        return ["normalized_events", "control_posture"]

    def discover_scope(self) -> dict[str, Any]:
        tables = self.show_tables()
        return {
            "ok": True,
            "selection_mode": "visible_tables",
            "selectors": [
                {"kind": "database", "name": "security", "required": True, "selected": True},
                *[
                    {
                        "kind": "table",
                        "name": name,
                        "required": name == "normalized_events",
                        "selected": name == "normalized_events",
                    }
                    for name in tables
                ],
            ],
            "recommended_options": {"database": "security", "table": "normalized_events"},
        }


def test_clickhouse_fixture_discovery_lists_tables() -> None:
    scope = ClickHouseFixtureClient(FIXTURE_DIR).discover_scope()
    assert scope["ok"] is True
    assert any(item["name"] == "normalized_events" for item in scope["selectors"])
