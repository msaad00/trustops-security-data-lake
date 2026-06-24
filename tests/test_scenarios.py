"""End-to-end scenario runner tests."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.cli import main
from security_lakehouse.scenarios import run_live_cloud_posture_scenario

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_dirs() -> dict[str, str]:
    return {
        "azure-posture": str(FIXTURES / "azure"),
        "aws-posture": str(FIXTURES / "aws"),
        "snowflake-evidence-lake": str(FIXTURES / "snowflake"),
    }


def test_live_cloud_posture_scenario_runs_connectors_integrity_snapshot_and_workflow(tmp_path: Path) -> None:
    report = run_live_cloud_posture_scenario(
        tmp_path,
        connectors=["azure-posture", "aws-posture", "snowflake-evidence-lake"],
        fixture_dirs=_fixture_dirs(),
        actor="test",
    )

    assert report["summary"]["ok"] is True
    assert report["summary"]["evidence_count"] == 22
    assert report["summary"]["sources"] == ["aws", "azure", "snowflake"]
    assert report["integrity"]["ok"] is True
    assert report["snapshot_chain"]["ok"] is True
    assert report["snapshot_chain"]["length"] == 2
    assert report["workflow"]["run"]["result"] == "ok"
    assert (tmp_path / "gold" / "scenario_reports" / "live-cloud-posture.json").is_file()


def test_live_cloud_posture_scenario_cli_emits_report(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "scenario",
            "run",
            "live-cloud-posture",
            "--lake",
            str(tmp_path),
            "--connector",
            "azure-posture",
            "--connector",
            "aws-posture",
            "--connector",
            "snowflake-evidence-lake",
            "--fixture",
            f"azure-posture={FIXTURES / 'azure'}",
            "--fixture",
            f"aws-posture={FIXTURES / 'aws'}",
            "--fixture",
            f"snowflake-evidence-lake={FIXTURES / 'snowflake'}",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scenario"] == "live-cloud-posture"
    assert payload["summary"]["ok"] is True
    assert payload["integrity"]["silver_count"] == 22
