"""Transport-agnostic ``/api/v1`` contract for headless humans and agents.

Both deployment modes build their versioned responses from this module:

- the zero-dependency stdlib server (:mod:`security_lakehouse.server`)
- the optional FastAPI server (:mod:`security_lakehouse.server_app`)

Keeping the envelope, collection controls, and route table here means the
agent-facing contract cannot drift between local mode and server mode.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from pathlib import Path
from typing import Any

from security_lakehouse.assessment import (
    build_current_posture,
    posture_as_of,
    verify_snapshot_chain,
    write_assessment_snapshot,
)
from security_lakehouse.connector_runner import ConnectorSyncError, run_connector_sync
from security_lakehouse.connector_state import (
    append_config_event,
    build_catalog_view,
    configure_payload_error,
    enablement_probe_error,
    list_runs,
    run_discovery,
    run_probe,
)
from security_lakehouse.framework_detail import build_framework_detail
from security_lakehouse.graph import analyze_coverage
from security_lakehouse.ingestion_status import build_ingestion_status
from security_lakehouse.io import read_jsonl, resolve_path
from security_lakehouse.tracking import verify_tracking_chain

API_VERSION = "v1"

Params = Mapping[str, list[str]]
JsonObject = dict[str, Any]


def envelope(resource: str, data: Any, *, meta: JsonObject | None = None) -> JsonObject:
    """Wrap a payload in the stable v1 envelope."""
    return {
        "data": data,
        "meta": {"api_version": API_VERSION, "resource": resource, **(meta or {})},
        "errors": [],
    }


def error_envelope(code: str, detail: str, *, resource: str = "unknown") -> JsonObject:
    """Build the v1 error envelope."""
    return {
        "data": None,
        "meta": {"api_version": API_VERSION, "resource": resource},
        "errors": [{"code": code, "detail": detail}],
    }


def list_snapshots(lake_dir: str | Path) -> list[JsonObject]:
    """Summarize point-in-time assessment snapshots written to the gold zone."""
    snapshots_dir = Path(lake_dir) / "gold" / "snapshots"
    if not snapshots_dir.is_dir():
        return []
    out: list[JsonObject] = []
    for path in sorted(snapshots_dir.glob("assessment-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        posture = payload.get("posture") or {}
        out.append(
            {
                "snapshot_path": str(path),
                "evaluated_at": payload.get("evaluated_at"),
                "reason": payload.get("snapshot_reason") or "manual",
                "assessment_hash": payload.get("assessment_hash"),
                "posture_score": posture.get("score"),
                "open_violation_count": posture.get("open_violation_count"),
                "critical_violation_count": posture.get("critical_violation_count"),
            }
        )
    return out


# Route -> (resource name, loader) for endpoints returning a single object.
SINGLETON_LOADERS: dict[str, tuple[str, Callable[[Path], Any]]] = {
    "/api/v1/healthz": ("healthz", lambda _lake: {"ok": True, "service": "trustops-assessment"}),
    "/api/v1/ingestion/status": ("ingestion.status", build_ingestion_status),
    "/api/v1/posture/current": ("posture.current", build_current_posture),
    "/api/v1/graph/coverage": ("graph.coverage", analyze_coverage),
}

# Route -> (resource name, loader) for endpoints returning a row collection.
COLLECTION_LOADERS: dict[str, tuple[str, Callable[[Path], list[JsonObject]]]] = {
    "/api/v1/controls": (
        "controls",
        lambda lake: read_jsonl(lake / "gold" / "control_posture.jsonl", missing_ok=True, base_dir=lake),
    ),
    "/api/v1/control-tests": (
        "control-tests",
        lambda lake: read_jsonl(lake / "gold" / "control_tests.jsonl", missing_ok=True, base_dir=lake),
    ),
    "/api/v1/evidence": (
        "evidence",
        lambda lake: read_jsonl(lake / "silver" / "normalized_events.jsonl", missing_ok=True, base_dir=lake),
    ),
    "/api/v1/evidence/freshness": (
        "evidence.freshness",
        lambda lake: read_jsonl(lake / "gold" / "evidence_freshness.jsonl", missing_ok=True, base_dir=lake),
    ),
    "/api/v1/assets": (
        "assets",
        lambda lake: read_jsonl(lake / "gold" / "asset_risk.jsonl", missing_ok=True, base_dir=lake),
    ),
    "/api/v1/violations": ("violations", lambda lake: build_current_posture(lake)["violations"]),
    "/api/v1/snapshots": ("snapshots", list_snapshots),
}

# Resources that also accept writes via handle_post.
_WRITABLE = {"/api/v1/snapshots": ["POST"]}


def _suffix_match(path: str, prefix: str, suffix: str) -> str | None:
    if not path.startswith(prefix) or not path.endswith(suffix):
        return None
    rest = path[len(prefix) : -len(suffix)]
    return rest or None


def _connector_action(path: str, action: str) -> str | None:
    return _suffix_match(path, "/api/v1/connectors/", f"/{action}")


def required_post_scope(path: str) -> str:
    """Return the RBAC scope required to mutate a v1 route."""
    if path == "/api/v1/snapshots":
        return "snapshot"
    if _connector_action(path, "configure") is not None:
        return "connector_manage"
    if _connector_action(path, "discover") is not None:
        return "connector_manage"
    if _connector_action(path, "probe") is not None:
        return "connector_manage"
    return "write"


# Typed write/read routes served only by the FastAPI server (``server_app``).
#
# ``SINGLETON_LOADERS`` / ``COLLECTION_LOADERS`` above cover the lake-backed
# read surface that both deployment modes share. The remediation workflow,
# tagging, saved views, and insights routes are stateful (database-backed) and
# live only in server mode, so they are not in the loader tables -- yet they are
# the verbs an agent needs to *act*. Enumerating them here keeps the
# self-describing ``GET /api/v1`` catalog honest about the full contract.
#
# Paths, methods, and scopes are kept in lockstep with the ``@app.<verb>``
# decorators and their ``Depends(_require_*)`` defaults in ``server_app``.
EXTENDED_RESOURCES: list[JsonObject] = [
    {
        "resource": "agent-runs",
        "path": "/api/v1/agent-runs",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "write"],
        "query": ["limit", "harness", "status"],
    },
    {
        "resource": "agent-runs",
        "path": "/api/v1/agent-runs/{run_id}",
        "kind": "singleton",
        "methods": ["GET"],
        "scopes": ["read"],
        "path_params": ["run_id"],
    },
    {
        "resource": "agent-runs.decisions",
        "path": "/api/v1/agent-runs/{run_id}/decisions/{decision_index}/approve",
        "kind": "action",
        "methods": ["POST"],
        "scopes": ["write"],
        "path_params": ["run_id", "decision_index"],
    },
    {
        "resource": "remediation.tasks",
        "path": "/api/v1/remediation/tasks",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "write"],
    },
    {
        "resource": "remediation.tasks",
        "path": "/api/v1/remediation/tasks/{task_id}",
        "kind": "singleton",
        "methods": ["GET", "PATCH"],
        "scopes": ["read", "write"],
        "path_params": ["task_id"],
    },
    {
        "resource": "remediation.evidence-requests",
        "path": "/api/v1/remediation/evidence-requests",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "evidence_request"],
    },
    {
        "resource": "remediation.evidence-requests",
        "path": "/api/v1/remediation/evidence-requests/{request_id}",
        "kind": "singleton",
        "methods": ["PATCH"],
        "scopes": ["evidence_request"],
        "path_params": ["request_id"],
    },
    {
        "resource": "remediation.exceptions",
        "path": "/api/v1/remediation/exceptions",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "control_manage"],
    },
    {
        "resource": "remediation.exceptions",
        "path": "/api/v1/remediation/exceptions/{exception_id}",
        "kind": "singleton",
        "methods": ["DELETE"],
        "scopes": ["control_manage"],
        "path_params": ["exception_id"],
    },
    {
        "resource": "risks",
        "path": "/api/v1/risks",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "write"],
    },
    {
        "resource": "risks",
        "path": "/api/v1/risks/{risk_id}",
        "kind": "singleton",
        "methods": ["PATCH", "DELETE"],
        "scopes": ["write"],
        "path_params": ["risk_id"],
    },
    {
        "resource": "tags",
        "path": "/api/v1/tags",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "write"],
    },
    {
        "resource": "tags",
        "path": "/api/v1/tags/{tag_id}",
        "kind": "singleton",
        "methods": ["DELETE"],
        "scopes": ["write"],
        "path_params": ["tag_id"],
    },
    {
        "resource": "tags.attach",
        "path": "/api/v1/tags/attach",
        "kind": "singleton",
        "methods": ["POST"],
        "scopes": ["write"],
    },
    {
        "resource": "tags.detach",
        "path": "/api/v1/tags/detach",
        "kind": "singleton",
        "methods": ["POST"],
        "scopes": ["write"],
    },
    {
        "resource": "tags.for",
        "path": "/api/v1/tags/for",
        "kind": "collection",
        "methods": ["GET"],
        "scopes": ["read"],
        "query": ["entity_type", "entity_id"],
    },
    {
        "resource": "saved-views",
        "path": "/api/v1/saved-views",
        "kind": "collection",
        "methods": ["GET", "POST"],
        "scopes": ["read", "write"],
    },
    {
        "resource": "saved-views",
        "path": "/api/v1/saved-views/{view_id}",
        "kind": "singleton",
        "methods": ["DELETE"],
        "scopes": ["write"],
        "path_params": ["view_id"],
    },
    {
        "resource": "insights.timeseries",
        "path": "/api/v1/insights/timeseries",
        "kind": "collection",
        "methods": ["GET"],
        "scopes": ["read"],
        "query": ["limit"],
    },
    {
        "resource": "insights.remediation",
        "path": "/api/v1/insights/remediation",
        "kind": "singleton",
        "methods": ["GET"],
        "scopes": ["read"],
    },
    {
        "resource": "insights.capture",
        "path": "/api/v1/insights/capture",
        "kind": "singleton",
        "methods": ["POST"],
        "scopes": ["write"],
    },
]


def resource_catalog() -> list[JsonObject]:
    """Self-describing list of v1 resources, for headless/agent discovery."""
    catalog: list[JsonObject] = []
    catalog.extend(
        [
            {
                "resource": "connectors",
                "path": "/api/v1/connectors",
                "kind": "collection",
                "methods": ["GET"],
                "scopes": ["read"],
            },
            {
                "resource": "connector.runs",
                "path": "/api/v1/connectors/{connector_id}/runs",
                "kind": "collection",
                "methods": ["GET"],
                "scopes": ["read"],
                "path_params": ["connector_id"],
            },
            {
                "resource": "connector.configure",
                "path": "/api/v1/connectors/{connector_id}/configure",
                "kind": "action",
                "methods": ["POST"],
                "scopes": ["connector_manage"],
                "path_params": ["connector_id"],
            },
            {
                "resource": "connector.discover",
                "path": "/api/v1/connectors/{connector_id}/discover",
                "kind": "action",
                "methods": ["POST"],
                "scopes": ["connector_manage"],
                "path_params": ["connector_id"],
            },
            {
                "resource": "connector.probe",
                "path": "/api/v1/connectors/{connector_id}/probe",
                "kind": "action",
                "methods": ["POST"],
                "scopes": ["connector_manage"],
                "path_params": ["connector_id"],
            },
            {
                "resource": "connector.sync",
                "path": "/api/v1/connectors/{connector_id}/sync",
                "kind": "action",
                "methods": ["POST"],
                "scopes": ["connector_manage"],
                "path_params": ["connector_id"],
            },
        ]
    )
    catalog.append(
        {
            "resource": "framework.detail",
            "path": "/api/v1/frameworks/{framework_id}/detail",
            "kind": "singleton",
            "methods": ["GET"],
            "path_params": ["framework_id"],
        }
    )
    catalog.append(
        {
            "resource": "posture.as_of",
            "path": "/api/v1/posture/as-of",
            "kind": "singleton",
            "methods": ["GET"],
            "query": ["as_of"],
        }
    )
    catalog.append(
        {
            "resource": "snapshots.integrity",
            "path": "/api/v1/snapshots/integrity",
            "kind": "singleton",
            "methods": ["GET"],
        }
    )
    catalog.append(
        {
            "resource": "tracking.integrity",
            "path": "/api/v1/tracking/integrity",
            "kind": "singleton",
            "methods": ["GET"],
        }
    )
    catalog.append(
        {
            "resource": "catalog.bundle",
            "path": "/api/v1/catalog/bundle",
            "kind": "singleton",
            "methods": ["GET"],
            "query": ["as_of", "full"],
        }
    )
    catalog.append(
        {
            "resource": "controls.as_of",
            "path": "/api/v1/controls/as-of",
            "kind": "singleton",
            "methods": ["GET"],
            "query": ["as_of"],
        }
    )
    catalog.append(
        {
            "resource": "control.history",
            "path": "/api/v1/controls/{control_id}/history",
            "kind": "singleton",
            "methods": ["GET"],
            "path_params": ["control_id"],
        }
    )
    for path, (name, _loader) in SINGLETON_LOADERS.items():
        catalog.append({"resource": name, "path": path, "kind": "singleton", "methods": ["GET"]})
    for path, (name, _loader) in COLLECTION_LOADERS.items():
        catalog.append(
            {
                "resource": name,
                "path": path,
                "kind": "collection",
                "methods": ["GET", *_WRITABLE.get(path, [])],
                "query": ["limit", "offset", "sort", "<field>=<value>"],
            }
        )
    catalog.extend(dict(entry) for entry in EXTENDED_RESOURCES)
    return sorted(catalog, key=lambda row: row["path"])


def index_payload() -> JsonObject:
    """Return the self-describing v1 contract index."""
    return {
        "api_version": API_VERSION,
        "resources": resource_catalog(),
        "collection_controls": {
            "limit": "1-1000 (default 100)",
            "offset": ">= 0",
            "sort": "field, or -field for descending",
            "filters": "any field=value (comma-separated values = OR)",
        },
        "auth": {
            "api_key": "Authorization: Bearer <token>",
            "session": "httpOnly cookie via OIDC/SAML SSO",
            "methods_endpoint": "/api/v1/auth/methods",
        },
        "streams": ["/api/v1/stream"],
        "openapi": "/openapi.json",
        "docs": "/docs",
    }


def filter_collection(rows: list[JsonObject], params: Params) -> tuple[list[JsonObject], dict[str, list[str]]]:
    """Apply ``field=value`` query filters (comma-separated, list-field aware)."""
    reserved = {"limit", "offset", "sort", "cursor"}
    filters = {
        key: [value for raw in values for value in raw.split(",") if value]
        for key, values in params.items()
        if key not in reserved
    }
    if not filters:
        return rows, {}

    def matches(row: JsonObject) -> bool:
        for field, expected_values in filters.items():
            actual = row.get(field)
            if actual is None:
                return False
            if isinstance(actual, list):
                actual_values = {str(item) for item in actual}
                if not any(expected in actual_values for expected in expected_values):
                    return False
            elif str(actual) not in expected_values:
                return False
        return True

    return [row for row in rows if matches(row)], filters


def sort_collection(rows: list[JsonObject], params: Params) -> tuple[list[JsonObject], str | None]:
    """Apply ``sort=field`` / ``sort=-field`` ordering; ``None`` values sort last."""
    sort = (params.get("sort") or [None])[0]
    if not sort:
        return rows, None
    reverse = sort.startswith("-")
    field = sort[1:] if reverse else sort
    if not field:
        raise ValueError("sort must name a field, optionally prefixed with '-'")
    sortable = [row for row in rows if row.get(field) is not None]
    missing = [row for row in rows if row.get(field) is None]

    def sort_key(row: JsonObject) -> tuple[int, float | str]:
        value = row[field]
        if isinstance(value, int | float):
            return (0, float(value))
        return (1, str(value))

    return sorted(sortable, key=sort_key, reverse=reverse) + missing, sort


def encode_cursor(offset: int) -> str:
    """Encode a next-page start ``offset`` into an opaque base64 cursor.

    The cursor today is an *offset cursor*: it carries the absolute start
    offset of the next page as base64-encoded JSON (``{"offset": N}``). This
    keeps the public contract opaque so callers treat it as a token to follow
    rather than a number to compute, while a future revision can switch the
    payload to a keyset/streaming position over the SQL mart without changing
    the wire shape. The applied limit/sort/filters are not embedded — the page
    boundary is the offset; callers should keep limit/sort/filters stable
    across pages (the existing ``meta`` echoes them back for that purpose).
    """
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> int:
    """Decode an opaque cursor produced by :func:`encode_cursor` to an offset.

    Raises ``ValueError`` (the same path as a bad ``limit``/``offset``) when the
    cursor is not valid base64, not JSON, or does not carry a non-negative
    integer ``offset``.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw)
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ValueError("invalid cursor") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid cursor")
    offset = payload.get("offset")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("invalid cursor")
    return offset


