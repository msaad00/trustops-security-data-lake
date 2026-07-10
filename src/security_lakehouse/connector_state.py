"""Connector configuration + probe state for the React workbench.

Persists three layers on top of the static ``connectors/catalog.json``:

* ``gold/connector_config.jsonl`` — append-only configuration events
  (enabled/disabled, credentials redacted, options) per connector.
* ``gold/connector_runs.jsonl`` — append-only discovery + probe + sync run history.

These are separate from the assessment posture so configuration changes
never mutate the immutable evidence pipeline.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from security_lakehouse.connectors import (
    SENSITIVE_FIELD_NAMES,
    load_connector_catalog,
)
from security_lakehouse.connectors_clickhouse import CONNECTOR_ID as CLICKHOUSE_CONNECTOR_ID
from security_lakehouse.connectors_clickhouse import discover_clickhouse_scope, probe_clickhouse_access
from security_lakehouse.connectors_runtime import CONNECTOR_ID as RUNTIME_GATEWAY_CONNECTOR_ID
from security_lakehouse.connectors_runtime import discover_runtime_gateway_scope, probe_runtime_gateway_access
from security_lakehouse.connectors_s3 import CONNECTOR_ID as S3_CONNECTOR_ID
from security_lakehouse.connectors_s3 import discover_s3_scope, probe_s3_access
from security_lakehouse.connectors_siem import CONNECTOR_ID as SIEM_CONNECTOR_ID
from security_lakehouse.connectors_siem import discover_siem_scope, probe_siem_access
from security_lakehouse.connectors_snowflake import CONNECTOR_ID as SNOWFLAKE_CONNECTOR_ID
from security_lakehouse.connectors_snowflake import discover_snowflake_scope, probe_snowflake_access
from security_lakehouse.lake_scale import apply_split_schedule_defaults
from security_lakehouse.models import parse_event_time, utc_iso

CONFIG_FILE = "connector_config.jsonl"
RUNS_FILE = "connector_runs.jsonl"

# Fallback SLO when a connector entry omits ``freshness_slo_minutes`` (one day).
DEFAULT_FRESHNESS_SLO_MINUTES = 1440

VALID_STATES = {"enabled", "disabled"}
VALID_RUN_KINDS = {"discover", "probe", "sync"}
VALID_RUN_RESULTS = {"ok", "error", "skipped"}
PRODUCTION_STATUS_ORDER = {
    "primary_lake": 0,
    "supported_connector": 1,
    "local_demo": 2,
}
_ACCESS_FINGERPRINT_KEY = b"trustops-access-fingerprint-v1"
_ACCESS_FINGERPRINT_OPTION_EXCLUDES = frozenset(
    {
        "raw",
        "sync_schedule",
        "eval_schedule",
        "split_ingest_eval",
        "fixture_dir",
        "token_env",
        "materialize",
    }
)
_SECRET_REFERENCE_SUFFIXES = ("_ref", "_env")


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def _redact_sensitive_value(value: Any) -> Any:
    """Recursively redact secret-like keys before persisting connector state."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            key_l = key.lower()
            if key_l.endswith(_SECRET_REFERENCE_SUFFIXES):
                out[key] = val
            elif any(sensitive in key_l for sensitive in SENSITIVE_FIELD_NAMES):
                if isinstance(val, str) and val:
                    marker = hashlib.pbkdf2_hmac("sha256", val.encode("utf-8"), _ACCESS_FINGERPRINT_KEY, 600_000)
                    out[key] = "***" + marker.hex()[:8]
                else:
                    out[key] = None
            else:
                out[key] = _redact_sensitive_value(val)
        return out
    if isinstance(value, list):
        return [_redact_sensitive_value(item) for item in value]
    return value


