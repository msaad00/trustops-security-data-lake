"""Snowflake evidence-lake connector tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from security_lakehouse import connector_runner, connector_state
from security_lakehouse.connectors_snowflake import (
    SnowflakeFixtureClient,
    collect_snowflake_evidence,
)
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "snowflake"


def test_collect_snowflake_fixture_evidence_validates() -> None:
    rows = collect_snowflake_evidence(
        SnowflakeFixtureClient(FIXTURE_DIR, account="acme_snowflake"),
        collected_at=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
    )

    assert len(rows) == 8
    assert validate_raw_events(rows) == []
    assert {row["source"] for row in rows} == {"snowflake"}
    assert {row["event_type"] for row in rows} == {
        "snowflake.asset.risk",
        "snowflake.audit.event",
        "snowflake.control.posture",
        "snowflake.evidence.bundle",
    }
    assert any(row["status"] == "open" and row["severity"] == "high" for row in rows)
    assert any(row["entity"]["asset_id"] == "snowflake:warehouse:trustops_wh" for row in rows)


def test_snowflake_sync_writes_raw_evidence_and_materializes(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.result == "ok"
    assert result.evidence_count == 8
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 8
    assert validate_raw_events(raw_rows) == []
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "control_posture.jsonl").is_file()
    assert (tmp_path / "gold" / "asset_risk.jsonl").is_file()
    run = connector_state.latest_run(tmp_path, "snowflake-evidence-lake", kind="sync")
    assert run is not None
    assert run["result"] == "ok"
    assert run["evidence_count"] == 8


def test_snowflake_live_requires_read_only_connection_details(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    for name in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_OAUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(connector_runner.ConnectorSyncError, match="SNOWFLAKE_ACCOUNT"):
        connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake", materialize=False)