def paginate_collection(rows: list[JsonObject], params: Params) -> tuple[list[JsonObject], int, int]:
    """Apply ``limit`` (1-1000, default 100) and a start offset.

    The start offset comes from an opaque ``cursor`` when present (see
    :func:`encode_cursor`); ``cursor`` takes precedence over a raw ``offset``
    when both are supplied. Otherwise it falls back to ``offset`` (>=0,
    default 0). An invalid cursor raises ``ValueError`` like a bad limit/offset.
    """
    try:
        limit = int((params.get("limit") or ["100"])[0])
    except ValueError as exc:
        raise ValueError("limit and offset must be integers") from exc
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    cursor_values = params.get("cursor") or []
    if cursor_values and cursor_values[0]:
        offset = decode_cursor(cursor_values[0])
    else:
        try:
            offset = int((params.get("offset") or ["0"])[0])
        except ValueError as exc:
            raise ValueError("limit and offset must be integers") from exc
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
    return rows[offset : offset + limit], limit, offset


def collection_response(resource: str, rows: list[JsonObject], params: Params) -> JsonObject:
    """Filter, sort, and paginate ``rows`` into a v1 collection envelope.

    The ``meta`` always includes ``next_cursor``: an opaque cursor for the next
    page when more filtered rows remain (``offset + limit < count``), else
    ``None``. The offset/limit/count/returned/sort/filters fields are unchanged,
    so offset-based pagination keeps working exactly as before.
    """
    filtered_rows, applied_filters = filter_collection(rows, params)
    sorted_rows, sort = sort_collection(filtered_rows, params)
    page_rows, limit, offset = paginate_collection(sorted_rows, params)
    count = len(filtered_rows)
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < count else None
    return envelope(
        resource,
        page_rows,
        meta={
            "count": count,
            "returned": len(page_rows),
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "filters": applied_filters,
            "next_cursor": next_cursor,
        },
    )