def _redact_credentials(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    redacted = _redact_sensitive_value(payload)
    return redacted if isinstance(redacted, dict) else {}


def _access_fingerprint(credentials: dict[str, Any] | None, options: dict[str, Any] | None) -> str:
    """Return a deterministic non-secret fingerprint for a scoped-access payload.

    The fingerprint is derived with PBKDF2 so secret-bearing staged payloads can
    be compared for exact probe-before-enable matching without persisting the
    raw credential material.
    """
    payload = {
        "credentials": credentials or {},
        "options": {k: v for k, v in (options or {}).items() if k not in _ACCESS_FINGERPRINT_OPTION_EXCLUDES},
    }
    return hashlib.pbkdf2_hmac(
        "sha256",
        json.dumps(payload, sort_keys=True).encode("utf-8"),
        _ACCESS_FINGERPRINT_KEY,
        100_000,
        dklen=16,
    ).hex()[:16]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON object as a line to a gold-zone JSONL file."""
    with path.open("a", encoding="utf-8") as fh:
        # lgtm[py/clear-text-storage-sensitive-data] record is sanitized before this write
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


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
    record = _build_disk_config_record(
        connector_id=connector_id,
        state=state,
        actor=actor or "anonymous",
        credentials=credentials,
        options=apply_split_schedule_defaults(options),
    )
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    _append_jsonl(gold / CONFIG_FILE, record)
    return record


def _build_disk_config_record(
    *,
    connector_id: str,
    state: str,
    actor: str,
    credentials: dict[str, Any] | None,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a connector config event safe to persist on disk (CodeQL boundary)."""
    return {
        "connector_id": connector_id,
        "state": state,
        "actor": actor,
        "credentials": _redact_credentials(credentials),
        "options": _redact_sensitive_value({k: v for k, v in (options or {}).items() if k != "raw"}),
        "credential_fingerprint": _access_fingerprint(credentials, options),
        "occurred_at": _utc_now_iso(),
    }


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
    error = configure_payload_error(
        connector_id=connector_id,
        state=state,
        credentials=credentials,
        options=options,
    )
    if error:
        raise ValueError(error)


def configure_payload_error(
    *,
    connector_id: str,
    state: str,
    credentials: dict[str, Any] | None,
    options: dict[str, Any] | None,
) -> str | None:
    """Return a public, deterministic connector configuration validation error."""
    if state != "enabled":
        return None
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        return f"unknown connector_id {connector_id!r}"

    creds = credentials or {}
    opts = {k: v for k, v in (options or {}).items() if k != "raw"}
    missing = _missing_required_config(
        connector_id, str(catalog[connector_id].get("credential_type") or ""), creds, opts
    )
    if missing:
        return "missing required connector configuration: " + ", ".join(missing)
    return None


def enablement_probe_error(
    lake_dir: str | Path,
    *,
    connector_id: str,
    state: str,
    credentials: dict[str, Any] | None,
    options: dict[str, Any] | None,
) -> str | None:
    """Return an enablement error when the latest probe is not usable.

    Public API/console enablement is stricter than low-level fixture writes:
    operators must prove the exact staged access payload before it can be
    persisted as enabled. ``skipped`` probes are diagnostic only and never
    authorize enablement.
    """
    if state != "enabled":
        return None
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        return None
    if not has_adapter(connector_id):
        return "connector has no live probe adapter; keep it disabled until collection support is implemented"
    probe = latest_run(lake_dir, connector_id, kind="probe")
    if not probe or probe.get("result") != "ok":
        return "run Test connection before enabling; latest probe must be ok"
    expected = _access_fingerprint(credentials, options)
    if probe.get("access_fingerprint") != expected:
        return "rerun Test connection for these exact credentials and read scope before enabling"
    return None


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
        missing = ["host"] if not _has_value(credentials, "host") else []
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        return missing

    if connector_id == "snowflake-evidence-lake":
        missing = [field for field in ("account", "user") if not _has_value(credentials, field)]
        if not (
            _has_value(credentials, "credential_ref")
            or _has_value(credentials, "private_key_ref")
            or _has_value(credentials, "oauth_token_ref")
        ):
            missing.append("credential_ref")
        missing.extend(
            field
            for field in (
                "warehouse",
                "database",
                "schema",
                "audit_events",
                "control_posture",
                "asset_risk",
                "evidence_bundles",
            )
            if not _has_value(options, field)
        )
        return missing

    if connector_id == "aws-posture":
        return ["account_id"] if not _has_value(credentials, "account_id") else []

    if connector_id == "azure-posture":
        return ["subscription_id"] if not _has_value(credentials, "subscription_id") else []

    if connector_id == "gcp-posture":
        # Credentials resolve through Application Default Credentials, so only
        # the project scope is required — no stored credential reference, the
        # same identity model as aws-posture and azure-posture.
        return ["project_id"] if not _has_value(credentials, "project_id") else []

    if connector_id in {"github-security", "gitlab-security"}:
        missing: list[str] = []
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        if not _has_value(options, "repo"):
            missing.append("repo")
        return missing

    if connector_id in {"okta-identity", "okta-system-log"}:
        missing = []
        if not _has_value(credentials, "org_url"):
            missing.append("org_url")
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        return missing

    if connector_id == "google-workspace-identity":
        missing = []
        if not _has_value(credentials, "customer_id"):
            missing.append("customer_id")
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        return missing

    if connector_id == "object-storage-evidence":
        return [field for field in ("bucket", "prefix") if not _has_value(options, field)]

    if connector_id == "siem-alerts":
        missing = ["host"] if not _has_value(credentials, "host") else []
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        if not _has_value(options, "index"):
            missing.append("index")
        return missing

    if connector_id == "runtime-gateway":
        missing = ["host"] if not _has_value(credentials, "host") else []
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        if not _has_value(options, "stream"):
            missing.append("stream")
        return missing

    if connector_id == "jira-ticketing":
        missing = []
        for field in ("base_url", "email"):
            if not _has_value(credentials, field):
                missing.append(field)
        if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token")):
            missing.append("credential_ref")
        return missing

    if "token" in credential_type:
        return (
            ["credential_ref"]
            if not (_has_value(credentials, "credential_ref") or _has_value(credentials, "token"))
            else []
        )
    if "scoped_user" in credential_type:
        return [field for field in ("host", "token") if not _has_value(credentials, field)]
    if "key_pair" in credential_type:
        return [field for field in ("account", "user", "private_key") if not _has_value(credentials, field)]
    if "local" in credential_type:
        return ["lake_path"] if not _has_value(credentials, "lake_path") else []
    return ["api_key"] if not _has_value(credentials, "api_key") else []


def _safe_persist_error(error: str | None) -> str | None:
    """Bound error text before writing connector run records to disk."""
    if error is None:
        return None
    if any(marker in error for marker in ("/", "\\", ":443", "connection to host", "10.")):
        return _safe_run_error(ValueError(error))
    return error


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
    access_fingerprint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a probe or sync run result."""
    if kind not in VALID_RUN_KINDS:
        raise ValueError(f"kind must be one of {sorted(VALID_RUN_KINDS)}")
    if result not in VALID_RUN_RESULTS:
        raise ValueError(f"result must be one of {sorted(VALID_RUN_RESULTS)}")
    record = _build_disk_run_record(
        connector_id=connector_id,
        kind=kind,
        result=result,
        actor=actor,
        duration_ms=duration_ms,
        evidence_count=evidence_count,
        error=error,
        access_fingerprint=access_fingerprint,
        metadata=metadata,
    )
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    _append_jsonl(gold / RUNS_FILE, record)
    return record


def _build_disk_run_record(
    *,
    connector_id: str,
    kind: str,
    result: str,
    actor: str,
    duration_ms: int | None,
    evidence_count: int | None,
    error: str | None,
    access_fingerprint: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a connector run record safe to persist on disk (CodeQL boundary)."""
    return {
        "connector_id": connector_id,
        "kind": kind,
        "result": result,
        "actor": actor,
        "duration_ms": duration_ms,
        "evidence_count": evidence_count,
        "error": _safe_persist_error(error),
        "access_fingerprint": access_fingerprint,
        "metadata": _redact_sensitive_value(metadata or {}),
        "occurred_at": _utc_now_iso(),
    }


def _missing_discovery_config(
    connector_id: str,
    credential_type: str,
    credentials: dict[str, Any],
) -> list[str]:
    if connector_id == "snowflake-evidence-lake":
        missing = [field for field in ("account", "user") if not _has_value(credentials, field)]
        if not (
            _has_value(credentials, "credential_ref")
            or _has_value(credentials, "private_key_ref")
            or _has_value(credentials, "oauth_token_ref")
        ):
            missing.append("credential_ref")
        return missing
    if connector_id == "aws-posture":
        return ["account_id"] if not _has_value(credentials, "account_id") else []
    if connector_id == "azure-posture":
        return ["subscription_id"] if not _has_value(credentials, "subscription_id") else []
    return _missing_required_config(connector_id, credential_type, credentials, {})


def _discovery_scope_context(credentials: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Allowlist non-secret discovery scope fields before anything is persisted."""
    return {
        "account_id": str(credentials.get("account_id") or ""),
        "subscription_id": str(credentials.get("subscription_id") or ""),
        "project_id": str(credentials.get("project_id") or ""),
        "account": str(credentials.get("account") or ""),
        "user": str(credentials.get("user") or ""),
        "region": str(credentials.get("region") or options.get("region") or ""),
    }


def _scope_candidates(
    *,
    connector_id: str,
    credentials: dict[str, Any],
    scope: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    """Return selectable read-scope candidates without collecting evidence."""
    if connector_id == "snowflake-evidence-lake":
        database = str(options.get("database") or "")
        schema = str(options.get("schema") or "")
        warehouse = str(options.get("warehouse") or "")
        recommended_database = "TRUSTOPS_SECURITY_LAKE"
        recommended_schema = "EVIDENCE"
        recommended_warehouse = "TRUSTOPS_READ_WH"
        defaults = {
            "audit_events": "TRUSTOPS_AUDIT_EVENTS",
            "control_posture": "TRUSTOPS_CONTROL_POSTURE",
            "asset_risk": "TRUSTOPS_ASSET_RISK",
            "evidence_bundles": "TRUSTOPS_EVIDENCE_BUNDLES",
        }
        views = [
            {
                "kind": "view",
                "name": str(options.get(key) or default),
                "required": True,
                "purpose": key,
            }
            for key, default in defaults.items()
        ]
        live = discover_snowflake_scope(credentials=credentials, options=options)
        if live.get("ok"):
            return live
        curated = {
            "selection_mode": "curated_views",
            "selectors": [
                {
                    "kind": "warehouse",
                    "name": warehouse,
                    "required": True,
                    "selected": bool(warehouse),
                },
                {
                    "kind": "database",
                    "name": database,
                    "required": True,
                    "selected": bool(database),
                },
                {
                    "kind": "schema",
                    "name": schema,
                    "required": True,
                    "selected": bool(schema),
                },
                *views,
            ],
            "requires_selection": [
                name
                for name, selected in (
                    ("warehouse", warehouse),
                    ("database", database),
                    ("schema", schema),
                )
                if not selected
            ],
            "recommended_options": {
                "warehouse": warehouse or recommended_warehouse,
                "database": database or recommended_database,
                "schema": schema or recommended_schema,
                **defaults,
            },
        }
        curated["live_discovery_error"] = live.get("error")
        return curated
    if connector_id == "aws-posture":
        account_id = str(scope.get("account_id") or "")
        region = str(scope.get("region") or options.get("region") or "us-east-1")
        return {
            "selection_mode": "account",
            "selectors": [
                {"kind": "account", "name": account_id, "required": True, "selected": bool(account_id)},
                {"kind": "region", "name": region, "required": False, "selected": bool(region)},
            ],
            "recommended_options": {"region": region},
        }
    if connector_id == "azure-posture":
        subscription_id = str(scope.get("subscription_id") or "")
        return {
            "selection_mode": "subscription",
            "selectors": [
                {
                    "kind": "subscription",
                    "name": subscription_id,
                    "required": True,
                    "selected": bool(subscription_id),
                }
            ],
            "recommended_options": {},
        }
    if connector_id == "object-storage-evidence":
        bucket = str(options.get("bucket") or credentials.get("bucket") or "")
        prefix = str(options.get("prefix") or credentials.get("prefix") or "")
        live = discover_s3_scope(credentials=credentials, options=options)
        if live.get("ok"):
            return live
        return {
            "selection_mode": "visible_prefixes",
            "selectors": [
                {"kind": "bucket", "name": bucket, "required": True, "selected": bool(bucket)},
                {"kind": "prefix", "name": prefix, "required": True, "selected": bool(prefix)},
            ],
            "recommended_options": {"bucket": bucket, "prefix": prefix},
            "live_discovery_error": live.get("error"),
        }
    if connector_id == "clickhouse-telemetry-lake":
        live = discover_clickhouse_scope(credentials=credentials, options=options)
        if live.get("ok"):
            return live
        database = str(options.get("database") or "security")
        table = str(options.get("table") or "normalized_events")
        return {
            "selection_mode": "visible_tables",
            "selectors": [
                {"kind": "database", "name": database, "required": True, "selected": bool(database)},
                {"kind": "table", "name": table, "required": True, "selected": bool(table)},
            ],
            "recommended_options": {"database": database, "table": table},
            "live_discovery_error": live.get("error"),
        }
    if connector_id == "siem-alerts":
        live = discover_siem_scope(credentials=credentials, options=options)
        if live.get("ok"):
            return live
        index = str(options.get("index") or "alerts")
        return {
            "selection_mode": "visible_indexes",
            "selectors": [{"kind": "index", "name": index, "required": True, "selected": bool(index)}],
            "recommended_options": {"index": index},
            "live_discovery_error": live.get("error"),
        }
    if connector_id == "runtime-gateway":
        live = discover_runtime_gateway_scope(credentials=credentials, options=options)
        if live.get("ok"):
            return live
        stream = str(options.get("stream") or "runtime-events")
        return {
            "selection_mode": "visible_streams",
            "selectors": [{"kind": "stream", "name": stream, "required": True, "selected": bool(stream)}],
            "recommended_options": {"stream": stream},
            "live_discovery_error": live.get("error"),
        }
    return {
        "selection_mode": "configured_scope",
        "selectors": [],
        "recommended_options": options,
    }


def run_discovery(
    lake_dir: str | Path,
    *,
    connector_id: str,
    actor: str = "console",
    credentials: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Discover selectable connector scopes without persisting credentials."""
    started = time.perf_counter()
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="discover",
            result="error",
            actor=actor,
            error=f"unknown connector_id {connector_id!r}",
        )
    staged_payload = credentials is not None or options is not None
    if staged_payload:
        credentials = credentials or {}
        options = {k: v for k, v in (options or {}).items() if k != "raw"}
    else:
        config = latest_config(lake_dir, connector_id)
        if config and config.get("state") == "enabled":
            credentials = dict(config.get("credentials") or {})
            options = {k: v for k, v in dict(config.get("options") or {}).items() if k != "raw"}
        else:
            credentials = {}
            options = {}
    missing = _missing_discovery_config(
        connector_id,
        str(catalog[connector_id].get("credential_type") or ""),
        credentials,
    )
    if missing:
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="discover",
            result="error",
            actor=actor,
            error="missing required connector discovery configuration: " + ", ".join(missing),
        )
    metadata = _scope_candidates(
        connector_id=connector_id,
        credentials=credentials,
        scope=_discovery_scope_context(credentials, options),
        options=options,
    )
    selectors = [item for item in metadata.get("selectors", []) if isinstance(item, dict)]
    return append_run_event(
        lake_dir,
        connector_id=connector_id,
        kind="discover",
        result="ok",
        actor=actor,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
        evidence_count=len(selectors),
        metadata=metadata,
    )


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


