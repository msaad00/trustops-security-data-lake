"""Transport-agnostic ``/api/v1`` contract for headless humans and agents.

Both deployment modes build their versioned responses from this module:

- the zero-dependency stdlib server (:mod:`security_lakehouse.server`)
- the optional FastAPI server (:mod:`security_lakehouse.server_app`)

Keeping the envelope, collection controls, and route table here means the
agent-facing contract cannot drift between local mode and server mode.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from pathlib import Path
from typing import Any

from security_lakehouse.assessment import build_current_posture, write_assessment_snapshot
from security_lakehouse.framework_detail import build_framework_detail
from security_lakehouse.io import read_jsonl

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
    "/api/v1/posture/current": ("posture.current", build_current_posture),
}

# Route -> (resource name, loader) for endpoints returning a row collection.
COLLECTION_LOADERS: dict[str, tuple[str, Callable[[Path], list[JsonObject]]]] = {
    "/api/v1/controls": ("controls", lambda lake: read_jsonl(lake / "gold" / "control_posture.jsonl", missing_ok=True)),
    "/api/v1/control-tests": (
        "control-tests",
        lambda lake: read_jsonl(lake / "gold" / "control_tests.jsonl", missing_ok=True),
    ),
    "/api/v1/evidence": (
        "evidence",
        lambda lake: read_jsonl(lake / "silver" / "normalized_events.jsonl", missing_ok=True),
    ),
    "/api/v1/assets": ("assets", lambda lake: read_jsonl(lake / "gold" / "asset_risk.jsonl", missing_ok=True)),
    "/api/v1/violations": ("violations", lambda lake: build_current_posture(lake)["violations"]),
    "/api/v1/snapshots": ("snapshots", list_snapshots),
}

# Resources that also accept writes via handle_post.
_WRITABLE = {"/api/v1/snapshots": ["POST"]}


def resource_catalog() -> list[JsonObject]:
    """Self-describing list of v1 resources, for headless/agent discovery."""
    catalog: list[JsonObject] = []
    catalog.append(
        {
            "resource": "framework.detail",
            "path": "/api/v1/frameworks/{framework_id}/detail",
            "kind": "singleton",
            "methods": ["GET"],
            "path_params": ["framework_id"],
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
    return sorted(catalog, key=lambda row: row["path"])


def filter_collection(rows: list[JsonObject], params: Params) -> tuple[list[JsonObject], dict[str, list[str]]]:
    """Apply ``field=value`` query filters (comma-separated, list-field aware)."""
    reserved = {"limit", "offset", "sort"}
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


def paginate_collection(rows: list[JsonObject], params: Params) -> tuple[list[JsonObject], int, int]:
    """Apply ``limit`` (1-1000, default 100) and ``offset`` (>=0, default 0)."""
    try:
        limit = int((params.get("limit") or ["100"])[0])
        offset = int((params.get("offset") or ["0"])[0])
    except ValueError as exc:
        raise ValueError("limit and offset must be integers") from exc
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    return rows[offset : offset + limit], limit, offset


def collection_response(resource: str, rows: list[JsonObject], params: Params) -> JsonObject:
    """Filter, sort, and paginate ``rows`` into a v1 collection envelope."""
    filtered_rows, applied_filters = filter_collection(rows, params)
    sorted_rows, sort = sort_collection(filtered_rows, params)
    page_rows, limit, offset = paginate_collection(sorted_rows, params)
    return envelope(
        resource,
        page_rows,
        meta={
            "count": len(filtered_rows),
            "returned": len(page_rows),
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "filters": applied_filters,
        },
    )


def handle_get(path: str, params: Params, lake_dir: str | Path) -> tuple[HTTPStatus, JsonObject]:
    """Resolve a v1 GET into an ``(status, body)`` pair."""
    lake = Path(lake_dir)
    if path.startswith("/api/v1/frameworks/") and path.endswith("/detail"):
        framework_id = path[len("/api/v1/frameworks/") : -len("/detail")]
        detail = build_framework_detail(framework_id, lake)
        if detail is None:
            return HTTPStatus.NOT_FOUND, error_envelope("not_found", "unknown framework", resource="framework.detail")
        return HTTPStatus.OK, envelope("framework.detail", detail)
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
    lake = Path(lake_dir)
    if path == "/api/v1/snapshots":
        reason = str((body or {}).get("reason") or "api_request")
        snapshot_path = write_assessment_snapshot(lake, reason=reason)
        return HTTPStatus.CREATED, envelope("snapshots", {"snapshot_path": str(snapshot_path), "reason": reason})
    return HTTPStatus.NOT_FOUND, error_envelope("not_found", f"unknown route {path}")
