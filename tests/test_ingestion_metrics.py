"""Ingestion accuracy and catalog coverage metrics."""

from __future__ import annotations

from pathlib import Path

from security_lakehouse.connector_state import append_config_event
from security_lakehouse.ingestion_metrics import build_catalog_coverage, build_eval_accuracy
from security_lakehouse.ingestion_status import build_ingestion_status
from security_lakehouse.lake_eval import run_lake_eval
from security_lakehouse.scale_synthesis import write_audit_scale_fixture


def test_build_eval_accuracy_from_control_tests(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "raw").mkdir()
    write_audit_scale_fixture(lake / "raw" / "connector_events.jsonl", 15, controls_per_event=1, open_ratio=0.25, seed=4)
    run_lake_eval(lake, actor="test")

    accuracy = build_eval_accuracy(lake)
    assert accuracy["total_tests"] > 0
    assert accuracy["passing"] + accuracy["failing"] + accuracy["warning"] == accuracy["total_tests"]
    assert accuracy["pass_rate"] is not None
    assert accuracy["evidence_source_count"] >= 1


def test_build_catalog_coverage_counts_implemented_and_enabled(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="aws-posture", state="enabled", actor="test")
    append_config_event(tmp_path, connector_id="okta-identity", state="enabled", actor="test")
    from security_lakehouse.connector_state import build_catalog_view

    connectors = build_catalog_view(tmp_path)
    coverage = build_catalog_coverage(connectors=connectors)
    assert coverage["total"] >= 10
    assert coverage["implemented"] >= 1
    assert coverage["enabled"] == 2
    assert coverage["implementation_rate"] > 0
    assert any(row["category"] for row in coverage["by_category"])


def test_ingestion_status_includes_eval_accuracy_and_catalog_coverage(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "raw").mkdir()
    write_audit_scale_fixture(lake / "raw" / "connector_events.jsonl", 10, controls_per_event=1, open_ratio=0.1, seed=5)
    run_lake_eval(lake, actor="test")
    append_config_event(lake, connector_id="aws-posture", state="enabled", actor="test")

    status = build_ingestion_status(lake)
    assert status["eval_accuracy"]["total_tests"] > 0
    assert status["catalog_coverage"]["total"] >= status["catalog_coverage"]["implemented"]
    actions = [row["action"] for row in status["recommended_actions"]]
    assert "triage_failing_control_tests" in actions or status["eval_accuracy"]["failing"] == 0
