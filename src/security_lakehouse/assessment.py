"""Continuous compliance assessment engine.

The security data lake pipeline creates evidence and analytics tables. This module turns
those artifacts into product-level assessment state:

- current posture: continuously refreshed answer to "are we compliant now?"
- point-in-time snapshot: immutable assessment export for audits or JIT reviews
- violations: control and asset failures requiring owner action
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.evidence_freshness import (
    build_evidence_freshness,
    stale_control_ids,
    summarize_source_freshness,
)
from security_lakehouse.io import read_jsonl, write_json
from security_lakehouse.models import utc_iso

VIOLATION_STATUSES = {"open", "failed", "blocked", "noncompliant"}


def build_current_posture(
    lake_dir: str | Path,
    *,
    freshness_days: int = 7,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the continuously refreshed compliance posture from lake artifacts."""
    lake = Path(lake_dir)
    evaluated_at = now or datetime.now(UTC)
    events = read_jsonl(lake / "silver" / "normalized_events.jsonl", missing_ok=True)
    controls = read_jsonl(lake / "gold" / "control_posture.jsonl", missing_ok=True)
    assets = read_jsonl(lake / "gold" / "asset_risk.jsonl", missing_ok=True)
    violations = _build_violations(events)
    evidence_freshness = build_evidence_freshness(
        events,
        now=evaluated_at,
        default_slo_minutes=freshness_days * 24 * 60,
    )
    stale_controls = stale_control_ids(evidence_freshness)
    stale_evidence = [row for row in evidence_freshness if row["status"] in {"stale", "expired", "missing"}]
    framework_scores = _framework_scores(controls, violations, stale_controls)
    open_violations = [item for item in violations if item["state"] == "open"]
    critical_violations = [item for item in open_violations if item["severity"] == "critical"]
    high_violations = [item for item in open_violations if item["severity"] == "high"]
    posture_score = _weighted_posture_score(framework_scores)
    assessment = {
        "schema_version": "trustops.assessment.v1",
        "assessment_type": "current_posture",
        "evaluated_at": utc_iso(evaluated_at),
        "freshness_days": freshness_days,
        "posture": {
            "score": posture_score,
            "state": _posture_state(posture_score, critical_violations, stale_controls),
            "framework_count": len(framework_scores),
            "control_count": len(controls),
            "asset_count": len(assets),
            "open_violation_count": len(open_violations),
            "critical_violation_count": len(critical_violations),
            "high_violation_count": len(high_violations),
            "stale_control_count": len(stale_controls),
            "stale_evidence_count": len(stale_evidence),
        },
        "frameworks": framework_scores,
        "violations": open_violations,
        "top_risk_assets": assets[:10],
        "stale_controls": sorted(stale_controls),
        "evidence_freshness": {
            "count": len(evidence_freshness),
            "stale_count": len(stale_evidence),
            "sources": summarize_source_freshness(evidence_freshness),
            "stale_evidence": stale_evidence[:50],
        },
    }
    assessment["assessment_hash"] = _assessment_hash(assessment)
    return assessment


def write_current_posture(lake_dir: str | Path, *, freshness_days: int = 7) -> Path:
    """Write current posture into the gold zone."""
    lake = Path(lake_dir)
    output = lake / "gold" / "current_posture.json"
    write_json(output, build_current_posture(lake, freshness_days=freshness_days))
    return output


def write_assessment_snapshot(
    lake_dir: str | Path,
    *,
    output: str | Path | None = None,
    freshness_days: int = 7,
    reason: str = "manual",
) -> Path:
    """Write a point-in-time assessment snapshot for audit/JIT review."""
    lake = Path(lake_dir)
    assessment = build_current_posture(lake, freshness_days=freshness_days)
    assessment["assessment_type"] = "point_in_time_snapshot"
    assessment["snapshot_reason"] = reason
    assessment["assessment_hash"] = _assessment_hash(assessment)
    if output is None:
        ts = assessment["evaluated_at"].replace(":", "").replace("-", "")
        output_path = lake / "gold" / "snapshots" / f"assessment-{ts}.json"
    else:
        output_path = Path(output)
    write_json(output_path, assessment)
    return output_path


def _build_violations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for event in events:
        if event["status"] not in VIOLATION_STATUSES:
            continue
        for control_id in event["control_ids"]:
            violations.append(
                {
                    "violation_id": f"{control_id}:{event['event_id']}",
                    "control_id": control_id,
                    "event_id": event["event_id"],
                    "asset_id": event["asset_id"],
                    "asset_owner": event["asset_owner"],
                    "environment": event["environment"],
                    "source": event["source"],
                    "event_type": event["event_type"],
                    "severity": event["severity"],
                    "severity_score": event["severity_score"],
                    "state": "open",
                    "evidence_ref": event["evidence_ref"],
                    "raw_sha256": event["raw_sha256"],
                    "detected_at": event["event_time"],
                }
            )
    return sorted(violations, key=lambda item: (-int(item["severity_score"]), item["control_id"], item["event_id"]))


def _framework_scores(
    controls: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    stale_controls: set[str],
) -> list[dict[str, Any]]:
    violations_by_control: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for violation in violations:
        violations_by_control[violation["control_id"]].append(violation)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for control in controls:
        grouped[control["framework"]].append(control)

    rows: list[dict[str, Any]] = []
    for framework, framework_controls in grouped.items():
        total = len(framework_controls)
        failing = [control for control in framework_controls if control["status"] == "fail"]
        stale = [control for control in framework_controls if control["control_id"] in stale_controls]
        framework_violations = [
            v for control in framework_controls for v in violations_by_control.get(control["control_id"], [])
        ]
        risk_penalty = sum(min(int(v["severity_score"]), 100) for v in framework_violations)
        max_penalty = max(1, total * 100)
        score = max(0, round(100 - ((risk_penalty / max_penalty) * 100) - (len(stale) * 5), 2))
        rows.append(
            {
                "framework": framework,
                "score": score,
                "state": "ready" if not failing and not stale else "attention_required",
                "control_count": total,
                "failing_control_count": len(failing),
                "violation_count": len(framework_violations),
                "stale_control_count": len(stale),
                "critical_violation_count": sum(1 for v in framework_violations if v["severity"] == "critical"),
                "high_violation_count": sum(1 for v in framework_violations if v["severity"] == "high"),
            }
        )
    return sorted(rows, key=lambda item: (float(item["score"]), item["framework"]))


def _weighted_posture_score(frameworks: list[dict[str, Any]]) -> float:
    if not frameworks:
        return 100.0
    controls = sum(int(row["control_count"]) for row in frameworks)
    if controls <= 0:
        return 100.0
    total = sum(float(row["score"]) * int(row["control_count"]) for row in frameworks)
    return round(total / controls, 2)


def _posture_state(score: float, critical_violations: list[dict[str, Any]], stale_controls: set[str]) -> str:
    if critical_violations:
        return "critical"
    if score < 75 or stale_controls:
        return "attention_required"
    return "ready"


def _assessment_hash(assessment: dict[str, Any]) -> str:
    body = {key: value for key, value in assessment.items() if key != "assessment_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
