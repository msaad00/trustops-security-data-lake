"""Event-driven continuous eval: a sync that lands evidence pushes to the
``trigger.evidence_changed`` workflows instead of waiting for the next cron tick.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import security_lakehouse.connector_runner as connector_runner
from security_lakehouse.workflows import run_evidence_changed_workflows, save_workflow


def _seed_workflow(lake: Path, *, connector_id: str | None = None) -> None:
    trigger_params = {"connector_id": connector_id} if connector_id else {}
    save_workflow(
        lake,
        workflow_id=None,
        name="on-evidence",
        description="",
        nodes=[
            {"id": "t", "node_type": "trigger.evidence_changed", "params": trigger_params},
            {"id": "c", "node_type": "check.evidence_exists", "params": {"control_id": "SOC2-CC6.1"}},
        ],
        edges=[{"source": "t", "target": "c", "condition": "always"}],
    )


def test_evidence_changed_fires_unscoped_workflow(tmp_path: Path) -> None:
    _seed_workflow(tmp_path)
    runs = run_evidence_changed_workflows(tmp_path, connector_id="aws-posture")
    assert len(runs) == 1


def test_evidence_changed_respects_connector_scope(tmp_path: Path) -> None:
    _seed_workflow(tmp_path, connector_id="okta-identity")
    # A scoped trigger only fires for its connector.
    assert run_evidence_changed_workflows(tmp_path, connector_id="aws-posture") == []
    assert len(run_evidence_changed_workflows(tmp_path, connector_id="okta-identity")) == 1


def test_no_evidence_changed_workflows_is_noop(tmp_path: Path) -> None:
    assert run_evidence_changed_workflows(tmp_path, connector_id="aws-posture") == []


def test_fire_evidence_changed_swallows_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_args: object, **_kwargs: object) -> list:
        raise RuntimeError("workflow engine down")

    monkeypatch.setattr("security_lakehouse.workflows.run_evidence_changed_workflows", boom)
    connector_runner._fire_evidence_changed(tmp_path, "aws-posture")  # must not raise
    assert "automations failed" in capsys.readouterr().err
