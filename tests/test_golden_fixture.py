"""Unified golden fixture tests."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.assessment import build_current_posture
from security_lakehouse.fixtures import find_fixture
from security_lakehouse.golden_fixture import (
    GOLDEN_COMPANY,
    build_golden_events,
    golden_control_ids,
    golden_fixture_summary,
)
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.validation import validate_raw_events


def test_golden_fixture_summary_lists_37_controls() -> None:
    summary = golden_fixture_summary()
    assert summary["company"] == GOLDEN_COMPANY
    assert summary["control_count"] == 37
    assert summary["soc2_control_count"] == 33
    assert summary["nist_ai_control_count"] == 4
    assert len(golden_control_ids()) == 37


def test_golden_events_validate() -> None:
    rows = build_golden_events()
    assert len(rows) == 37
    assert validate_raw_events(rows) == []
    assert {row["controls"][0] for row in rows} == set(golden_control_ids())


def test_golden_fixture_ships_and_populates_dashboard(tmp_path: Path) -> None:
    fixture = find_fixture(GOLDEN_COMPANY)
    assert fixture is not None
    assert fixture.event_count == 37
    assert set(fixture.controls) == set(golden_control_ids())

    run_pipeline(fixture.raw_path, tmp_path)
    posture_rows = [
        json.loads(line)
        for line in (tmp_path / "gold" / "control_posture.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(posture_rows) == 37
    assert {row["control_id"] for row in posture_rows} == set(golden_control_ids())

    posture = build_current_posture(tmp_path)
    assert posture["posture"]["control_count"] == 37
    assert posture["posture"]["framework_count"] == 2
    frameworks = {row["framework"] for row in posture["frameworks"]}
    assert frameworks == {"SOC 2", "NIST AI RMF"}
