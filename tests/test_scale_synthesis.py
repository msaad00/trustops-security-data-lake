"""Audit-scale synthesis, streaming IO, and capped violation rollups."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from security_lakehouse.assessment import build_current_posture, build_violations
from security_lakehouse.io import count_jsonl, iter_jsonl, iter_jsonl_batches, jsonl_field_counts, write_jsonl_from_iterable
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.scale_synthesis import (
    audit_scale_plan,
    iter_synthesize_audit_events,
    write_audit_scale_fixture,
)
from security_lakehouse.validation import validate_raw_events


def test_iter_jsonl_streams_without_loading_whole_file(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    rows = [{"event_id": f"evt-{index}", "source": "aws"} for index in range(5)]
    write_jsonl_from_iterable(target, rows)
    assert count_jsonl(target) == 5
    assert list(iter_jsonl(target)) == rows
    batches = list(iter_jsonl_batches(target, 2))
    assert batches == [rows[:2], rows[2:4], rows[4:]]


def test_jsonl_field_counts(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    write_jsonl_from_iterable(
        target,
        [{"source": "aws"}, {"source": "okta"}, {"source": "aws"}],
    )
    assert dict(jsonl_field_counts(target, "source")) == {"aws": 2, "okta": 1}


def test_audit_scale_plan_projects_findings() -> None:
    plan = audit_scale_plan(1_000_000, controls_per_event=3, open_ratio=0.1)
    assert plan["projected_open_events"] == 100_000
    assert plan["projected_findings"] == 300_000
    assert plan["warehouse_recommended_above_events"] == 100_000


def test_synthesize_audit_events_validate(tmp_path: Path) -> None:
    rows = list(iter_synthesize_audit_events(50, controls_per_event=2, open_ratio=0.2, seed=7))
    assert len(rows) == 50
    assert validate_raw_events(rows) == []
    assert all(len(row["controls"]) == 2 for row in rows)


def test_write_audit_scale_fixture_streams(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    result = write_audit_scale_fixture(output, 200, controls_per_event=2, open_ratio=0.15, seed=1)
    assert result["event_count"] == 200
    assert count_jsonl(output) == 200
    assert result["events_per_second"] > 0


def test_pipeline_manifest_row_counts(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    write_audit_scale_fixture(raw, 120, controls_per_event=1, open_ratio=0.25, seed=3)
    lake = tmp_path / "lake"
    run_pipeline(raw, lake)
    manifest = json.loads((lake / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["row_counts"]["silver"] == 120
    assert manifest["row_counts"]["gold_control_posture"] > 0


def test_build_violations_caps_payload_while_preserving_totals() -> None:
    events = []
    for index in range(100):
        events.append(
            {
                "event_id": f"evt-{index}",
                "status": "open",
                "severity": "high" if index % 2 else "critical",
                "severity_score": 80 if index % 2 else 100,
                "control_ids": ["SOC2-CC1.1", "SOC2-CC2.1"],
                "asset_id": f"asset-{index}",
                "asset_owner": "team-a",
                "environment": "prod",
                "source": "aws",
                "event_type": "cloud.config",
                "evidence_ref": "s3://bucket/obj",
                "raw_sha256": "abc",
                "event_time": "2026-06-30T12:00:00Z",
            }
        )
    violations, summary = build_violations(events, max_violations=10)
    assert summary["total_count"] == 200
    assert summary["truncated"] is True
    assert len(violations) == 10
    assert all(item["severity"] == "critical" for item in violations)


def test_build_current_posture_auto_caps_large_lakes(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    write_audit_scale_fixture(raw, 500, controls_per_event=2, open_ratio=0.3, seed=11)
    lake = tmp_path / "lake"
    run_pipeline(raw, lake)
    posture = build_current_posture(lake, max_violations=25)
    assert posture["violation_summary"]["total_count"] > 25
    assert len(posture["violations"]) == 25
    assert posture["posture"]["open_violation_count"] == posture["violation_summary"]["total_count"]
