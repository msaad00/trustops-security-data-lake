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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from security_lakehouse.connectors import (
    SENSITIVE_FIELD_NAMES,
    load_connector_catalog,
)
from security_lakehouse.models import parse_event_time, utc_iso

CONFIG_FILE = "connector_config.jsonl"
RUNS_FILE = "connector_runs.jsonl"

# Fallback SLO when a connector entry omits ``freshness_slo_minutes`` (one day).
DEFAULT_FRESHNESS_SLO_MINUTES = 1440

VALID_STATES = {"enabled", "disabled"}
VALID_RUN_KINDS = {"probe", "sync"}
VALID_RUN_RESULTS = {"ok", "error", "skipped"}
PRODUCTION_STATUS_ORDER = {
    "primary_lake": 0,
    "supported_connector": 1,
    "local_demo": 2,
}


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


def validate_configure_payload(
    *,
    connector_id: str,
    state: str,
    credentials: dict[str, Any] | None,
    options: dict[str, Any] | None,
) -> None:
    """Validate public connector configuration before it can be enabled.

    ``append_config_event`` is intentionally a low-level append helper used by
    tests and offline fixture setup. Public API/console callers must pass
    through this validator so an empty form cannot create an enabled connector.
    """
    if state != "enabled":
        return
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        raise ValueError(f"unknown connector_id {connector_id!r}")

    creds = credentials or {}
    opts = {k: v for k, v in (options or {}).items() if k != "raw"}
    missing = _missing_required_config(connector_id, str(catalog[connector_id].get("credential_type") or ""), creds, opts)
    if missing:
        raise ValueError("missing required connector configuration: " + ", ".join(missing))


def _has_value(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return value is not None and str(value).strip() != ""


def _missing_required_config(
    connector_id: str,
    credential_type: str,
    credentials: dict[str, Any],
    options: dict[str, Any],
) -> list[str]:
    if connector_id == "clickhouse-telemetry-lake":
        missing = [field for field in ("host",) if not _has_value(credentials, field)]
        if not (_has_value(credentials, "token") or _has_value(credentials, "password")):
            missing.append("token or password")
        missing.extend(
            field
            for field in ("database", "events_table", "metrics_table", "detections_table")
            if not _has_value(options, field)
        )
        return missing

    if connector_id == "snowflake-evidence-lake":
        missing = [field for field in ("account", "user") if not _has_value(credentials, field)]
        if not (_has_value(credentials, "private_key") or _has_value(credentials, "oauth_token")):
            missing.append("private_key or oauth_token")
        missing.extend(
            field
            for field in ("warehouse", "database", "schema", "evidence_view")
            if not _has_value(options, field)
        )
        return missing

    if "token" in credential_type:
        return ["token"] if not _has_value(credentials, "token") else []
    if "scoped_user" in credential_type:
        return [field for field in ("host", "user", "password") if not _has_value(credentials, field)]
    if "key_pair" in credential_type:
        return [field for field in ("account", "user", "private_key") if not _has_value(credentials, field)]
    if "local" in credential_type:
        return ["lake_path"] if not _has_value(credentials, "lake_path") else []
    return ["api_key"] if not _has_value(credentials, "api_key") else []


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


def _evaluate_freshness(
    base: dict[str, Any],
    sync: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive a freshness signal for a connector from its latest sync.

    Pure compute over already-on-disk data: compares the latest *successful*
    sync's ``occurred_at`` against the connector's ``freshness_slo_minutes`` to
    flag when evidence has aged past its SLO and the dependent controls are at
    risk. Returns ``freshness_state`` ("fresh" | "stale" | "never_synced") and
    an ISO ``next_run_at`` (when the next sync is due).
    """
    evaluated_at = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        slo_minutes = int(base.get("freshness_slo_minutes") or DEFAULT_FRESHNESS_SLO_MINUTES)
    except (TypeError, ValueError):
        slo_minutes = DEFAULT_FRESHNESS_SLO_MINUTES
    if slo_minutes <= 0:
        slo_minutes = DEFAULT_FRESHNESS_SLO_MINUTES
    slo = timedelta(minutes=slo_minutes)

    last_sync_at: datetime | None = None
    if sync and sync.get("result") == "ok" and sync.get("occurred_at"):
        try:
            last_sync_at = parse_event_time(str(sync["occurred_at"]))
        except (TypeError, ValueError):
            last_sync_at = None

    if last_sync_at is None:
        return {
            "freshness_slo_minutes": slo_minutes,
            "freshness_state": "never_synced",
            "last_sync_at": None,
            "next_run_at": utc_iso(evaluated_at),
        }

    state = "stale" if (evaluated_at - last_sync_at) > slo else "fresh"
    return {
        "freshness_slo_minutes": slo_minutes,
        "freshness_state": state,
        "last_sync_at": utc_iso(last_sync_at),
        "next_run_at": utc_iso(last_sync_at + slo),
    }


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
                **_evaluate_freshness(base, sync),
            }
        )
    out.sort(
        key=lambda c: (
            PRODUCTION_STATUS_ORDER.get(str(c.get("production_status") or ""), 99),
            c.get("connector_id", ""),
        )
    )
    return out


def _implemented_adapters() -> frozenset[str]:
    """The connector_ids with a real collection adapter.

    This is derived from connector catalog metadata to avoid importing
    ``connector_runner`` from this module, which introduces a cyclic import.
    Connectors absent from the implemented set are access-contract definitions
    only: their probes validate configuration but never report a synthetic
    evidence count implying live collection in the UI.
    """
    catalog = load_connector_catalog()
    return frozenset(
        connector_id for connector_id, definition in catalog.items() if bool(definition.get("is_implemented"))
    )


def __getattr__(name: str) -> Any:
    # Expose IMPLEMENTED_ADAPTERS as a computed module attribute so callers
    # cannot mutate a stale module-level frozenset.
    if name == "IMPLEMENTED_ADAPTERS":
        return _implemented_adapters()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def has_adapter(connector_id: str) -> bool:
    """True when a real collection adapter is implemented for this connector."""
    return connector_id in _implemented_adapters()


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
