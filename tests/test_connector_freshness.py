"""Per-connector freshness SLO evaluation in the catalog view."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from security_lakehouse.connector_state import (
    DEFAULT_FRESHNESS_SLO_MINUTES,
    _evaluate_freshness,
    append_run_event,
    build_catalog_view,
)
from security_lakehouse.models import parse_event_time, utc_iso

CONNECTOR_ID = "github-security"


def _view_entry(lake_dir: Path, connector_id: str = CONNECTOR_ID) -> dict:
    view = build_catalog_view(lake_dir)
    entry = next(c for c in view if c["connector_id"] == connector_id)
    return entry


def test_never_synced_reports_never_synced(tmp_path: Path) -> None:
    entry = _view_entry(tmp_path)
    assert entry["freshness_state"] == "never_synced"
    # next_run_at is present and parseable (defaults to "now").
    assert entry["next_run_at"] is not None
    parse_event_time(entry["next_run_at"])


def test_recent_sync_is_fresh(tmp_path: Path) -> None:
    append_run_event(tmp_path, connector_id=CONNECTOR_ID, kind="sync", result="ok")
    entry = _view_entry(tmp_path)
    assert entry["freshness_state"] == "fresh"
    # next_run_at is in the future relative to the just-recorded sync.
    next_run = parse_event_time(entry["next_run_at"])
    last_sync = parse_event_time(entry["last_sync_at"])
    assert next_run > last_sync


def test_old_sync_is_stale(tmp_path: Path) -> None:
    # Write a successful sync far in the past, bypassing the now-stamped helper.
    gold = tmp_path / "gold"
    gold.mkdir(parents=True, exist_ok=True)
    old_at = utc_iso(datetime.now(UTC) - timedelta(days=30))
    record = {
        "connector_id": CONNECTOR_ID,
        "kind": "sync",
        "result": "ok",
        "occurred_at": old_at,
    }
    (gold / "connector_runs.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    entry = _view_entry(tmp_path)
    assert entry["freshness_state"] == "stale"
    # next_run_at = last_sync + slo, which (for a 30-day-old sync) is in the past.
    next_run = parse_event_time(entry["next_run_at"])
    assert next_run < datetime.now(UTC)


def test_failed_sync_does_not_count_as_synced(tmp_path: Path) -> None:
    append_run_event(tmp_path, connector_id=CONNECTOR_ID, kind="sync", result="error")
    entry = _view_entry(tmp_path)
    assert entry["freshness_state"] == "never_synced"


def test_failed_sync_after_success_keeps_freshness(tmp_path: Path) -> None:
    append_run_event(tmp_path, connector_id=CONNECTOR_ID, kind="sync", result="ok")
    append_run_event(tmp_path, connector_id=CONNECTOR_ID, kind="sync", result="error")
    entry = _view_entry(tmp_path)
    assert entry["freshness_state"] == "fresh"
    assert entry["last_sync"]["result"] == "error"
    assert entry["last_successful_sync"]["result"] == "ok"


def test_evaluate_freshness_boundary_and_ordering() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    base = {"freshness_slo_minutes": 60}

    # Exactly at the SLO boundary is still fresh (age == slo, not > slo).
    sync = {"result": "ok", "occurred_at": utc_iso(now - timedelta(minutes=60))}
    fresh = _evaluate_freshness(base, sync, now=now)
    assert fresh["freshness_state"] == "fresh"
    assert parse_event_time(fresh["next_run_at"]) == now

    # One minute past the SLO is stale.
    sync = {"result": "ok", "occurred_at": utc_iso(now - timedelta(minutes=61))}
    stale = _evaluate_freshness(base, sync, now=now)
    assert stale["freshness_state"] == "stale"
    assert parse_event_time(stale["next_run_at"]) < now


def test_missing_slo_falls_back_to_default() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    sync = {"result": "ok", "occurred_at": utc_iso(now - timedelta(minutes=10))}
    result = _evaluate_freshness({}, sync, now=now)
    assert result["freshness_slo_minutes"] == DEFAULT_FRESHNESS_SLO_MINUTES
    assert result["freshness_state"] == "fresh"


def test_zulu_suffix_timestamp_is_parsed() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    sync = {"result": "ok", "occurred_at": "2026-06-01T11:30:00Z"}
    result = _evaluate_freshness({"freshness_slo_minutes": 60}, sync, now=now)
    assert result["freshness_state"] == "fresh"
    assert result["last_sync_at"] == "2026-06-01T11:30:00Z"
