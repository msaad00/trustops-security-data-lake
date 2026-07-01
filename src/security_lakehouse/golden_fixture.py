"""Unified golden demo fixture for the console dashboard.

Ships one canonical mockup company (``golden``) whose raw evidence covers all
33 SOC 2 common-criteria controls plus four representative NIST AI RMF
subcategories — 37 controls total on the workbench dashboard without live
connectors.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.fixtures import FIXTURES_DIR
from security_lakehouse.validation import validate_raw_events

GOLDEN_COMPANY = "golden"
GOLDEN_TENANT_ID = "acme-golden"

GOLDEN_NIST_CONTROLS: tuple[str, ...] = (
    "NIST-AI-RMF-MAP-1.5",
    "NIST-AI-RMF-MEASURE-2.7",
    "NIST-AI-RMF-GOVERN-1.2",
    "NIST-AI-RMF-MANAGE-2.3",
)

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
_STATUSES = ("passed", "open", "passed", "open", "blocked", "passed", "open", "passed")


def golden_control_ids() -> list[str]:
    """Return the 37 control IDs the golden fixture is designed to populate."""
    catalog = load_control_catalog()
    soc2 = sorted(control_id for control_id in catalog if control_id.startswith("SOC2-"))
    missing = [control_id for control_id in GOLDEN_NIST_CONTROLS if control_id not in catalog]
    if missing:
        raise ValueError(f"golden fixture references unknown controls: {missing}")
    if len(soc2) != 33:
        raise ValueError(f"expected 33 SOC 2 controls in catalog, found {len(soc2)}")
    return soc2 + list(GOLDEN_NIST_CONTROLS)


def build_golden_events(
    *, tenant_id: str = GOLDEN_TENANT_ID, base_time: datetime | None = None
) -> list[dict[str, Any]]:
    """Synthesize one validated raw event per golden control ID."""
    base = (base_time or datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)).astimezone(UTC)
    rows: list[dict[str, Any]] = []
    for index, control_id in enumerate(golden_control_ids()):
        status = _STATUSES[index % len(_STATUSES)]
        severity = (
            "critical" if status in {"open", "blocked"} and index % 5 == 0 else "high" if status == "open" else "info"
        )
        event_time = base + timedelta(minutes=index)
        collected = event_time + timedelta(minutes=1)
        asset_type = _ASSET_TYPES[index % len(_ASSET_TYPES)]
        rows.append(
            {
                "tenant_id": tenant_id,
                "event_id": f"golden-{index + 1:03d}",
                "event_time": event_time.isoformat().replace("+00:00", "Z"),
                "event_type": _EVENT_TYPES[index % len(_EVENT_TYPES)],
                "source": _SOURCES[index % len(_SOURCES)],
                "severity": severity,
                "status": status,
                "entity": {
                    "asset_id": f"golden:asset:{control_id.lower()}",
                    "asset_type": asset_type,
                    "environment": "prod",
                    "owner": "security-platform",
                },
                "controls": [control_id],
                "evidence": {
                    "collected_at": collected.isoformat().replace("+00:00", "Z"),
                    "evidence_id": f"ev-golden-{index + 1:03d}",
                    "uri": f"s3://acme-golden-evidence/{control_id}/golden-{index + 1:03d}.json",
                },
                "attributes": {
                    "fixture": GOLDEN_COMPANY,
                    "control_id": control_id,
                    "demo": True,
                },
            }
        )
    errors = validate_raw_events(rows)
    if errors:
        raise ValueError("; ".join(errors))
    return rows


def golden_fixture_path(root: Path | None = None) -> Path:
    """Path to ``mockup_companies/golden/raw/security_events.jsonl``."""
    return (root or FIXTURES_DIR) / GOLDEN_COMPANY / "raw" / "security_events.jsonl"


def write_golden_fixture(*, root: Path | None = None) -> Path:
    """Write the golden JSONL fixture and return its path."""
    path = golden_fixture_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_golden_events()
    path.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
    return path


def golden_fixture_summary() -> dict[str, Any]:
    """Return control coverage metadata for CLI and tests."""
    control_ids = golden_control_ids()
    return {
        "company": GOLDEN_COMPANY,
        "tenant_id": GOLDEN_TENANT_ID,
        "control_count": len(control_ids),
        "soc2_control_count": 33,
        "nist_ai_control_count": len(GOLDEN_NIST_CONTROLS),
        "controls": control_ids,
    }