def handle_get(path: str, params: Params, lake_dir: str | Path) -> tuple[HTTPStatus, JsonObject]:
    """Resolve a v1 GET into an ``(status, body)`` pair."""
    lake = resolve_path(lake_dir)
    if path == "/api/v1":
        return HTTPStatus.OK, envelope("index", index_payload())
    if path == "/api/v1/connectors":
        rows = build_catalog_view(lake)
        return HTTPStatus.OK, collection_response("connectors", rows, params)
    connector_runs = _suffix_match(path, "/api/v1/connectors/", "/runs")
    if connector_runs is not None:
        rows = list_runs(lake, connector_runs)
        try:
            body = collection_response("connector.runs", rows, params)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", "invalid request parameters", resource="connector.runs"
            )
        body["meta"]["connector_id"] = connector_runs
        return HTTPStatus.OK, body
    if path.startswith("/api/v1/frameworks/") and path.endswith("/detail"):
        framework_id = path[len("/api/v1/frameworks/") : -len("/detail")]
        detail = build_framework_detail(framework_id, lake)
        if detail is None:
            return HTTPStatus.NOT_FOUND, error_envelope("not_found", "unknown framework", resource="framework.detail")
        return HTTPStatus.OK, envelope("framework.detail", detail)
    if path == "/api/v1/snapshots/integrity":
        return HTTPStatus.OK, envelope("snapshots.integrity", verify_snapshot_chain(lake))
    if path == "/api/v1/tracking/integrity":
        return HTTPStatus.OK, envelope("tracking.integrity", verify_tracking_chain(lake))
    if path == "/api/v1/catalog/bundle":
        from security_lakehouse.catalog_versions import bundle_summary, compute_bundle

        as_of_values = params.get("as_of") or []
        as_of = as_of_values[0] if as_of_values else None
        full = (params.get("full") or [""])[0] in ("1", "true", "yes")
        try:
            data = compute_bundle(as_of=as_of) if full else bundle_summary(as_of=as_of)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", f"invalid 'as_of' value: {as_of!r}", resource="catalog.bundle"
            )
        return HTTPStatus.OK, envelope("catalog.bundle", data)
    if path == "/api/v1/controls/as-of":
        from security_lakehouse.catalog_versions import controls_as_of

        as_of_values = params.get("as_of") or []
        as_of = as_of_values[0] if as_of_values else ""
        if not as_of:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", "query parameter 'as_of' is required", resource="controls.as_of"
            )
        try:
            controls = controls_as_of(as_of)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", f"invalid 'as_of' value: {as_of!r}", resource="controls.as_of"
            )
        return HTTPStatus.OK, envelope(
            "controls.as_of", {"as_of": as_of, "control_count": len(controls), "controls": list(controls.values())}
        )
    if path.startswith("/api/v1/controls/") and path.endswith("/history"):
        from security_lakehouse.catalog_versions import control_history

        control_id = path[len("/api/v1/controls/") : -len("/history")]
        versions = control_history(control_id)
        if not versions:
            return HTTPStatus.NOT_FOUND, error_envelope(
                "not_found", f"unknown control {control_id}", resource="control.history"
            )
        return HTTPStatus.OK, envelope("control.history", {"control_id": control_id, "versions": versions})
    if path == "/api/v1/posture/as-of":
        as_of_values = params.get("as_of") or []
        as_of = as_of_values[0] if as_of_values else ""
        if not as_of:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", "query parameter 'as_of' is required", resource="posture.as_of"
            )
        try:
            data = posture_as_of(lake, as_of=as_of)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", f"invalid 'as_of' value: {as_of!r}", resource="posture.as_of"
            )
        return HTTPStatus.OK, envelope("posture.as_of", data)
    singleton = SINGLETON_LOADERS.get(path)
    if singleton is not None:
        resource, loader = singleton
        return HTTPStatus.OK, envelope(resource, loader(lake))
    collection = COLLECTION_LOADERS.get(path)
    if collection is not None:
        resource, loader = collection
        try:
            return HTTPStatus.OK, collection_response(resource, loader(lake), params)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "bad_request", "invalid request parameters", resource=resource
            )
    return HTTPStatus.NOT_FOUND, error_envelope("not_found", f"unknown route {path}")


