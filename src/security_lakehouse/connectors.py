"""Connector registry and access-boundary validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root  # noqa: PLC2701 (reused root lookup)

ROOT = _data_root()
DEFAULT_CONNECTOR_CATALOG = ROOT / "connectors" / "catalog.json"

VALID_COLLECTION_MODES = {"existing_lake_read", "direct_api_read", "managed_evidence_object"}
VALID_ACCESS_BOUNDARIES = {"read_only_role", "scoped_token", "dedicated_schema"}
VALID_ROUTES = {"Snowflake", "ClickHouse", "dual", "local"}
VALID_PRODUCTION_STATUSES = {"primary_lake", "supported_connector", "local_demo"}
DENIED_PERMISSION_WORDS = {"admin", "delete", "drop", "modify", "owner", "write all", "root"}
EXPLICIT_READ_ONLY_PERMISSIONS = {"administration:read"}
SENSITIVE_FIELD_NAMES = {"password", "secret", "token", "private_key", "client_secret", "api_key"}


def load_connector_catalog(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    payload = _read_json(path or DEFAULT_CONNECTOR_CATALOG)
    connectors = payload.get("connectors")
    if not isinstance(connectors, list):
        raise ValueError("connector catalog must contain a connectors list")
    return {str(item["connector_id"]): item for item in connectors}


def validate_connector_catalog(path: str | Path | None = None) -> list[str]:
    connectors = load_connector_catalog(path)
    errors: list[str] = []
    for connector_id, connector in connectors.items():
        for required in (
            "name",
            "category",
            "collection_mode",
            "access_boundary",
            "credential_type",
            "minimum_permissions",
            "evidence_types",
            "default_route",
            "freshness_slo_minutes",
            "production_status",
        ):
            if connector.get(required) in (None, "", []):
                errors.append(f"connector {connector_id} missing {required}")

        mode = str(connector.get("collection_mode", ""))
        boundary = str(connector.get("access_boundary", ""))
        route = str(connector.get("default_route", ""))
        production_status = str(connector.get("production_status", ""))
        permissions = [str(item).lower() for item in connector.get("minimum_permissions", [])]

        if mode not in VALID_COLLECTION_MODES:
            errors.append(f"connector {connector_id} has invalid collection_mode {mode}")
        if boundary not in VALID_ACCESS_BOUNDARIES:
            errors.append(f"connector {connector_id} has invalid access_boundary {boundary}")
        if route not in VALID_ROUTES:
            errors.append(f"connector {connector_id} has invalid default_route {route}")
        if production_status not in VALID_PRODUCTION_STATUSES:
            errors.append(f"connector {connector_id} has invalid production_status {production_status}")
        if int(connector.get("freshness_slo_minutes") or 0) <= 0:
            errors.append(f"connector {connector_id} freshness_slo_minutes must be positive")

        if mode == "existing_lake_read" and boundary != "read_only_role":
            errors.append(f"connector {connector_id} existing_lake_read must use read_only_role")
        if mode == "direct_api_read" and boundary != "scoped_token":
            errors.append(f"connector {connector_id} direct_api_read must use scoped_token")
        if mode == "managed_evidence_object" and boundary != "dedicated_schema":
            errors.append(f"connector {connector_id} managed_evidence_object must use dedicated_schema")

        for permission in permissions:
            if permission not in EXPLICIT_READ_ONLY_PERMISSIONS and any(
                word in permission for word in DENIED_PERMISSION_WORDS
            ):
                errors.append(f"connector {connector_id} permission is too broad: {permission}")

        for field_name, value in _flatten(connector):
            lowered = field_name.lower()
            if any(sensitive in lowered for sensitive in SENSITIVE_FIELD_NAMES):
                errors.append(f"connector {connector_id} contains secret-like field {field_name}")
            if isinstance(value, str) and _looks_like_secret(value):
                errors.append(f"connector {connector_id} contains secret-like value in {field_name}")
    return errors


def _read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _flatten(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(payload, dict):
        rows: list[tuple[str, Any]] = []
        for key, value in payload.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(value, name))
        return rows
    if isinstance(payload, list):
        rows = []
        for index, value in enumerate(payload):
            rows.extend(_flatten(value, f"{prefix}[{index}]"))
        return rows
    return [(prefix, payload)]


def _looks_like_secret(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 24:
        return False
    secret_prefixes = ("ghp_", "gho_", "xoxb-", "sk-", "AKIA")
    return stripped.startswith(secret_prefixes)