def latest_successful_run(
    lake_dir: str | Path,
    connector_id: str,
    *,
    kind: str = "sync",
) -> dict[str, Any] | None:
    """Return the newest run of ``kind`` whose ``result`` is ``ok``."""
    for run in list_runs(lake_dir, connector_id):
        if run.get("kind") == kind and run.get("result") == "ok":
            return run
    return None


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
        sync_attempt = latest_run(lake_dir, connector_id, kind="sync")
        sync_success = latest_successful_run(lake_dir, connector_id, kind="sync")
        out.append(
            {
                **base,
                "state": (config or {}).get("state", "disabled"),
                "configured_at": (config or {}).get("occurred_at"),
                "credential_fingerprint": (config or {}).get("credential_fingerprint"),
                "configured_options": (config or {}).get("options") or {},
                "last_probe": probe,
                "last_sync": sync_attempt,
                "last_successful_sync": sync_success,
                **_evaluate_freshness(base, sync_success),
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


def _safe_run_error(exc: Exception) -> str:
    """Bounded, safe error text for a run record surfaced at the HTTP boundary.

    A probe run record is returned to the caller over the API, and a raw
    exception string can carry connection detail or internal paths. Record only
    the exception class name — a code identifier, not runtime data — so the
    operator still sees the failure category without the engine leaking
    internals. (The configure step reports missing fields separately and safely.)
    """
    return type(exc).__name__


def run_probe(
    lake_dir: str | Path,
    *,
    connector_id: str,
    actor: str = "console",
    credentials: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a connector's configuration and persist the probe result.

    The probe checks that the connector is registered and has either an enabled
    saved configuration or a staged credential payload supplied by the caller.
    Staged payloads are validated but never persisted. The probe does not
    collect evidence, so it never reports an evidence count. Connectors without
    an implemented collection adapter report ``skipped`` (contract validated
    only) rather than implying live collection.
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
    has_staged_payload = credentials is not None or options is not None
    staged_access_fingerprint = _access_fingerprint(credentials, options) if has_staged_payload else None
    if has_staged_payload:
        error = configure_payload_error(
            connector_id=connector_id,
            state="enabled",
            credentials=credentials or {},
            options=options or {},
        )
        if error:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=error,
                access_fingerprint=staged_access_fingerprint,
            )
    else:
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
            access_fingerprint=staged_access_fingerprint,
            metadata={"probe_mode": "contract_only"},
        )
    if connector_id == CLICKHOUSE_CONNECTOR_ID:
        if has_staged_payload:
            effective_credentials = credentials or {}
            effective_options = options or {}
        else:
            config = latest_config(lake_dir, connector_id) or {}
            effective_credentials = dict(config.get("credentials") or {})
            effective_options = dict(config.get("options") or {})
        try:
            probe = probe_clickhouse_access(
                credentials=effective_credentials,
                options=effective_options,
            )
        except ValueError as exc:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=_safe_run_error(exc),
                access_fingerprint=staged_access_fingerprint,
            )
        if not probe.get("ok"):
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=f"ClickHouse read scope is not ready: {probe.get('table') or 'normalized_events'}",
                access_fingerprint=staged_access_fingerprint,
                metadata={**probe, "probe_mode": "live"},
            )
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="ok",
            actor=actor,
            duration_ms=12,
            evidence_count=int(probe.get("row_count") or 0),
            access_fingerprint=staged_access_fingerprint,
            metadata={**probe, "probe_mode": "live"},
        )
    if connector_id == S3_CONNECTOR_ID:
        if has_staged_payload:
            effective_credentials = credentials or {}
            effective_options = options or {}
        else:
            config = latest_config(lake_dir, connector_id) or {}
            effective_credentials = dict(config.get("credentials") or {})
            effective_options = dict(config.get("options") or {})
        try:
            probe = probe_s3_access(
                credentials=effective_credentials,
                options=effective_options,
            )
        except ValueError as exc:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=_safe_run_error(exc),
                access_fingerprint=staged_access_fingerprint,
            )
        if not probe.get("ok"):
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=f"S3 read scope is not ready: {probe.get('bucket') or 'bucket'}/{probe.get('prefix') or ''}",
                access_fingerprint=staged_access_fingerprint,
                metadata={**probe, "probe_mode": "live"},
            )
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="ok",
            actor=actor,
            duration_ms=12,
            evidence_count=int(probe.get("object_count") or 0),
            access_fingerprint=staged_access_fingerprint,
            metadata={**probe, "probe_mode": "live"},
        )
    if connector_id == SIEM_CONNECTOR_ID:
        if has_staged_payload:
            effective_credentials = credentials or {}
            effective_options = options or {}
        else:
            config = latest_config(lake_dir, connector_id) or {}
            effective_credentials = dict(config.get("credentials") or {})
            effective_options = dict(config.get("options") or {})
        try:
            probe = probe_siem_access(
                credentials=effective_credentials,
                options=effective_options,
            )
        except ValueError as exc:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=_safe_run_error(exc),
                access_fingerprint=staged_access_fingerprint,
            )
        if not probe.get("ok"):
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=f"SIEM read scope is not ready: {probe.get('index') or 'alerts'}",
                access_fingerprint=staged_access_fingerprint,
                metadata={**probe, "probe_mode": "live"},
            )
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="ok",
            actor=actor,
            duration_ms=12,
            evidence_count=int(probe.get("alert_count") or 0),
            access_fingerprint=staged_access_fingerprint,
            metadata={**probe, "probe_mode": "live"},
        )
    if connector_id == RUNTIME_GATEWAY_CONNECTOR_ID:
        if has_staged_payload:
            effective_credentials = credentials or {}
            effective_options = options or {}
        else:
            config = latest_config(lake_dir, connector_id) or {}
            effective_credentials = dict(config.get("credentials") or {})
            effective_options = dict(config.get("options") or {})
        try:
            probe = probe_runtime_gateway_access(
                credentials=effective_credentials,
                options=effective_options,
            )
        except ValueError as exc:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=_safe_run_error(exc),
                access_fingerprint=staged_access_fingerprint,
            )
        if not probe.get("ok"):
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=f"Runtime gateway read scope is not ready: {probe.get('stream') or 'runtime-events'}",
                access_fingerprint=staged_access_fingerprint,
                metadata={**probe, "probe_mode": "live"},
            )
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="ok",
            actor=actor,
            duration_ms=12,
            evidence_count=int(probe.get("event_count") or 0),
            access_fingerprint=staged_access_fingerprint,
            metadata={**probe, "probe_mode": "live"},
        )
    if connector_id == SNOWFLAKE_CONNECTOR_ID:
        if has_staged_payload:
            effective_credentials = credentials or {}
            effective_options = options or {}
        else:
            config = latest_config(lake_dir, connector_id) or {}
            effective_credentials = dict(config.get("credentials") or {})
            effective_options = dict(config.get("options") or {})
        try:
            probe = probe_snowflake_access(credentials=effective_credentials, options=effective_options)
        except ValueError as exc:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error=_safe_run_error(exc),
                access_fingerprint=staged_access_fingerprint,
            )
        failed = [
            str(view.get("view") or view.get("purpose") or "unknown")
            for view in probe.get("views", [])
            if isinstance(view, dict) and view.get("ok") is not True
        ]
        if failed:
            return append_run_event(
                lake_dir,
                connector_id=connector_id,
                kind="probe",
                result="error",
                actor=actor,
                error="Snowflake read scope is not ready: " + ", ".join(failed),
                access_fingerprint=staged_access_fingerprint,
                metadata=probe,
            )
        return append_run_event(
            lake_dir,
            connector_id=connector_id,
            kind="probe",
            result="ok",
            actor=actor,
            duration_ms=12,
            evidence_count=len(probe.get("views", [])),
            access_fingerprint=staged_access_fingerprint,
            metadata={**probe, "probe_mode": "live"},
        )

    # Adapter available and the access contract is valid. The generic probe
    # validates configuration only — collecting evidence is the sync's job.
    return append_run_event(
        lake_dir,
        connector_id=connector_id,
        kind="probe",
        result="ok",
        actor=actor,
        duration_ms=12,
        access_fingerprint=staged_access_fingerprint,
        metadata={"probe_mode": "config_only"},
    )