def handle_post(path: str, body: JsonObject | None, lake_dir: str | Path) -> tuple[HTTPStatus, JsonObject]:
    """Resolve a v1 POST into an ``(status, body)`` pair."""
    lake = resolve_path(lake_dir)
    payload = body or {}
    if path == "/api/v1/snapshots":
        reason = str(payload.get("reason") or "api_request")
        snapshot_path = write_assessment_snapshot(lake, reason=reason)
        return HTTPStatus.CREATED, envelope("snapshots", {"snapshot_path": str(snapshot_path), "reason": reason})
    configure = _connector_action(path, "configure")
    if configure is not None:
        state = str(payload.get("state") or "enabled").lower()
        credentials = payload.get("credentials") or {}
        options = payload.get("options") or {}
        error = configure_payload_error(
            connector_id=configure,
            state=state,
            credentials=credentials,
            options=options,
        )
        if error:
            return HTTPStatus.BAD_REQUEST, error_envelope("bad_request", error, resource="connector.configure")
        error = enablement_probe_error(
            lake,
            connector_id=configure,
            state=state,
            credentials=credentials,
            options=options,
        )
        if error:
            return HTTPStatus.BAD_REQUEST, error_envelope("bad_request", error, resource="connector.configure")
        record = append_config_event(
            lake,
            connector_id=configure,
            state=state,
            actor=str(payload.get("actor") or "console"),
            credentials=credentials,
            options=options,
        )
        return HTTPStatus.CREATED, envelope("connector.configure", record)
    discover = _connector_action(path, "discover")
    if discover is not None:
        record = run_discovery(
            lake,
            connector_id=discover,
            actor=str(payload.get("actor") or "console"),
            credentials=payload.get("credentials") if "credentials" in payload else None,
            options=payload.get("options") if "options" in payload else None,
        )
        return HTTPStatus.CREATED, envelope("connector.discover", record)
    probe = _connector_action(path, "probe")
    if probe is not None:
        record = run_probe(
            lake,
            connector_id=probe,
            actor=str(payload.get("actor") or "console"),
            credentials=payload.get("credentials") if "credentials" in payload else None,
            options=payload.get("options") if "options" in payload else None,
        )
        return HTTPStatus.CREATED, envelope("connector.probe", record)
    sync = _connector_action(path, "sync")
    if sync is not None:
        try:
            result = run_connector_sync(
                lake,
                connector_id=sync,
                actor=str(payload.get("actor") or "console"),
            )
        except ConnectorSyncError:
            # The run is persisted with its outcome; surface a generic failure
            # here so no exception detail crosses the HTTP boundary. The reason
            # is available via GET /api/v1/connectors/{id}/runs.
            return HTTPStatus.BAD_REQUEST, error_envelope(
                "sync_failed", "connector sync failed; see the connector runs for details", resource="connector.sync"
            )
        return HTTPStatus.CREATED, envelope(
            "connector.sync",
            {
                "connector_id": result.connector_id,
                "result": result.result,
                "evidence_count": result.evidence_count,
                "materialized": result.materialized,
                "run": result.run,
            },
        )
    return HTTPStatus.NOT_FOUND, error_envelope("not_found", f"unknown route {path}")
