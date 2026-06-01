"""Workflow (story) DAG + action library + persistence.

A workflow is a directed acyclic graph of typed actions that runs against
the lake. The library aims for Tines-grade UX: every node has a published
input/output schema, can be tested live with sample data, and the whole
DAG is versioned + persisted append-only.

Persistence
-----------
* ``gold/workflows.jsonl``     — append-only workflow versions; each line
  is a full snapshot (``workflow_id``, ``version``, ``nodes``, ``edges``,
  ``actor``, ``occurred_at``). The latest version per id is materialized
  on read.
* ``gold/workflow_runs.jsonl`` — append-only execution log; each line is
  one whole-DAG run with per-node results.

Action library (PR 6 ships six; the registry is the extension point):

  trigger.evidence_changed     fires when new silver events land
  trigger.cron                 fires on a cron schedule (informational)
  check.evidence_exists        passes when N silver events match a filter
  check.control_pass           passes when a control_id's latest test is "pass"
  action.snapshot              freezes a point-in-time assessment snapshot
  action.assign_owner          appends a triage event with assignee + state

Every action declares its input schema (the params the user fills in) and
its output schema (the keys downstream nodes can read), so the canvas can
validate edge wiring and the "Test action" button can render a form +
display the live result.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.assessment import write_assessment_snapshot
from security_lakehouse.io import read_jsonl
from security_lakehouse.tracking import append_event as append_triage_event

WORKFLOWS_FILE = "workflows.jsonl"
RUNS_FILE = "workflow_runs.jsonl"

_RUN_ACTORS = {"console", "scheduler", "api"}


# ---------------------------------------------------------------------------
# Action library
# ---------------------------------------------------------------------------


def _evidence_changed(_lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger_kind": "evidence_changed",
        "since": params.get("since"),
        "matched": True,
    }


def _cron(_lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    return {"trigger_kind": "cron", "schedule": params.get("schedule") or "@hourly"}


def _check_evidence_exists(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    control_id = str(params.get("control_id") or "")
    minimum = int(params.get("minimum") or 1)
    silver = lake / "silver" / "normalized_events.jsonl"
    matched = 0
    if silver.is_file():
        for row in read_jsonl(silver):
            if control_id and control_id not in (row.get("control_ids") or []):
                continue
            matched += 1
    return {"matched_count": matched, "passed": matched >= minimum, "minimum": minimum}


def _check_control_pass(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    control_id = str(params.get("control_id") or "")
    tests = lake / "gold" / "control_tests.jsonl"
    if not tests.is_file():
        return {"control_id": control_id, "passed": False, "reason": "no control_tests.jsonl"}
    rows = [r for r in read_jsonl(tests) if r.get("control_id") == control_id]
    if not rows:
        return {"control_id": control_id, "passed": False, "reason": "control not found"}
    rows.sort(key=lambda r: str(r.get("evaluated_at") or ""), reverse=True)
    latest = rows[0]
    return {
        "control_id": control_id,
        "passed": latest.get("result") == "pass",
        "result": latest.get("result"),
        "confidence_score": latest.get("confidence_score"),
    }


def _action_snapshot(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    reason = str(params.get("reason") or "workflow_run")
    path = write_assessment_snapshot(lake, reason=reason)
    return {"snapshot_path": str(path), "reason": reason}


def _action_assign_owner(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    violation_id = str(params.get("violation_id") or "")
    assignee = str(params.get("assignee") or "")
    if not violation_id:
        raise ValueError("violation_id is required")
    record = append_triage_event(
        lake,
        violation_id=violation_id,
        actor=str(params.get("actor") or "workflow"),
        state=str(params.get("state") or "triaged"),
        assignee=assignee or None,
        due_at=params.get("due_at"),
        note=params.get("note") or "auto-assigned by workflow",
    )
    return {"violation_id": violation_id, "assignee": assignee, "tracking_id": record["tracking_id"]}


ACTION_LIBRARY: dict[str, dict[str, Any]] = {
    "trigger.evidence_changed": {
        "kind": "trigger",
        "label": "Evidence changed",
        "description": "Fires when new silver-layer evidence lands in the lake.",
        "input_schema": {"since": {"type": "string", "label": "Since (ISO 8601)", "optional": True}},
        "output_schema": {"trigger_kind": "string", "since": "string", "matched": "boolean"},
        "handler": _evidence_changed,
    },
    "trigger.cron": {
        "kind": "trigger",
        "label": "Cron schedule",
        "description": "Fires on a cron schedule (canvas-only; the runner is not wired yet).",
        "input_schema": {"schedule": {"type": "string", "label": "Cron expression", "default": "@hourly"}},
        "output_schema": {"trigger_kind": "string", "schedule": "string"},
        "handler": _cron,
    },
    "check.evidence_exists": {
        "kind": "check",
        "label": "Evidence exists",
        "description": "Passes when at least N silver-layer events match the given control_id.",
        "input_schema": {
            "control_id": {"type": "string", "label": "Control id", "required": True},
            "minimum": {"type": "number", "label": "Minimum count", "default": 1},
        },
        "output_schema": {"matched_count": "number", "passed": "boolean", "minimum": "number"},
        "handler": _check_evidence_exists,
    },
    "check.control_pass": {
        "kind": "check",
        "label": "Control passes",
        "description": "Passes when the latest control test for this control_id is 'pass'.",
        "input_schema": {"control_id": {"type": "string", "label": "Control id", "required": True}},
        "output_schema": {
            "control_id": "string",
            "passed": "boolean",
            "result": "string",
            "confidence_score": "number",
        },
        "handler": _check_control_pass,
    },
    "action.snapshot": {
        "kind": "action",
        "label": "Freeze snapshot",
        "description": "Writes a point-in-time assessment snapshot to gold/snapshots/.",
        "input_schema": {"reason": {"type": "string", "label": "Reason", "default": "workflow_run"}},
        "output_schema": {"snapshot_path": "string", "reason": "string"},
        "handler": _action_snapshot,
    },
    "action.assign_owner": {
        "kind": "action",
        "label": "Assign owner",
        "description": "Appends a triage event with an assignee for a violation_id.",
        "input_schema": {
            "violation_id": {"type": "string", "label": "Violation id", "required": True},
            "assignee": {"type": "string", "label": "Assignee", "required": True},
            "state": {"type": "string", "label": "State", "default": "triaged"},
            "note": {"type": "string", "label": "Note", "optional": True},
            "due_at": {"type": "string", "label": "Due (ISO 8601)", "optional": True},
        },
        "output_schema": {"violation_id": "string", "assignee": "string", "tracking_id": "string"},
        "handler": _action_assign_owner,
    },
}


def action_catalog() -> list[dict[str, Any]]:
    """Return the action library minus handler refs (the React canvas reads this)."""
    return [
        {
            "node_type": node_type,
            "kind": spec["kind"],
            "label": spec["label"],
            "description": spec["description"],
            "input_schema": spec["input_schema"],
            "output_schema": spec["output_schema"],
        }
        for node_type, spec in ACTION_LIBRARY.items()
    ]


def run_action(
    lake_dir: str | Path,
    *,
    node_type: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single action node against the lake and return its output."""
    spec = ACTION_LIBRARY.get(node_type)
    if spec is None:
        raise ValueError(f"unknown node_type {node_type!r}")
    handler = spec["handler"]
    return handler(Path(lake_dir), params or {})


