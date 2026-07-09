"""Dedicated tests for lake evaluation runs."""

from __future__ import annotations

from pathlib import Path

from security_lakehouse.ingestion_metrics import build_eval_accuracy
from security_lakehouse.lake_eval import list_eval_runs, run_lake_eval
from security_lakehouse.scale_synthesis import write_audit_scale_fixture


def test_list_eval_runs_returns_newest_first(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "raw").mkdir()
    write_audit_scale_fixture(lake / "raw" / "connector_events.jsonl", 12, controls_per_event=1, open_ratio=0.1, seed=1)
    first = run_lake_eval(lake, actor="first")
    second = run_lake_eval(lake, actor="second")
    assert first.result == "ok"
    assert second.result == "ok"

    runs = list_eval_runs(lake, limit=10)
    assert len(runs) == 2
    assert runs[0]["actor"] == "second"
    assert runs[1]["actor"] == "first"


def test_run_lake_eval_records_accuracy_snapshot(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "raw").mkdir()
    write_audit_scale_fixture(lake / "raw" / "connector_events.jsonl", 20, controls_per_event=1, open_ratio=0.2, seed=2)
    result = run_lake_eval(lake, actor="accuracy-test")
    assert result.result == "ok"

    accuracy = build_eval_accuracy(lake)
    assert accuracy["total_tests"] > 0
    assert accuracy["pass_rate"] is not None

    latest = list_eval_runs(lake, limit=1)[0]
    assert latest["control_tests_total"] == accuracy["total_tests"]
    assert latest["control_tests_passing"] == accuracy["passing"]
    assert latest["pass_rate"] == accuracy["pass_rate"]


def test_run_lake_eval_warehouse_required_is_error(tmp_path: Path, monkeypatch) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "raw").mkdir()
    write_audit_scale_fixture(
        lake / "raw" / "connector_events.jsonl",
        5,
        controls_per_event=1,
        open_ratio=0.0,
        seed=3,
    )

    def _force_warehouse_required(_lake, _raw, *, env=None):
        return {
            "mode": "warehouse_required",
            "recommendation": "configure warehouse sink",
            "event_count": 200_000,
            "silver_count": 0,
        }

    monkeypatch.setattr(
        "security_lakehouse.lake_eval.resolve_materialize_strategy",
        _force_warehouse_required,
    )
    result = run_lake_eval(lake, actor="warehouse-test")
    assert result.result == "error"
    assert result.error
    latest = list_eval_runs(lake, limit=1)[0]
    assert latest["result"] == "error"
    assert latest.get("control_tests_total") is None
