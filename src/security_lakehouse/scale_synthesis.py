"""Audit-scale synthetic evidence generation and throughput benchmarks.

Generates millions of validated raw events for load testing ingestion,
evaluation, and posture rollups without live connectors. Events fan out across
the active control catalog with configurable open-finding ratios.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.io import write_jsonl_from_iterable
from security_lakehouse.models import SEVERITY_SCORE
from security_lakehouse.pipeline import run_pipeline

_EVENT_TYPES = (
    "cloud.config",
    "iam.access_review",
    "monitoring.audit",
    "monitoring.detection",
    "scm.branch_protection",
    "scanner.dependency",
    "model.lineage",
    "runtime.inference",
)
_SOURCES = ("aws_config", "okta", "github", "audit_log", "siem", "model_registry", "runtime_gateway")
_ASSET_TYPES = ("iam_role", "repository", "audit_trail", "database", "model", "agent", "data_store")
_OPEN_STATUSES = ("open", "failed", "blocked", "noncompliant")
_PASS_STATUSES = ("passed", "observed", "resolved")


def audit_scale_control_pool(*, framework_prefix: str | None = None) -> list[str]:
    """Return control IDs used for scale synthesis (defaults to full catalog)."""
    catalog = load_control_catalog()
    if framework_prefix:
        return sorted(control_id for control_id in catalog if control_id.startswith(framework_prefix))
    return sorted(catalog)


def synthesize_audit_event(
    *,
    index: int,
    tenant_id: str,
    control_ids: list[str],
    controls_per_event: int,
    open_ratio: float,
    base_time: datetime,
    rng: random.Random,
) -> dict[str, Any]:
    """Build one validated raw event with realistic control fan-out."""
    if not control_ids:
        raise ValueError("control_ids must not be empty")
    if controls_per_event < 1:
        raise ValueError("controls_per_event must be >= 1")

    status = rng.choice(_OPEN_STATUSES) if rng.random() < open_ratio else rng.choice(_PASS_STATUSES)
    severity = (
        "critical" if status in _OPEN_STATUSES and index % 17 == 0 else "high" if status in _OPEN_STATUSES else "info"
    )
    event_time = base_time + timedelta(seconds=index)
    collected = event_time + timedelta(seconds=1)
    asset_type = _ASSET_TYPES[index % len(_ASSET_TYPES)]
    source = _SOURCES[index % len(_SOURCES)]
    event_type = _EVENT_TYPES[index % len(_EVENT_TYPES)]
    picked = rng.sample(control_ids, k=min(controls_per_event, len(control_ids)))

    return {
        "tenant_id": tenant_id,
        "event_id": f"scale-{index:012d}",
        "event_time": event_time.isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "source": source,
        "severity": severity,
        "status": status,
        "entity": {
            "asset_id": f"scale:asset:{index:012d}",
            "asset_type": asset_type,
            "environment": "prod" if index % 3 else "staging",
            "owner": f"team-{(index % 12) + 1:02d}",
        },
        "controls": picked,
        "evidence": {
            "collected_at": collected.isoformat().replace("+00:00", "Z"),
            "evidence_id": f"ev-scale-{index:012d}",
            "uri": f"s3://scale-evidence/{source}/{index:012d}.json",
        },
        "attributes": {
            "fixture": "audit_scale",
            "synthetic": True,
            "severity_score": SEVERITY_SCORE[severity],
        },
    }


def iter_synthesize_audit_events(
    count: int,
    *,
    tenant_id: str = "audit-scale",
    controls_per_event: int = 2,
    open_ratio: float = 0.12,
    framework_prefix: str | None = None,
    seed: int = 42,
    base_time: datetime | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield ``count`` synthetic raw events without materializing the full list."""
    if count < 0:
        raise ValueError("count must be >= 0")
    if not 0 <= open_ratio <= 1:
        raise ValueError("open_ratio must be between 0 and 1")

    control_ids = audit_scale_control_pool(framework_prefix=framework_prefix)
    rng = random.Random(seed)
    base = (base_time or datetime(2026, 6, 30, 0, 0, 0, tzinfo=UTC)).astimezone(UTC)
    for index in range(count):
        yield synthesize_audit_event(
            index=index,
            tenant_id=tenant_id,
            control_ids=control_ids,
            controls_per_event=controls_per_event,
            open_ratio=open_ratio,
            base_time=base,
            rng=rng,
        )


def write_audit_scale_fixture(
    output: str | Path,
    count: int,
    *,
    tenant_id: str = "audit-scale",
    controls_per_event: int = 2,
    open_ratio: float = 0.12,
    framework_prefix: str | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Stream synthetic events to ``output`` and return generation metadata."""
    started = time.perf_counter()
    written = write_jsonl_from_iterable(
        output,
        iter_synthesize_audit_events(
            count,
            tenant_id=tenant_id,
            controls_per_event=controls_per_event,
            open_ratio=open_ratio,
            framework_prefix=framework_prefix,
            seed=seed,
        ),
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    control_pool = audit_scale_control_pool(framework_prefix=framework_prefix)
    return {
        "output": str(output),
        "event_count": written,
        "controls_per_event": controls_per_event,
        "open_ratio": open_ratio,
        "control_pool_size": len(control_pool),
        "estimated_open_events": round(written * open_ratio),
        "estimated_findings": round(written * open_ratio * controls_per_event),
        "duration_ms": elapsed_ms,
        "events_per_second": round(written / max(elapsed_ms / 1000, 0.001), 2),
    }


def benchmark_pipeline(
    raw_path: str | Path,
    out_dir: str | Path,
    *,
    tenant_id: str = "audit-scale",
) -> dict[str, Any]:
    """Run the lake pipeline and return timing + throughput metrics."""
    started = time.perf_counter()
    result = run_pipeline(raw_path, out_dir, tenant_id=tenant_id)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    events = result.raw_count
    return {
        "raw_path": str(raw_path),
        "out_dir": str(out_dir),
        "event_count": events,
        "silver_count": result.silver_count,
        "control_count": result.control_count,
        "asset_count": result.asset_count,
        "duration_ms": elapsed_ms,
        "events_per_second": round(events / max(elapsed_ms / 1000, 0.001), 2),
        "pipeline_result": result.__dict__,
    }


def audit_scale_plan(
    event_count: int,
    *,
    controls_per_event: int = 2,
    open_ratio: float = 0.12,
) -> dict[str, Any]:
    """Return projected finding cardinality for an audit-scale lake."""
    open_events = round(event_count * open_ratio)
    findings = open_events * controls_per_event
    return {
        "event_count": event_count,
        "controls_per_event": controls_per_event,
        "open_ratio": open_ratio,
        "projected_open_events": open_events,
        "projected_findings": findings,
        "recommended_posture_max_violations": min(10_000, max(1_000, findings // 100)),
        "warehouse_recommended_above_events": 100_000,
    }