# ---------------------------------------------------------------------------
# Workflow persistence
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def _read_log(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _slugify(text: str) -> str:
    clean = "".join(c if c.isalnum() or c in "-_" else "-" for c in text.lower())
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-") or "workflow"


def _validate_workflow_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    """Reject structurally invalid workflows before they are persisted.

    Guards against unknown node types, missing/duplicate node ids, edges that
    reference non-existent nodes, and cycles. A saved workflow is therefore
    always a runnable DAG over known actions, rather than failing opaquely (or
    running in a nondeterministic order) at execution time.
    """
    if not isinstance(edges, list):
        raise ValueError("workflow edges must be a list")
    ids: list[str] = []
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            raise ValueError("every workflow node requires a non-empty 'id'")
        node_type = str(node.get("node_type") or "")
        if node_type not in ACTION_LIBRARY:
            raise ValueError(f"unknown node_type {node_type!r} for node {node_id!r}")
        ids.append(node_id)
    id_set = set(ids)
    if len(id_set) != len(ids):
        duplicates = sorted({nid for nid in ids if ids.count(nid) > 1})
        raise ValueError(f"duplicate node ids: {duplicates}")

    incoming: dict[str, list[str]] = {nid: [] for nid in id_set}
    outgoing: dict[str, list[str]] = {nid: [] for nid in id_set}
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in id_set:
            raise ValueError(f"edge source {source!r} is not a node id")
        if target not in id_set:
            raise ValueError(f"edge target {target!r} is not a node id")
        incoming[target].append(source)
        outgoing[source].append(target)

    # Kahn's algorithm: if any node never reaches in-degree 0, a cycle exists.
    indegree = {nid: len(parents) for nid, parents in incoming.items()}
    ready = [nid for nid, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        nid = ready.pop()
        visited += 1
        for child in outgoing[nid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(id_set):
        raise ValueError("workflow graph must be acyclic (a cycle was detected)")


def save_workflow(
    lake_dir: str | Path,
    *,
    workflow_id: str | None,
    name: str,
    description: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    actor: str = "console",
) -> dict[str, Any]:
    """Append a new version of a workflow (auto-generates workflow_id if absent)."""
    if not name:
        raise ValueError("workflow name is required")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("workflow must declare at least one node")
    _validate_workflow_graph(nodes, edges)
    workflow_id = workflow_id or _slugify(name)
    existing = list_workflows(lake_dir)
    versions = [w for w in existing if w["workflow_id"] == workflow_id]
    version = (max(int(v.get("version") or 0) for v in versions) + 1) if versions else 1
    record = {
        "workflow_id": workflow_id,
        "version": version,
        "name": name,
        "description": description,
        "nodes": nodes,
        "edges": edges,
        "actor": actor,
        "occurred_at": _utc_now_iso(),
        "hash": hashlib.sha256(
            json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
    }
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    with (gold / WORKFLOWS_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def list_workflows(lake_dir: str | Path) -> list[dict[str, Any]]:
    """Return the latest version per workflow_id, newest-saved first."""
    rows = _read_log(_gold(lake_dir) / WORKFLOWS_FILE)
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        wid = str(row.get("workflow_id") or "")
        if not wid:
            continue
        prev = latest.get(wid)
        if prev is None or int(row.get("version") or 0) > int(prev.get("version") or 0):
            latest[wid] = row
    return sorted(latest.values(), key=lambda r: str(r.get("occurred_at") or ""), reverse=True)


def get_workflow(lake_dir: str | Path, workflow_id: str) -> dict[str, Any] | None:
    for w in list_workflows(lake_dir):
        if w["workflow_id"] == workflow_id:
            return w
    return None


_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\.output\.([A-Za-z0-9_]+)\s*\}\}")


def _substitute_variables(
    params: dict[str, Any],
    outputs_by_node: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Replace ``{{nodeId.output.field}}`` references in string params."""

    def resolve(value: Any) -> Any:
        if isinstance(value, str):

            def repl(match: re.Match[str]) -> str:
                node_id = match.group(1)
                field = match.group(2)
                source = outputs_by_node.get(node_id)
                if not source:
                    return match.group(0)
                replacement = source.get(field)
                if replacement is None:
                    return ""
                return str(replacement)

            return _VAR_RE.sub(repl, value)
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        return value

    return {k: resolve(v) for k, v in params.items()}


def _edge_allows(edge: dict[str, Any], parent_result: dict[str, Any] | None) -> bool:
    """Return True if `edge` should fire given the parent node's run result."""
    condition = str(edge.get("condition") or "always").lower()
    if condition == "always":
        return True
    if parent_result is None or parent_result.get("result") != "ok":
        return False
    output = parent_result.get("output") or {}
    passed = bool(output.get("passed"))
    if condition == "passed":
        return passed
    if condition == "failed":
        return not passed
    return True


def run_workflow(
    lake_dir: str | Path,
    *,
    workflow_id: str,
    actor: str = "console",
) -> dict[str, Any]:
    """Execute every node in a workflow (topological order) and persist the run.

    Variable references ``{{nodeId.output.field}}`` in params are substituted
    from upstream node outputs before each action runs. Edges with
    ``condition: "passed"|"failed"`` gate the target node based on the parent
    check's ``output.passed`` boolean.
    """
    if actor not in _RUN_ACTORS:
        actor = "console"
    workflow = get_workflow(lake_dir, workflow_id)
    if workflow is None:
        raise ValueError(f"unknown workflow_id {workflow_id!r}")
    nodes_by_id = {str(n.get("id")): n for n in workflow["nodes"]}
    edges: list[dict[str, Any]] = list(workflow.get("edges") or [])
    parents: dict[str, list[dict[str, Any]]] = {nid: [] for nid in nodes_by_id}
    incoming: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for edge in edges:
        src = str(edge.get("source"))
        dst = str(edge.get("target"))
        if dst in incoming:
            incoming[dst].append(src)
            parents[dst].append(edge)
    order = _topo_sort(nodes_by_id, incoming)
    started_at = _utc_now_iso()
    node_results: list[dict[str, Any]] = []
    outputs_by_node: dict[str, dict[str, Any]] = {}
    results_by_node: dict[str, dict[str, Any]] = {}
    failed = False
    for node_id in order:
        node = nodes_by_id[node_id]
        node_type = str(node.get("node_type") or "")
        raw_params = node.get("params") or {}
        # Gate on incoming edge conditions: skip the node if *any* parent
        # edge declines (failed condition with the parent's `passed=true`,
        # or vice versa). This mirrors how Tines edges flow conditionally.
        skip_reason: str | None = None
        for edge in parents.get(node_id, []):
            parent_id = str(edge.get("source"))
            parent_result = results_by_node.get(parent_id)
            if not _edge_allows(edge, parent_result):
                condition = str(edge.get("condition") or "always")
                skip_reason = f"edge from {parent_id} declined (condition={condition})"
                break
        if skip_reason:
            entry = {
                "node_id": node_id,
                "node_type": node_type,
                "params": raw_params,
                "result": "skipped",
                "reason": skip_reason,
            }
            node_results.append(entry)
            results_by_node[node_id] = entry
            continue
        params = _substitute_variables(raw_params, outputs_by_node)
        result_entry: dict[str, Any] = {
            "node_id": node_id,
            "node_type": node_type,
            "params": params,
        }
        try:
            output = run_action(lake_dir, node_type=node_type, params=params)
            result_entry["result"] = "ok"
            result_entry["output"] = output
            outputs_by_node[node_id] = output
        except Exception as exc:  # surface every failure in the run log
            failed = True
            result_entry["result"] = "error"
            result_entry["error"] = str(exc)
        node_results.append(result_entry)
        results_by_node[node_id] = result_entry
        if failed:
            break
    run = {
        "workflow_id": workflow_id,
        "workflow_version": workflow["version"],
        "actor": actor,
        "result": "error" if failed else "ok",
        "started_at": started_at,
        "finished_at": _utc_now_iso(),
        "node_results": node_results,
    }
    with (_gold(lake_dir) / RUNS_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run, separators=(",", ":")) + "\n")
    return run


def list_runs(lake_dir: str | Path, workflow_id: str | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = _read_log(_gold(lake_dir) / RUNS_FILE)
    if workflow_id:
        rows = [r for r in rows if r.get("workflow_id") == workflow_id]
    rows.sort(key=lambda r: str(r.get("started_at") or ""), reverse=True)
    return rows[:limit]


def _topo_sort(nodes_by_id: dict[str, dict], incoming: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm. Cycles fall back to insertion order so the run still attempts."""
    indeg = {nid: len(parents) for nid, parents in incoming.items()}
    ready = [nid for nid, n in indeg.items() if n == 0]
    order: list[str] = []
    seen: set[str] = set()
    # Outgoing index
    outgoing: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for child, parents in incoming.items():
        for parent in parents:
            if parent in outgoing:
                outgoing[parent].append(child)
    while ready:
        nid = ready.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        order.append(nid)
        for child in outgoing.get(nid, []):
            indeg[child] = max(0, indeg[child] - 1)
            if indeg[child] == 0:
                ready.append(child)
    # Append any cycle survivors so the workflow still runs partially.
    for nid in nodes_by_id:
        if nid not in seen:
            order.append(nid)
    return order
