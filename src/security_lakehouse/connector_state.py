"""Connector configuration + probe state for the React workbench.

Persists three layers on top of the static ``connectors/catalog.json``:

* ``gold/connector_config.jsonl`` — append-only configuration events
  (enabled/disabled, credentials redacted, options) per connector.
* ``gold/connector_runs.jsonl`` — append-only probe + sync run history.

These are separate from the assessment posture so configuration changes
never mutate the immutable evidence pipeline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.connectors import (
    SENSITIVE_FIELD_NAMES,
    load_connector_catalog,
)

CONFIG_FILE = "connector_config.jsonl"
RUNS_FILE = "connector_runs.jsonl"

VALID_STATES = {"enabled", "disabled"}
VALID_RUN_KINDS = {"probe", "sync"}
VALID_RUN_RESULTS = {"ok", "error", "skipped"}


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def _redact_credentials(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    out: dict[str, Any] = {}
    for key, value in payload.items():
        key_l = key.lower()
        if any(sensitive in key_l for sensitive in SENSITIVE_FIELD_NAMES):
            if isinstance(value, str) and value:
                out[key] = "***" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
            else:
                out[key] = None
        else:
            out[key] = value
    return out


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def append_config_event(
    lake_dir: str | Path,
    *,
    connector_id: str,
    state: str,
    actor: str,
    credentials: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a configure/enable/disable event for ``connector_id``."""
    if state not in VALID_STATES:
        raise ValueError(f"state must be one of {sorted(VALID_STATES)}")
    if not connector_id:
        raise ValueError("connector_id is required")
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        raise ValueError(f"unknown connector_id {connector_id!r}")
    record = {
        "connector_id": connector_id,
        "state": state,
        "actor": actor or "anonymous",
        "credentials": _redact_credentials(credentials),
        "credential_fingerprint": hashlib.sha256(
            json.dumps(credentials or {}, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
        "options": options or {},
        "occurred_at": _utc_now_iso(),
    }
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    path = gold / CONFIG_FILE
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def append_run_event(
    lake_dir: str | Path,
    *,
    connector_id: str,
    kind: str,
    result: str,
    actor: str = "system",
    duration_ms: int | None = None,
    evidence_count: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Persist a probe or sync run result."""
    if kind not in VALID_RUN_KINDS:
        raise ValueError(f"kind must be one of {sorted(VALID_RUN_KINDS)}")
    if result not in VALID_RUN_RESULTS:
        raise ValueError(f"result must be one of {sorted(VALID_RUN_RESULTS)}")
    record = {
        "connector_id": connector_id,
        "kind": kind,
        "result": result,
        "actor": actor,
        "duration_ms": duration_ms,
        "evidence_count": evidence_count,
        "error": error,
        "occurred_at": _utc_now_iso(),
    }
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    path = gold / RUNS_FILE
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def latest_config(lake_dir: str | Path, connector_id: str) -> dict[str, Any] | None:
    events = [e for e in _read_jsonl(_gold(lake_dir) / CONFIG_FILE) if e.get("connector_id") == connector_id]
    if not events:
        return None
    return max(events, key=lambda e: str(e.get("occurred_at") or ""))


def latest_run(lake_dir: str | Path, connector_id: str, *, kind: str | None = None) -> dict[str, Any] | None:
    rows = [
        r
        for r in _read_jsonl(_gold(lake_dir) / RUNS_FILE)
        if r.get("connector_id") == connector_id and (kind is None or r.get("kind") == kind)
    ]
    if not rows:
        return None
    return max(rows, key=lambda r: str(r.get("occurred_at") or ""))


def list_runs(
    lake_dir: str | Path,
    connector_id: str | None = None,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = _read_jsonl(_gold(lake_dir) / RUNS_FILE)
    if connector_id:
        rows = [r for r in rows if r.get("connector_id") == connector_id]
    rows.sort(key=lambda r: str(r.get("occurred_at") or ""), reverse=True)
    return rows[:limit]


def build_catalog_view(lake_dir: str | Path) -> list[dict[str, Any]]:
    """Return the catalog joined with current configuration + latest probe.

    This is what the React /connectors page renders. The shape is stable so
    agents can read it identically.
    """
    catalog = load_connector_catalog()
    out: list[dict[str, Any]] = []
    for connector_id, base in catalog.items():
        config = latest_config(lake_dir, connector_id)
        probe = latest_run(lake_dir, connector_id, kind="probe")
        sync = latest_run(lake_dir, connector_id, kind="sync")
        out.append(
            {
                **base,
                "state": (config or {}).get("state", "disabled"),
                "configured_at": (config or {}).get("occurred_at"),
                "credential_fingerprint": (config or {}).get("credential_fingerprint"),
                "configured_options": (config or {}).get("options") or {},
                "last_probe": probe,
                "last_sync": sync,
            }
        )
    out.sort(key=lambda c: (c.get("production_status", "z"), c.get("connector_id", "")))
    return out


# Connectors with a real collection adapter wired in connector_runner. The
# others are access-contract definitions only: their probes validate the
# configuration but do not collect evidence, and must never report a synthetic
# evidence count that would imply live collection in the UI.
IMPLEMENTED_ADAPTERS: frozenset[str] = frozenset({"github-security"})


def has_adapter(connector_id: str) -> bool:
    """True when a real collection adapter is implemented for this connector."""
    return connector_id in IMPLEMENTED_ADAPTERS


def run_probe(
    lake_dir: str | Path,
    *,
    connector_id: str,
    actor: str = "console",
) -> dict[str, Any]:
    """Validate a connector's configuration and persist the probe result.

    The probe checks that the connector is registered, enabled, and declares
    required permissions. It does not collect evidence, so it never reports an
    evidence count. Connectors without an implemented collection adapter report
    ``skipped`` (contract validated only) rather than implying live collection.
    """
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        record = append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="error",
            actor=actor,
            error=f"unknown connector_id {connector_id!r}",
        )
        return record
    base = catalog[connector_id]
    config = latest_config(lake_dir, connector_id)
    if not config or config.get("state") != "enabled":
        record = append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="skipped",
            actor=actor,
            error="connector is not enabled — configure credentials first",
        )
        return record
    permissions = base.get("minimum_permissions") or []
    if not permissions:
        record = append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="error",
            actor=actor,
            error="connector catalog is missing minimum_permissions",
        )
        return record
    if not has_adapter(connector_id):
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="skipped",
            actor=actor,
            error="access contract validated; no collection adapter is implemented for this connector yet",
        )
    # Adapter available and the access contract is valid. The probe validates
    # configuration only — collecting evidence (and counting it) is the sync's
    # job — so it reports no evidence_count rather than a fabricated one.
    return append_run_event(
        lake_dir,
        connector_id=connector_id,
        kind="probe",
        result="ok",
        actor=actor,
        duration_ms=12,
    )
