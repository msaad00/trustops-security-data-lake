"""Incremental materialize, split schedules, and warehouse scale tier."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from security_lakehouse.connector_state import append_config_event, latest_config
from security_lakehouse.lake_eval import run_lake_eval
from security_lakehouse.lake_scale import (
    DEFAULT_EVAL_SCHEDULE,
    apply_split_schedule_defaults,
    connector_materialize_on_sync,
    lake_eval_schedule,
    resolve_materialize_strategy,
)
from security_lakehouse.pipeline import run_pipeline, run_pipeline_incremental
from security_lakehouse.scale_synthesis import write_audit_scale_fixture
from security_lakehouse.scheduler import tick


def test_apply_split_schedule_defaults_sets_eval_and_ingest_only() -> None:
    opts = apply_split_schedule_defaults({"sync_schedule": "every 15m"})
    assert opts["eval_schedule"] == DEFAULT_EVAL_SCHEDULE
    assert opts["split_ingest_eval"] is True
    assert opts["materialize"] is False


def test_connector_materialize_on_sync_respects_split_mode() -> None:
    assert connector_materialize_on_sync({"split_ingest_eval": True}) is False
    assert connector_materialize_on_sync({"split_ingest_eval": True, "materialize": True}) is True
    assert connector_materialize_on_sync({}) is True


def test_run_pipeline_incremental_processes_only_delta(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    lake = tmp_path / "lake"
    write_audit_scale_fixture(raw, 40, controls_per_event=1, open_ratio=0.2, seed=11)
    run_pipeline(raw, lake)
    manifest_v1 = json.loads((lake / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_v1["materialize_mode"] == "full"
    assert manifest_v1["row_counts"]["silver"] == 40

    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.append(
        {
            **rows[0],
            "event_id": "scale-delta-0001",
            "status": "open",
            "severity": "critical",
        }
    )
    raw.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")

    result = run_pipeline_incremental(raw, lake)
    manifest_v2 = json.loads((lake / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_v2["materialize_mode"] == "incremental"
    assert manifest_v2["delta_count"] == 1
    assert manifest_v2["row_counts"]["silver"] == 41
    assert result.silver_count == 41


def test_run_pipeline_incremental_noop_when_unchanged(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    lake = tmp_path / "lake"
    write_audit_scale_fixture(raw, 25, controls_per_event=1, open_ratio=0.1, seed=3)
    run_pipeline(raw, lake)
    manifest_v1 = json.loads((lake / "manifest.json").read_text(encoding="utf-8"))

    result = run_pipeline_incremental(raw, lake)
    manifest_v2 = json.loads((lake / "manifest.json").read_text(encoding="utf-8"))
    assert result.silver_count == manifest_v1["row_counts"]["silver"]
    assert manifest_v2["row_counts"]["silver"] == manifest_v1["row_counts"]["silver"]


def test_resolve_materialize_strategy_warehouse_required_above_threshold(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw.jsonl"
    lake = tmp_path / "lake"
    write_audit_scale_fixture(raw, 120, controls_per_event=1, open_ratio=0.1, seed=4)
    run_pipeline(raw, lake)
    monkeypatch.setattr(
        "security_lakehouse.lake_scale.WAREHOUSE_ROW_THRESHOLD",
        50,
    )
    strategy = resolve_materialize_strategy(lake, raw, env={})
    assert strategy["mode"] == "warehouse_required"
    assert strategy["warehouse_sink_configured"] is False


def test_configure_applies_split_schedule_defaults(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        credentials={"credential_ref": "TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"},
        options={"sync_schedule": "every 15m", "repo": "acme/app"},
    )
    config = latest_config(tmp_path, "github-security")
    opts = config["options"]
    assert opts["eval_schedule"] == DEFAULT_EVAL_SCHEDULE
    assert opts["split_ingest_eval"] is True
    assert opts["materialize"] is False


def test_scheduler_fires_split_sync_and_lake_eval(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        options={
            "sync_schedule": "every 5m",
            "eval_schedule": "every 10m",
            "repo": "acme/model-service",
            "fixture_dir": str(Path(__file__).parent / "fixtures" / "github-governance"),
        },
    )
    base = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
    sync_calls: list[bool] = []

    def connector_runner(_lake, **kwargs):
        sync_calls.append(kwargs.get("materialize", True))
        return {"result": "ok", "evidence_count": 5}

    first = tick(tmp_path, now=base, connector_runner=connector_runner)
    assert any(row.get("target_kind") == "connector" for row in first)
    assert sync_calls == [False]

    second = tick(tmp_path, now=base + timedelta(minutes=10), connector_runner=connector_runner)
    kinds = [row.get("target_kind") for row in second]
    assert "lake_eval" in kinds


def test_lake_eval_schedule_from_enabled_connector(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        options={"sync_schedule": "every 15m"},
    )
    assert lake_eval_schedule(tmp_path) == DEFAULT_EVAL_SCHEDULE


def test_run_lake_eval_writes_scale_state(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir(parents=True)
    (lake / "raw").mkdir(parents=True)
    write_audit_scale_fixture(lake / "raw" / "connector_events.jsonl", 30, controls_per_event=1, open_ratio=0.1, seed=9)
    result = run_lake_eval(lake, actor="test")
    assert result.result == "ok"
    assert (lake / "gold" / "lake_scale.json").is_file()
