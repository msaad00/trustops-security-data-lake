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
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.evidence_freshness import (
    build_evidence_freshness,
    stale_control_ids,
    summarize_source_freshness,
)
from security_lakehouse.io import append_jsonl, read_jsonl, write_json
from security_lakehouse.models import utc_iso

VIOLATION_STATUSES = {"open", "failed", "blocked", "noncompliant"}

# Append-only ledger that chains every snapshot to its predecessor. Each line
# records (prev_hash -> assessment_hash); because assessment_hash covers
# prev_hash, mutating or dropping any historical snapshot breaks the chain.
SNAPSHOT_LEDGER = ("gold", "snapshots", "_ledger.jsonl")


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
    control_tests = read_jsonl(lake / "gold" / "control_tests.jsonl", missing_ok=True)
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
    failed_control_tests = [item for item in control_tests if str(item.get("result", "")).lower() == "fail"]
    warning_control_tests = [item for item in control_tests if str(item.get("result", "")).lower() == "warn"]
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
            "failed_control_test_count": len(failed_control_tests),
            "warning_control_test_count": len(warning_control_tests),
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


def _catalog_bundle_for_snapshot() -> dict[str, Any] | None:
    """Return the active catalog bundle, or None if no catalog is reachable.

    Snapshots taken in bare test lakes without a control catalog still succeed;
    they just record a null bundle rather than failing the freeze.
    """
    try:
        from security_lakehouse.catalog_versions import bundle_summary

        return bundle_summary()
    except (OSError, ValueError, KeyError):
        return None


def _ledger_path(lake_dir: str | Path) -> Path:
    return Path(lake_dir).joinpath(*SNAPSHOT_LEDGER)


def _chain_tip(lake_dir: str | Path) -> str | None:
    """Return the assessment_hash of the most recent ledgered snapshot.

    The ledger — not file mtime or ``evaluated_at`` — is the chain's source of
    truth, so two snapshots sharing a timestamp still chain deterministically.
    """
    entries = read_jsonl(_ledger_path(lake_dir), missing_ok=True)
    return entries[-1].get("assessment_hash") if entries else None


def write_assessment_snapshot(
    lake_dir: str | Path,
    *,
    output: str | Path | None = None,
    freshness_days: int = 7,
    reason: str = "manual",
) -> Path:
    """Write a point-in-time assessment snapshot for audit/JIT review.

    Each snapshot is linked to its predecessor via ``prev_hash`` and recorded
    in an append-only ledger, so a snapshot that is later mutated or deleted is
    detectable by :func:`verify_snapshot_chain`.
    """
    lake = Path(lake_dir)
    prev_hash = _chain_tip(lake)
    assessment = build_current_posture(lake, freshness_days=freshness_days)
    assessment["assessment_type"] = "point_in_time_snapshot"
    assessment["snapshot_reason"] = reason
    # Pin the catalog bundle (framework + control versions in force) so this
    # audit reproduces against the exact controls it was evaluated with. The
    # bundle is covered by assessment_hash below, so it is tamper-evident too.
    assessment["catalog_bundle"] = _catalog_bundle_for_snapshot()
    assessment["prev_hash"] = prev_hash
    # assessment_hash covers prev_hash, so the chain is tamper-evident.
    assessment["assessment_hash"] = _assessment_hash(assessment)
    if output is None:
        ts = assessment["evaluated_at"].replace(":", "").replace("-", "")
        # Suffix with the content hash so same-timestamp freezes never collide
        # and an existing immutable snapshot is never silently overwritten.
        short = assessment["assessment_hash"][:12]
        output_path = lake / "gold" / "snapshots" / f"assessment-{ts}-{short}.json"
        if output_path.exists():
            raise FileExistsError(f"snapshot already exists, refusing to overwrite: {output_path}")
    else:
        output_path = Path(output)
    write_json(output_path, assessment)
    append_jsonl(
        _ledger_path(lake),
        {
            "evaluated_at": assessment["evaluated_at"],
            "snapshot": output_path.name,
            "prev_hash": prev_hash,
            "assessment_hash": assessment["assessment_hash"],
            "snapshot_reason": reason,
            "recorded_at": utc_iso(datetime.now(UTC)),
        },
    )
    return output_path


def verify_snapshot_chain(lake_dir: str | Path) -> dict[str, Any]:
    """Verify the snapshot hash-chain against the append-only ledger.

    Walks the ledger oldest-first and, for each entry, confirms the referenced
    snapshot file exists, recomputes its ``assessment_hash`` from content, and
    checks that the recorded hash, the file's stored hash, and the ``prev_hash``
    linkage all agree. Returns ``{"ok", "length", "issues"}`` — ``ok`` is True
    only when the chain is intact and unbroken.
    """
    lake = Path(lake_dir)
    entries = read_jsonl(_ledger_path(lake), missing_ok=True)
    snapshots_dir = lake / "gold" / "snapshots"
    issues: list[str] = []
    expected_prev: str | None = None
    for index, entry in enumerate(entries):
        name = entry.get("snapshot")
        recorded_hash = entry.get("assessment_hash")
        if entry.get("prev_hash") != expected_prev:
            issues.append(f"entry {index} ({name}): prev_hash breaks the chain")
        path = snapshots_dir / name if isinstance(name, str) else None
        if path is None or not path.exists():
            issues.append(f"entry {index} ({name}): snapshot file is missing")
            expected_prev = recorded_hash
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            issues.append(f"entry {index} ({name}): snapshot file is unreadable")
            expected_prev = recorded_hash
            continue
        recomputed = _assessment_hash(payload)
        if recomputed != recorded_hash or payload.get("assessment_hash") != recorded_hash:
            issues.append(f"entry {index} ({name}): content hash does not match the ledger")
        expected_prev = recorded_hash
    return {"ok": not issues, "length": len(entries), "issues": issues}


