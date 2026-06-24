"""Repeatable product scenarios over the TrustOps lake.

Scenarios are thin orchestration around shipped primitives. They are meant to
prove end-to-end claims against fixtures, cloud shells, or live cloud accounts
without creating a second execution path.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from security_lakehouse.assessment import build_current_posture, verify_snapshot_chain, write_assessment_snapshot
from security_lakehouse.connector_runner import ConnectorSyncError, run_connector_sync
from security_lakehouse.connector_state import append_config_event
from security_lakehouse.io import read_jsonl, write_json
from security_lakehouse.verification import verify_lake_integrity
from security_lakehouse.workflows import run_workflow, save_workflow

LIVE_CLOUD_SCENARIO = "live-cloud-posture"
DEFAULT_LIVE_CONNECTORS = ("azure-posture", "aws-posture", "snowflake-evidence-lake")
SCENARIO_REPORT = ("gold", "scenario_reports", "live-cloud-posture.json")
SCENARIO_WORKFLOW_ID = "live-cloud-posture-freeze"


def parse_fixture_specs(values: list[str] | None) -> dict[str, str]:
    """Parse ``connector_id=path`` fixture specs from the CLI."""
    fixtures: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"fixture spec must be connector_id=path, got {raw!r}")
        connector_id, path = raw.split("=", 1)
        connector_id = connector_id.strip()
        path = path.strip()
        if not connector_id or not path:
            raise ValueError(f"fixture spec must be connector_id=path, got {raw!r}")
        fixtures[connector_id] = path
    return fixtures


def run_live_cloud_posture_scenario(
    lake_dir: str | Path,
    *,
    connectors: list[str] | tuple[str, ...] | None = None,
    fixture_dirs: dict[str, str] | None = None,
    actor: str = "scenario",
    continue_on_error: bool = False,
) -> dict[str, Any]:
    """Run a live-cloud posture scenario and return a durable report.

    The scenario:

    1. enables selected connectors,
    2. syncs them into the managed raw lake,
    3. verifies evidence integrity/idempotency,
    4. freezes a snapshot and verifies the snapshot chain,
    5. saves and runs a workflow DAG that freezes another snapshot when
       SOC2-CC6.1 evidence exists.
    """
    lake = Path(lake_dir)
    connector_ids = list(connectors or DEFAULT_LIVE_CONNECTORS)
    fixtures = fixture_dirs or {}
    syncs: list[dict[str, Any]] = []

    for connector_id in connector_ids:
        append_config_event(lake, connector_id=connector_id, state="enabled", actor=actor)
        try:
            result = run_connector_sync(
                lake,
                connector_id=connector_id,
                actor=actor,
                fixture_dir=fixtures.get(connector_id),
                materialize=True,
            )
            syncs.append({"connector_id": connector_id, "ok": True, **asdict(result)})
        except ConnectorSyncError as exc:
            entry = {
                "connector_id": connector_id,
                "ok": False,
                "error": str(exc),
                "run": exc.run,
            }
            syncs.append(entry)
            if not continue_on_error:
                report = _scenario_report(
                    lake,
                    actor=actor,
                    connectors=connector_ids,
                    syncs=syncs,
                    integrity=None,
                    snapshot=None,
                    snapshot_chain=None,
                    workflow=None,
                )
                _write_report(lake, report)
                raise

    integrity = verify_lake_integrity(lake)
    snapshot_path = write_assessment_snapshot(lake, reason=f"scenario:{LIVE_CLOUD_SCENARIO}")
    workflow = _run_scenario_workflow(lake, actor=actor)
    snapshot_chain = verify_snapshot_chain(lake)
    report = _scenario_report(
        lake,
        actor=actor,
        connectors=connector_ids,
        syncs=syncs,
        integrity=integrity,
        snapshot=str(snapshot_path),
        snapshot_chain=snapshot_chain,
        workflow=workflow,
    )
    _write_report(lake, report)
    return report


def _run_scenario_workflow(lake: Path, *, actor: str) -> dict[str, Any]:
    workflow = save_workflow(
        lake,
        workflow_id=SCENARIO_WORKFLOW_ID,
        name="Live cloud posture freeze",
        description="Freeze a snapshot when live cloud evidence for SOC2-CC6.1 exists.",
        actor=actor,
        nodes=[
            {
                "id": "evidence_changed",
                "node_type": "trigger.evidence_changed",
                "params": {},
            },
            {
                "id": "soc2_evidence",
                "node_type": "check.evidence_exists",
                "params": {"control_id": "SOC2-CC6.1", "minimum": 1},
            },
            {
                "id": "freeze_snapshot",
                "node_type": "action.snapshot",
                "params": {"reason": f"workflow:{LIVE_CLOUD_SCENARIO}"},
            },
        ],
        edges=[
            {"source": "evidence_changed", "target": "soc2_evidence"},
            {"source": "soc2_evidence", "target": "freeze_snapshot", "condition": "passed"},
        ],
    )
    run = run_workflow(lake, workflow_id=workflow["workflow_id"], actor="scheduler")
    return {"workflow": workflow, "run": run}


def _scenario_report(
    lake: Path,
    *,
    actor: str,
    connectors: list[str],
    syncs: list[dict[str, Any]],
    integrity: dict[str, Any] | None,
    snapshot: str | None,
    snapshot_chain: dict[str, Any] | None,
    workflow: dict[str, Any] | None,
) -> dict[str, Any]:
    posture = build_current_posture(lake)
    silver_rows = read_jsonl(lake / "silver" / "normalized_events.jsonl", missing_ok=True)
    workflow_ok = workflow is not None and (workflow.get("run") or {}).get("result") == "ok"
    chain_ok = snapshot_chain is not None and snapshot_chain.get("ok") is True
    return {
        "schema_version": "trustops.scenario_report.v1",
        "scenario": LIVE_CLOUD_SCENARIO,
        "actor": actor,
        "lake": str(lake),
        "connectors": connectors,
        "syncs": syncs,
        "summary": {
            "ok": all(row.get("ok") for row in syncs)
            and bool(integrity and integrity.get("ok"))
            and chain_ok
            and workflow_ok,
            "evidence_count": len(silver_rows),
            "sources": sorted({str(row.get("source") or "") for row in silver_rows if row.get("source")}),
            "posture_score": posture.get("posture", {}).get("score"),
            "posture_state": posture.get("posture", {}).get("state"),
            "open_violations": posture.get("posture", {}).get("open_violation_count"),
            "frameworks": posture.get("posture", {}).get("framework_count"),
        },
        "integrity": integrity,
        "snapshot": snapshot,
        "snapshot_chain": snapshot_chain,
        "workflow": workflow,
        "artifacts": {
            "raw": str(lake / "raw" / "connector_events.jsonl"),
            "bronze": str(lake / "bronze" / "raw_events.jsonl"),
            "silver": str(lake / "silver" / "normalized_events.jsonl"),
            "posture": str(lake / "gold" / "current_posture.json"),
            "integrity": str(lake / "gold" / "evidence_integrity.json"),
            "report": str(lake.joinpath(*SCENARIO_REPORT)),
        },
    }


def _write_report(lake: Path, report: dict[str, Any]) -> Path:
    path = lake.joinpath(*SCENARIO_REPORT)
    write_json(path, report)
    return path
