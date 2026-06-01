"""save_workflow rejects structurally invalid workflow graphs."""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse.workflows import save_workflow


def _nodes() -> list[dict]:
    return [
        {"id": "n1", "node_type": "trigger.evidence_changed", "params": {}},
        {"id": "n2", "node_type": "action.snapshot", "params": {"reason": "test"}},
    ]


def _save(tmp_path: Path, nodes: list[dict], edges: list[dict]):
    return save_workflow(tmp_path, workflow_id=None, name="wf", description="", nodes=nodes, edges=edges)


def test_valid_dag_saves(tmp_path: Path) -> None:
    record = _save(tmp_path, _nodes(), [{"source": "n1", "target": "n2"}])
    assert record["version"] == 1


def test_cycle_is_rejected(tmp_path: Path) -> None:
    edges = [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n1"}]
    with pytest.raises(ValueError, match="acyclic"):
        _save(tmp_path, _nodes(), edges)


def test_unknown_node_type_is_rejected(tmp_path: Path) -> None:
    nodes = [{"id": "n1", "node_type": "action.does_not_exist", "params": {}}]
    with pytest.raises(ValueError, match="unknown node_type"):
        _save(tmp_path, nodes, [])


def test_duplicate_node_id_is_rejected(tmp_path: Path) -> None:
    nodes = [
        {"id": "dup", "node_type": "trigger.evidence_changed", "params": {}},
        {"id": "dup", "node_type": "action.snapshot", "params": {"reason": "x"}},
    ]
    with pytest.raises(ValueError, match="duplicate node ids"):
        _save(tmp_path, nodes, [])


def test_missing_node_id_is_rejected(tmp_path: Path) -> None:
    nodes = [{"id": "", "node_type": "action.snapshot", "params": {}}]
    with pytest.raises(ValueError, match="non-empty 'id'"):
        _save(tmp_path, nodes, [])


def test_edge_to_unknown_node_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a node id"):
        _save(tmp_path, _nodes(), [{"source": "n1", "target": "ghost"}])
