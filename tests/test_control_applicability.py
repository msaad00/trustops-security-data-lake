"""Control→asset applicability: which controls apply to which asset type."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.catalog import (
    PROVENANCE_FIELDS,
    controls_for_asset_type,
    validate_catalog,
)
from security_lakehouse.cli import main
from security_lakehouse.pipeline import _build_asset_rows


def test_shipped_catalog_declares_asset_types() -> None:
    assert validate_catalog() == []
    # The identity domain governs identity assets; AI domains govern AI assets.
    assert "SOC2-CC6.1" in controls_for_asset_type("iam_role")
    assert controls_for_asset_type("ai_model")
    assert controls_for_asset_type("no_such_asset_type") == []


def _full_control(asset_types: list[str]) -> dict:
    base = {
        "control_id": "T-1",
        "framework_id": "soc2",
        "framework": "SOC 2",
        "title": "t",
        "risk_domain": "identity",
        "owner": "security",
        "evidence_requirement": "e",
        "evaluation_rule": "fail_when_open_violation_or_stale_evidence",
        "frequency": "continuous",
        "implementation_status": "implemented",
        "official_source_ref": "soc2",
        "asset_types": asset_types,
    }
    base.update({f: "x" for f in PROVENANCE_FIELDS})
    return base


def test_empty_asset_types_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"controls": [_full_control([])]}), encoding="utf-8")
    errors = validate_catalog(catalog_path=path)
    assert any("asset_types" in e for e in errors)

    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"controls": [_full_control(["iam_role"])]}), encoding="utf-8")
    assert all("asset_types" not in e for e in validate_catalog(catalog_path=ok))


def _silver(asset_type: str) -> dict:
    return {
        "asset_id": "a1",
        "asset_type": asset_type,
        "asset_owner": "sec",
        "environment": "prod",
        "status": "ok",
        "severity": "info",
        "severity_score": 0,
        "event_time": "2026-06-01T00:00:00Z",
    }


def test_asset_rows_carry_applicable_controls() -> None:
    rows = _build_asset_rows([_silver("iam_role")], {"iam_role": ["SOC2-CC6.1"]})
    assert rows[0]["applicable_control_ids"] == ["SOC2-CC6.1"]
    # Unknown asset type → empty applicability, not a crash.
    bare = _build_asset_rows([_silver("mystery")], {"iam_role": ["SOC2-CC6.1"]})
    assert bare[0]["applicable_control_ids"] == []


def test_cli_applies_to(capsys) -> None:
    assert main(["controls", "applies-to", "--asset-type", "iam_role"]) == 0
    out = capsys.readouterr().out
    assert "SOC2-CC6.1" in out