def _parse_iso(value: str | datetime) -> datetime:
    """Parse an ISO date/datetime into a tz-aware UTC datetime.

    Accepts trailing ``Z``, naive values (assumed UTC), and bare dates
    (``2026-05-20`` -> start of that day). Raises ``ValueError`` on garbage so
    callers can surface a 400.
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if not text:
            raise ValueError("timestamp must not be empty")
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iter_snapshots(lake_dir: str | Path) -> list[tuple[datetime, dict[str, Any], Path]]:
    """Load assessment snapshots as ``(evaluated_at, payload, path)`` tuples.

    Snapshots with a missing/unparseable ``evaluated_at`` are skipped. The
    result is sorted oldest-first by ``evaluated_at``.
    """
    snapshots_dir = Path(lake_dir) / "gold" / "snapshots"
    if not snapshots_dir.is_dir():
        return []
    rows: list[tuple[datetime, dict[str, Any], Path]] = []
    for path in snapshots_dir.glob("assessment-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw = payload.get("evaluated_at")
        if not isinstance(raw, str):
            continue
        try:
            evaluated_at = _parse_iso(raw)
        except ValueError:
            continue
        rows.append((evaluated_at, payload, path))
    return sorted(rows, key=lambda item: item[0])


def list_snapshot_times(lake_dir: str | Path) -> list[str]:
    """Return the ``evaluated_at`` timestamps of all snapshots, oldest-first."""
    return [payload.get("evaluated_at") for _ts, payload, _path in _iter_snapshots(lake_dir)]


_SNAPSHOT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _is_safe_snapshot_token(token: str) -> bool:
    if not token or token in {".", ".."}:
        return False
    if Path(token).is_absolute():
        return False
    if "/" in token or "\\" in token:
        return False
    return bool(_SNAPSHOT_ID_RE.fullmatch(token))


def resolve_snapshot_path(lake_dir: str | Path, snapshot_id: str) -> Path | None:
    """Resolve a snapshot file by filename stem or ``assessment_hash`` prefix."""
    snapshots_dir = (Path(lake_dir) / "gold" / "snapshots").resolve()
    token = snapshot_id.strip()
    if not snapshots_dir.is_dir() or not _is_safe_snapshot_token(token):
        return None

    direct = (snapshots_dir / token).resolve()
    if direct.is_file() and (direct == snapshots_dir or snapshots_dir in direct.parents):
        return direct

    stem_path = (snapshots_dir / f"{token}.json").resolve()
    if stem_path.is_file() and (stem_path == snapshots_dir or snapshots_dir in stem_path.parents):
        return stem_path
    for path in snapshots_dir.glob("assessment-*.json"):
        if path.stem == token:
            return path
    for path in snapshots_dir.glob("assessment-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        digest = payload.get("assessment_hash")
        if isinstance(digest, str) and (digest == token or digest.startswith(token)):
            return path
    return None


def load_snapshot(lake_dir: str | Path, snapshot_id: str) -> dict[str, Any]:
    """Load a point-in-time snapshot payload by id."""
    path = resolve_snapshot_path(lake_dir, snapshot_id)
    if path is None:
        raise FileNotFoundError(f"snapshot not found: {snapshot_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def posture_as_of(lake_dir: str | Path, *, as_of: str | datetime) -> dict[str, Any]:
    """Return the posture from the most recent snapshot at/before ``as_of``.

    Walks the immutable point-in-time snapshots in ``gold/snapshots/`` and picks
    the newest one whose ``evaluated_at`` is ``<= as_of``. The returned object
    carries the snapshot's ``posture`` summary plus the snapshot's
    ``evaluated_at`` / ``assessment_hash`` and the ``requested_as_of`` echo.

    If no snapshot exists at/before ``as_of`` (or none exist at all), returns a
    null-posture result with ``available_from`` set to the earliest snapshot's
    ``evaluated_at`` (``None`` when there are no snapshots) so the caller can
    explain why the answer is empty.

    ``as_of`` may be a ``datetime`` or an ISO date/datetime string; an invalid
    string raises ``ValueError``.
    """
    requested = _parse_iso(as_of)
    requested_iso = utc_iso(requested)
    snapshots = _iter_snapshots(lake_dir)
    available_from = snapshots[0][1].get("evaluated_at") if snapshots else None

    selected: tuple[datetime, dict[str, Any], Path] | None = None
    for entry in snapshots:
        if entry[0] <= requested:
            selected = entry
        else:
            break

    if selected is None:
        return {
            "schema_version": "trustops.assessment.v1",
            "assessment_type": "point_in_time_query",
            "requested_as_of": requested_iso,
            "found": False,
            "evaluated_at": None,
            "assessment_hash": None,
            "available_from": available_from,
            "snapshot_count": len(snapshots),
            "posture": None,
        }

    _ts, payload, path = selected
    return {
        "schema_version": "trustops.assessment.v1",
        "assessment_type": "point_in_time_query",
        "requested_as_of": requested_iso,
        "found": True,
        "evaluated_at": payload.get("evaluated_at"),
        "assessment_hash": payload.get("assessment_hash"),
        "snapshot_reason": payload.get("snapshot_reason") or "manual",
        "snapshot_path": str(path),
        "available_from": available_from,
        "snapshot_count": len(snapshots),
        "posture": payload.get("posture"),
        "frameworks": payload.get("frameworks", []),
    }


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
