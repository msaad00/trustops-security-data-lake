"""Optional agent harness tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from security_lakehouse.agents import build_posture_review_graph, run_posture_review
from security_lakehouse.cli import main
from test_api_v1 import _seed_lake


def _seed_gap(lake: Path) -> None:
    _seed_lake(lake)
    rows = [
        {
            "test_id": "test-soc2",
            "control_id": "SOC2-CC6.1",
            "framework": "SOC 2",
            "owner": "security-platform",
            "status": "needs_evidence",
            "missing_evidence_types": ["identity.access_review"],
            "stale_evidence_types": [],
            "expired_evidence_types": ["mfa.status"],
            "freshness_status": "expired",
        }
    ]
    (lake / "gold" / "control_tests.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_posture_review_runs_without_langgraph_or_llm(tmp_path: Path) -> None:
    _seed_gap(tmp_path)

    state = run_posture_review(tmp_path, role="read_only")

    assert state["mode"] == "rules_only"
    assert state["posture"]["posture"]["control_count"] >= 1
    assert state["evidence_gaps"][0]["control_id"] == "SOC2-CC6.1"
    assert state["decisions"][0].action == "create_evidence_request"
    assert state["decisions"][0].requires_approval is True
    assert state["decisions"][0].status == "proposed"


def test_posture_review_uses_role_redaction(tmp_path: Path) -> None:
    _seed_gap(tmp_path)

    state = run_posture_review(tmp_path, role="auditor")

    assert state["evidence_gaps"][0]["owner"] == "[redacted]"


def test_langgraph_builder_is_optional() -> None:
    if importlib.util.find_spec("langgraph") is not None:
        assert build_posture_review_graph() is not None
        return

    with pytest.raises(RuntimeError, match="install trustops-security-data-lake\\[agents\\]"):
        build_posture_review_graph()


def test_posture_review_cli_outputs_json(tmp_path: Path, capsys) -> None:
    _seed_gap(tmp_path)

    assert main(["agents", "posture-review", "--lake", str(tmp_path), "--role", "auditor"]) == 0
    out = json.loads(capsys.readouterr().out)

    assert out["mode"] == "rules_only"
    assert out["role"] == "auditor"
    assert out["evidence_gaps"][0]["owner"] == "[redacted]"
    assert out["decisions"][0]["requires_approval"] is True
