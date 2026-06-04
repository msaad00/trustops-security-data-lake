"""Snowflake evidence-lake collector.

The Snowflake connector is an existing-lake reader: it expects TrustOps-shaped
evidence views to already exist in the customer's Snowflake account and reads
them with a least-privilege role. It never creates, updates, or deletes
Snowflake objects.

Two clients sit behind one interface:

* :class:`SnowflakeClient` — optional live client backed by
  ``snowflake.connector`` when it is installed. The base package does not
  depend on the driver; CI runs entirely from fixtures.
* :class:`SnowflakeFixtureClient` — reads JSON fixtures that mirror the four
  evidence views so collection is deterministic and network-free in tests.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.io import read_json
from security_lakehouse.models import utc_iso

CONNECTOR_ID = "snowflake-evidence-lake"
SOURCE = "snowflake"

DEFAULT_VIEWS = {
    "audit_events": "TRUSTOPS_AUDIT_EVENTS",
    "control_posture": "TRUSTOPS_CONTROL_POSTURE",
    "asset_risk": "TRUSTOPS_ASSET_RISK",
    "evidence_bundles": "TRUSTOPS_EVIDENCE_BUNDLES",
}

AUDIT_CONTROLS = ["SOC2-CC7.2", "ISO27001-A.8.16"]
CONTROL_POSTURE_CONTROLS = ["SOC2-CC6.1", "SOC2-CC7.2"]
ASSET_RISK_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.8.8", "NIST-AI-RMF-MAP-1.5"]
BUNDLE_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15"]


class SnowflakeClient:
    """Read-only Snowflake client backed by ``snowflake.connector``.

    The connector is imported lazily so TrustOps remains lightweight unless a
    user opts into live Snowflake collection. Authentication supports the
    Snowflake Python connector's standard keyword arguments passed by the
    runner (account, user, password/token, warehouse, database, schema, role).
    """

    def __init__(self, *, query_params: dict[str, Any], views: dict[str, str] | None = None) -> None:
        try:
            import snowflake.connector  # type: ignore[import-untyped]  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - live Snowflake only
            raise RuntimeError(
                "snowflake-evidence-lake live collection requires snowflake-connector-python; "
                "install it or use --fixture-dir"
            ) from exc
        self._connector = snowflake.connector
        self.query_params = {key: value for key, value in query_params.items() if value}
        self.views = views or DEFAULT_VIEWS

    def audit_events(self) -> list[dict[str, Any]]:
        return self._select_view("audit_events")

    def control_posture(self) -> list[dict[str, Any]]:
        return self._select_view("control_posture")

    def asset_risk(self) -> list[dict[str, Any]]:
        return self._select_view("asset_risk")

    def evidence_bundles(self) -> list[dict[str, Any]]:
        return self._select_view("evidence_bundles")

    def _select_view(self, key: str) -> list[dict[str, Any]]:
        view = _safe_identifier(self.views[key])
        with self._connector.connect(**self.query_params) as conn:  # pragma: no cover - live Snowflake only
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM {view}")  # noqa: S608 - identifier is strictly validated above
                names = [str(col[0]).lower() for col in cursor.description or []]
                return [dict(zip(names, row, strict=False)) for row in cursor.fetchall()]
            finally:
                cursor.close()


class SnowflakeFixtureClient:
    """Offline Snowflake evidence client backed by a fixture directory."""

    def __init__(self, fixture_dir: str | Path, *, account: str = "fixture-snowflake") -> None:
        self.fixture = Path(fixture_dir)
        self.account = account

    def audit_events(self) -> list[dict[str, Any]]:
        return self._read_list("audit_events.json")

    def control_posture(self) -> list[dict[str, Any]]:
        return self._read_list("control_posture.json")

    def asset_risk(self) -> list[dict[str, Any]]:
        return self._read_list("asset_risk.json")

    def evidence_bundles(self) -> list[dict[str, Any]]:
        return self._read_list("evidence_bundles.json")

    def _read_list(self, name: str) -> list[dict[str, Any]]:
        path = self.fixture / name
        if not path.exists():
            return []
        payload = read_json(path)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []


def collect_snowflake_evidence(
    client: SnowflakeClient | SnowflakeFixtureClient,
    *,
    account: str | None = None,
    collected_at: datetime | None = None,
    tenant_id: str = "customer-managed",
) -> list[dict[str, Any]]:
    """Collect canonical raw evidence from Snowflake evidence views."""
    now = collected_at or datetime.now(UTC)
    account_slug = _slug(account or getattr(client, "account", None) or "snowflake")
    rows: list[dict[str, Any]] = []

    for row in client.audit_events():
        event = _audit_event(account_slug, row, now, tenant_id)
        if event:
            rows.append(event)
    for row in client.control_posture():
        event = _control_posture_event(account_slug, row, now, tenant_id)
        if event:
            rows.append(event)
    for row in client.asset_risk():
        event = _asset_risk_event(account_slug, row, now, tenant_id)
        if event:
            rows.append(event)
    for row in client.evidence_bundles():
        event = _evidence_bundle_event(account_slug, row, now, tenant_id)
        if event:
            rows.append(event)
    return rows


def _audit_event(account: str, row: dict[str, Any], collected_at: datetime, tenant_id: str) -> dict[str, Any] | None:
    audit_id = _first(row, "audit_id", "event_id", "id")
    if not audit_id:
        return None
    actor = _first(row, "actor", "user_name", "principal") or "unknown"
    object_name = _first(row, "object_name", "target", "asset_id") or "snowflake:audit"
    status = _status(row.get("status") or row.get("result") or "observed")
    severity = _severity(row.get("severity") or ("medium" if status == "open" else "info"))
    evidence_ref = _first(row, "evidence_ref", "query_id", "event_id") or str(audit_id)
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="audit_event",
        dedupe_key=str(audit_id),
        event_type="snowflake.audit.event",
        asset_id=f"snowflake:audit:{_slug(object_name)}",
        asset_type="audit_event",
        controls=_controls(row, AUDIT_CONTROLS),
        status=status,
        severity=severity,
        evidence_ref=f"snowflake://audit/{evidence_ref}",
        attributes={
            "audit_id": audit_id,
            "actor": actor,
            "object_name": object_name,
            "query_id": row.get("query_id"),
            "event_action": row.get("event_action") or row.get("action"),
            "source_view": "audit_events",
        },
    )


def _control_posture_event(
    account: str,
    row: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any] | None:
    control_id = _first(row, "control_id", "control")
    if not control_id:
        return None
    status = _status(row.get("status") or row.get("result") or "observed")
    risk = _int(row.get("risk_score"))
    severity = _severity(row.get("severity") or _severity_from_risk(risk, status))
    evidence_ref = _first(row, "evidence_ref", "snapshot_id") or str(control_id)
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="control_posture",
        dedupe_key=str(control_id),
        event_type="snowflake.control.posture",
        asset_id=f"snowflake:control:{_slug(control_id)}",
        asset_type="control_posture",
        controls=_controls(row, [str(control_id), *CONTROL_POSTURE_CONTROLS]),
        status=status,
        severity=severity,
        evidence_ref=f"snowflake://control_posture/{evidence_ref}",
        attributes={
            "control_id": control_id,
            "framework_id": row.get("framework_id"),
            "risk_score": risk,
            "confidence": row.get("confidence"),
            "source_view": "control_posture",
        },
    )


def _asset_risk_event(
    account: str, row: dict[str, Any], collected_at: datetime, tenant_id: str
) -> dict[str, Any] | None:
    asset_id = _first(row, "asset_id", "asset")
    if not asset_id:
        return None
    risk = _int(row.get("risk_score"))
    status = _status(row.get("status") or ("open" if risk >= 70 else "observed"))
    severity = _severity(row.get("severity") or _severity_from_risk(risk, status))
    evidence_ref = _first(row, "evidence_ref", "asset_id") or str(asset_id)
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="asset_risk",
        dedupe_key=str(asset_id),
        event_type="snowflake.asset.risk",
        asset_id=str(asset_id),
        asset_type=str(row.get("asset_type") or "asset"),
        controls=_controls(row, ASSET_RISK_CONTROLS),
        status=status,
        severity=severity,
        evidence_ref=f"snowflake://asset_risk/{evidence_ref}",
        attributes={
            "asset_id": asset_id,
            "asset_type": row.get("asset_type"),
            "owner": row.get("owner") or row.get("asset_owner"),
            "environment": row.get("environment"),
            "risk_score": risk,
            "source_view": "asset_risk",
        },
    )


def _evidence_bundle_event(
    account: str,
    row: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any] | None:
    bundle_id = _first(row, "bundle_id", "evidence_id", "id")
    if not bundle_id:
        return None
    evidence_ref = _first(row, "evidence_ref", "object_uri", "bundle_uri") or str(bundle_id)
    status = _status(row.get("status") or "observed")
    severity = _severity(row.get("severity") or "info")
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="evidence_bundle",
        dedupe_key=str(bundle_id),
        event_type="snowflake.evidence.bundle",
        asset_id=f"snowflake:evidence_bundle:{_slug(bundle_id)}",
        asset_type="evidence_bundle",
        controls=_controls(row, BUNDLE_CONTROLS),
        status=status,
        severity=severity,
        evidence_ref=str(evidence_ref),
        attributes={
            "bundle_id": bundle_id,
            "hash_sha256": row.get("hash_sha256") or row.get("sha256"),
            "object_uri": row.get("object_uri"),
            "source_view": "evidence_bundles",
        },
    )


def _event(
    *,
    account: str,
    collected_at: datetime,
    tenant_id: str,
    signal: str,
    event_type: str,
    asset_id: str,
    asset_type: str,
    controls: list[str],
    status: str,
    severity: str,
    evidence_ref: str,
    attributes: dict[str, Any],
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    stable = _stable_suffix(account=account, signal=signal, asset_id=asset_id, dedupe_key=dedupe_key)
    owner = str(attributes.get("owner") or attributes.get("actor") or account)
    environment = str(attributes.get("environment") or "prod")
    return {
        "event_id": f"snowflake-{stable}",
        "tenant_id": tenant_id,
        "workspace_id": "default",
        "event_time": utc_iso(collected_at),
        "source": SOURCE,
        "event_type": event_type,
        "entity": {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_owner": owner,
            "environment": environment,
            "org": account,
        },
        "severity": severity,
        "status": status,
        "controls": controls,
        "evidence": {
            "evidence_id": f"ev-{stable}",
            "evidence_ref": evidence_ref,
            "evidence_collected_at": utc_iso(collected_at),
        },
        "attributes": attributes,
    }


def _controls(row: dict[str, Any], default: list[str]) -> list[str]:
    raw = row.get("controls") or row.get("control_ids") or row.get("control_id")
    values: list[str]
    if isinstance(raw, list):
        values = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        values = [part.strip() for part in re.split(r"[,|]", raw) if part.strip()]
    else:
        values = []
    out: list[str] = []
    for item in [*values, *default]:
        if item and item not in out:
            out.append(item)
    return out


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _status(value: Any) -> str:
    text = str(value or "observed").strip().lower()
    if text in {"pass", "passed", "ok", "ready", "compliant", "closed", "resolved"}:
        return "pass"
    if text in {"fail", "failed", "failing", "blocked", "open", "noncompliant", "non-compliant"}:
        return "open"
    return "observed"


def _severity(value: Any) -> str:
    text = str(value or "info").strip().lower()
    if text in {"critical", "high", "medium", "low", "info", "none"}:
        return text
    return "info"


def _severity_from_risk(risk: int | None, status: str) -> str:
    if status != "open":
        return "info"
    if risk is None:
        return "medium"
    if risk >= 90:
        return "critical"
    if risk >= 70:
        return "high"
    if risk >= 40:
        return "medium"
    return "low"


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9_.:@/-]+", "-", str(value or "").lower()).strip("-")
    return slug[:128] or "snowflake"


def _stable_suffix(*, account: str, signal: str, asset_id: str, dedupe_key: str | None) -> str:
    seed = f"{account}:{signal}:{dedupe_key or asset_id}".lower()
    return re.sub(r"[^a-z0-9_.:-]+", "-", seed).strip("-")[:96] or "snowflake"


def _safe_identifier(value: str) -> str:
    """Validate a Snowflake identifier/view reference used in SELECT statements."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("Snowflake view name must not be empty")
    parts = text.split(".")
    if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", part) for part in parts):
        raise ValueError(f"unsafe Snowflake view identifier {value!r}")
    return ".".join(parts)


def _as_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [row for row in rows if isinstance(row, dict)]
