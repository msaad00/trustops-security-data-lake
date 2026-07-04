"""Stale evidence SLA workflows — escalate breaches into remediation tasks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from security_lakehouse.db import remediation
from security_lakehouse.evidence_freshness import STALE_STATUSES, build_freshness_summary
from security_lakehouse.io import read_jsonl


def load_freshness_records(lake_dir: str) -> list[dict[str, Any]]:
    from pathlib import Path

    lake = Path(lake_dir)
    return read_jsonl(lake / "gold" / "evidence_freshness.jsonl", missing_ok=True, base_dir=lake)


def escalate_stale_evidence(
    session: Session,
    *,
    tenant_id: str,
    lake_dir: str,
    actor_email: str,
    statuses: set[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Create remediation tasks for stale/expired/missing evidence rows."""
    allowed = statuses or set(STALE_STATUSES)
    records = load_freshness_records(lake_dir)
    summary = build_freshness_summary(records)
    candidates = [
        row
        for row in records
        if str(row.get("status") or "") in allowed and str(row.get("status") or "") in STALE_STATUSES
    ]
    candidates.sort(key=lambda row: (str(row.get("status")), -(row.get("age_minutes") or 0)))
    created: list[dict[str, Any]] = []
    skipped = 0
    due_at = datetime.now(UTC) + timedelta(days=7)
    for row in candidates[: max(1, min(limit, 100))]:
        source = str(row.get("source") or "unknown")
        status = str(row.get("status") or "stale")
        control_ids = [str(item) for item in (row.get("control_ids") or []) if str(item)]
        control_id = control_ids[0] if control_ids else None
        title = f"Refresh {status} {source} evidence"
        description = "\n".join(
            filter(
                None,
                [
                    str(row.get("reason") or ""),
                    str(row.get("next_action") or ""),
                    f"event_id={row.get('event_id')}",
                    f"evidence_ref={row.get('evidence_ref')}",
                ],
            )
        )
        existing = remediation.list_tasks(session, tenant_id=tenant_id, limit=500)
        if any(t.title == title and t.status in {"open", "in_progress"} for t in existing):
            skipped += 1
            continue
        priority = "high" if status in {"expired", "missing"} else "medium"
        task = remediation.create_task(
            session,
            tenant_id=tenant_id,
            title=title,
            description=description,
            control_id=control_id,
            owner="",
            priority=priority,
            due_at=due_at,
            created_by=actor_email,
        )
        created.append(remediation.task_to_dict(task))
    return {
        "created_count": len(created),
        "skipped_duplicates": skipped,
        "sla_breach_count": summary["sla_breach_count"],
        "tasks": created,
    }


__all__ = ["escalate_stale_evidence", "load_freshness_records"]
