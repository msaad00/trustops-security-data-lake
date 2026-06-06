"""Control source-provenance gate: every control is source-linked + reviewed."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.catalog import (
    PROVENANCE_FIELDS,
    controls_missing_provenance,
    validate_catalog,
)
from security_lakehouse.cli import main

_FULL = {f: "x" for f in PROVENANCE_FIELDS}


def _write_catalog(tmp_path: Path, controls: list[dict], name: str = "controls.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"controls": controls}), encoding="utf-8")
    return path


def test_shipped_catalog_passes_validation_with_provenance() -> None:
    # The real catalog must validate (provenance now required) and have no gaps.
    assert validate_catalog() == []
    assert controls_missing_provenance() == {}


def test_missing_provenance_field_is_flagged(tmp_path: Path) -> None:
    incomplete = {"control_id": "C-2", **_FULL}
    del incomplete["source_url"]
    path = _write_catalog(tmp_path, [{"control_id": "C-1", **_FULL}, incomplete])
    gaps = controls_missing_provenance(path)
    assert gaps == {"C-2": ["source_url"]}


def test_cli_provenance_exit_codes(tmp_path: Path, capsys) -> None:
    clean = _write_catalog(tmp_path, [{"control_id": "C-1", **_FULL}], "ok.json")
    assert main(["controls", "provenance", "--catalog", str(clean)]) == 0

    gap = {"control_id": "C-2", **_FULL}
    del gap["reviewed_by"]
    bad = _write_catalog(tmp_path, [gap], "bad.json")
    assert main(["controls", "provenance", "--catalog", str(bad)]) == 1
    assert "reviewed_by" in capsys.readouterr().out
