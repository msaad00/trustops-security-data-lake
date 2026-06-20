"""Typed TrustOps tools exposed to the optional agent harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from security_lakehouse.assessment import build_current_posture
from security_lakehouse.data_policy import redact_payload
from security_lakehouse.io import read_jsonl


def load_redacted_posture(lake_dir: str | Path, *, role: str) -> dict[str, Any]:
    """Read current posture through the same role redaction used by the API."""
    posture = build_current_posture(Path(lake_dir))
    redacted = redact_payload(posture, role=role)
    return redacted if isinstance(redacted, dict) else {}


def load_evidence_gaps(lake_dir: str | Path, *, role: str) -> list[dict[str, Any]]:
    """Return controls with missing, stale, or expired evidence."""
    rows = read_jsonl(Path(lake_dir) / "gold" / "control_tests.jsonl", missing_ok=True)
    gaps: list[dict[str, Any]] = []
    for row in rows:
        missing = row.get("missing_evidence_types") or []
        stale = row.get("stale_evidence_types") or []
        expired = row.get("expired_evidence_types") or []
        if not (missing or stale or expired):
            continue
        gap = {
            "control_id": row.get("control_id"),
            "framework": row.get("framework"),
            "status": row.get("status"),
            "owner": row.get("owner"),
            "missing_evidence_types": missing,
            "stale_evidence_types": stale,
            "expired_evidence_types": expired,
            "freshness_status": row.get("freshness_status"),
        }
        redacted = redact_payload(gap, role=role)
        if isinstance(redacted, dict):
            gaps.append(redacted)
    return gaps


def propose_evidence_gap_actions(gaps: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    """Build deterministic, approval-required action proposals."""
    proposals: list[dict[str, Any]] = []
    for gap in gaps[:limit]:
        control_id = str(gap.get("control_id") or "")
        missing = gap.get("missing_evidence_types") or []
        stale = gap.get("stale_evidence_types") or []
        expired = gap.get("expired_evidence_types") or []
        reason_parts = []
        if missing:
            reason_parts.append(f"missing {', '.join(str(item) for item in missing)}")
        if stale:
            reason_parts.append(f"stale {', '.join(str(item) for item in stale)}")
        if expired:
            reason_parts.append(f"expired {', '.join(str(item) for item in expired)}")
        proposals.append(
            {
                "action": "create_evidence_request",
                "control_id": control_id,
                "reason": "; ".join(reason_parts) or "evidence gap",
                "requires_approval": True,
                "status": "proposed",
            }
        )
    return proposals
