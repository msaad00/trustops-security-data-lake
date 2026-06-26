"""Per-branch failure isolation in the workflow engine.

A node failure must only skip its *downstream descendants*. Independent
parallel branches keep running instead of the whole DAG aborting on the first
error (Tines-grade behavior).
"""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.workflows import run_workflow, save_workflow


def _bootstrap_silver(lake: Path) -> None:
    """Minimal gold/silver layer so snapshot + evidence checks can run."""
    (lake / "silver").mkdir(parents=True, exist_ok=True)
    (lake / "silver" / "normalized_events.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "event_id": f"evt-{i}",
                    "control_ids": ["SOC2-CC6.1"],
                    "asset_id": "x",
                    "asset_owner": "platform",
                    "environment": "test",
                    "source": "test",
                    "event_type": "test.evidence",
                    "event_time": "2026-05-20T00:00:00Z",
                    "evidence_collected_at": "2026-05-20T00:00:00Z",
                    "evidence_ref": f"test://evt-{i}",
                    "raw_sha256": "0" * 64,
                    "severity": "info",
                    "severity_score": 0,
                    "status": "passed",
                }
            )
            for i in range(3)
        )
        + "\n",
        encoding="utf-8",
    )
    (lake / "gold").mkdir(parents=True, exist_ok=True)
    (lake / "gold" / "control_posture.jsonl").write_text(
        json.dumps(
            {
                "control_id": "SOC2-CC6.1",
                "framework": "SOC 2",
                "framework_id": "soc2",
                "status": "pass",
                "control_count": 1,
                "evidence_count": 3,
                "event_count": 3,
                "risk_score": 10,
                "owner": "security-platform",
                "title": "Logical access",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (lake / "gold" / "asset_risk.jsonl").write_text(
        json.dumps(
            {
                "asset_id": "x",
                "asset_owner": "platform",
                "asset_type": "test",
                "environment": "test",
                "risk_score": 0,
                "critical_open": 0,
                "high_open": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (lake / "gold" / "control_tests.jsonl").write_text(
        json.dumps(
            {
                "control_id": "SOC2-CC6.1",
                "result": "pass",
                "evaluated_at": "2026-05-20T00:00:00Z",
                "confidence_score": 88,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_node_failure_isolated_to_its_branch(tmp_path: Path) -> None:
    """A failing node skips only its descendants; the parallel branch runs.

    DAG (diamond fan-out from a shared trigger):

        trigger ─┬─> bad ──> bad_child      (bad raises: missing violation_id)
                 └─> good ─> good_child     (independent branch, must complete)
    """
    _bootstrap_silver(tmp_path)
    nodes = [
        {"id": "trigger", "node_type": "trigger.evidence_changed", "params": {}},
        # Failing branch: action.assign_owner requires violation_id -> raises.
        {"id": "bad", "node_type": "action.assign_owner", "params": {"assignee": "alice"}},
        {"id": "bad_child", "node_type": "action.snapshot", "params": {"reason": "after_bad"}},
        # Independent healthy branch.
        {
            "id": "good",
            "node_type": "check.evidence_exists",
            "params": {"control_id": "SOC2-CC6.1", "minimum": 1},
        },
        {"id": "good_child", "node_type": "action.snapshot", "params": {"reason": "after_good"}},
    ]
    edges = [
        {"source": "trigger", "target": "bad"},
        {"source": "bad", "target": "bad_child"},
        {"source": "trigger", "target": "good"},
        {"source": "good", "target": "good_child"},
    ]
    saved = save_workflow(
        tmp_path,
        workflow_id=None,
        name="branch isolation",
        description="",
        nodes=nodes,
        edges=edges,
    )

    run = run_workflow(tmp_path, workflow_id=saved["workflow_id"])
    by_id = {r["node_id"]: r for r in run["node_results"]}

    # The failing node errors, surfacing only a safe failure category (the
    # exception class name) — never the raw exception text, which can leak
    # internal paths or lake contents at the HTTP boundary.
    assert by_id["bad"]["result"] == "error"
    assert by_id["bad"]["error"] == "node execution failed (ValueError)"

    # Its descendant is skipped with an upstream reason.
    assert by_id["bad_child"]["result"] == "skipped"
    assert by_id["bad_child"]["reason"] == "upstream node bad did not complete"

    # The independent branch is unaffected and completes.
    assert by_id["trigger"]["result"] == "ok"
    assert by_id["good"]["result"] == "ok"
    assert by_id["good_child"]["result"] == "ok"
    assert by_id["good_child"]["output"]["snapshot_path"].endswith(".json")


def test_overall_run_result_is_error_when_a_node_fails(tmp_path: Path) -> None:
    _bootstrap_silver(tmp_path)
    nodes = [
        {"id": "trigger", "node_type": "trigger.evidence_changed", "params": {}},
        {"id": "bad", "node_type": "action.assign_owner", "params": {"assignee": "alice"}},
        {
            "id": "good",
            "node_type": "check.evidence_exists",
            "params": {"control_id": "SOC2-CC6.1", "minimum": 1},
        },
    ]
    edges = [
        {"source": "trigger", "target": "bad"},
        {"source": "trigger", "target": "good"},
    ]
    saved = save_workflow(
        tmp_path,
        workflow_id=None,
        name="error overall",
        description="",
        nodes=nodes,
        edges=edges,
    )

    run = run_workflow(tmp_path, workflow_id=saved["workflow_id"])
    assert run["result"] == "error"
    by_id = {r["node_id"]: r for r in run["node_results"]}
    assert by_id["good"]["result"] == "ok"  # branch still ran despite sibling error


def test_descendants_chain_blocks_transitively(tmp_path: Path) -> None:
    """A blocked node propagates the skip to its own descendants."""
    _bootstrap_silver(tmp_path)
    nodes = [
        {"id": "bad", "node_type": "action.assign_owner", "params": {"assignee": "alice"}},
        {"id": "child", "node_type": "action.snapshot", "params": {"reason": "c"}},
        {"id": "grandchild", "node_type": "action.snapshot", "params": {"reason": "gc"}},
    ]
    edges = [
        {"source": "bad", "target": "child"},
        {"source": "child", "target": "grandchild"},
    ]
    saved = save_workflow(tmp_path, workflow_id=None, name="chain", description="", nodes=nodes, edges=edges)

    run = run_workflow(tmp_path, workflow_id=saved["workflow_id"])
    by_id = {r["node_id"]: r for r in run["node_results"]}
    assert by_id["bad"]["result"] == "error"
    assert by_id["child"]["result"] == "skipped"
    assert by_id["child"]["reason"] == "upstream node bad did not complete"
    assert by_id["grandchild"]["result"] == "skipped"
    assert by_id["grandchild"]["reason"] == "upstream node child did not complete"


def test_clean_linear_path_still_ok(tmp_path: Path) -> None:
    _bootstrap_silver(tmp_path)
    nodes = [
        {"id": "n1", "node_type": "trigger.evidence_changed", "params": {}},
        {
            "id": "n2",
            "node_type": "check.evidence_exists",
            "params": {"control_id": "SOC2-CC6.1", "minimum": 1},
        },
        {"id": "n3", "node_type": "action.snapshot", "params": {"reason": "ok_path"}},
    ]
    edges = [
        {"source": "n1", "target": "n2"},
        {"source": "n2", "target": "n3"},
    ]
    saved = save_workflow(tmp_path, workflow_id=None, name="linear", description="", nodes=nodes, edges=edges)

    run = run_workflow(tmp_path, workflow_id=saved["workflow_id"])
    assert run["result"] == "ok"
    assert [r["result"] for r in run["node_results"]] == ["ok", "ok", "ok"]
