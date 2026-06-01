"""The self-describing v1 catalog must advertise the write/typed surface.

``resource_catalog()`` used to enumerate only the lake-backed read resources
(``SINGLETON_LOADERS`` + ``COLLECTION_LOADERS``), hiding the remediation,
tagging, saved-view, and insights routes from agents discovering the contract
via ``GET /api/v1``. These assertions lock the catalog to the typed routes.
"""

from __future__ import annotations

from security_lakehouse import api_v1


def _by_path(catalog: list[dict], path: str) -> dict:
    return next(row for row in catalog if row["path"] == path)


def test_catalog_lists_extended_write_resources() -> None:
    catalog = api_v1.resource_catalog()
    paths = {row["path"] for row in catalog}
    assert {
        "/api/v1/remediation/tasks",
        "/api/v1/remediation/evidence-requests",
        "/api/v1/remediation/exceptions",
        "/api/v1/tags",
        "/api/v1/tags/attach",
        "/api/v1/tags/detach",
        "/api/v1/tags/for",
        "/api/v1/saved-views",
        "/api/v1/insights/timeseries",
        "/api/v1/insights/remediation",
        "/api/v1/insights/capture",
    } <= paths


def test_catalog_advertises_write_methods() -> None:
    catalog = api_v1.resource_catalog()

    tasks = _by_path(catalog, "/api/v1/remediation/tasks")
    assert tasks["resource"] == "remediation.tasks"
    assert "POST" in tasks["methods"]

    task_item = _by_path(catalog, "/api/v1/remediation/tasks/{task_id}")
    assert "PATCH" in task_item["methods"]
    assert task_item["path_params"] == ["task_id"]

    tags = _by_path(catalog, "/api/v1/tags")
    assert tags["resource"] == "tags"
    assert "POST" in tags["methods"]

    views = _by_path(catalog, "/api/v1/saved-views")
    assert views["resource"] == "saved-views"
    assert "POST" in views["methods"]

    capture = _by_path(catalog, "/api/v1/insights/capture")
    assert "POST" in capture["methods"]


def test_catalog_carries_required_scopes() -> None:
    catalog = api_v1.resource_catalog()

    timeseries = _by_path(catalog, "/api/v1/insights/timeseries")
    assert timeseries["resource"] == "insights.timeseries"
    assert timeseries["methods"] == ["GET"]
    assert timeseries["scopes"] == ["read"]

    exceptions = _by_path(catalog, "/api/v1/remediation/exceptions")
    assert "control_manage" in exceptions["scopes"]

    evidence = _by_path(catalog, "/api/v1/remediation/evidence-requests")
    assert "evidence_request" in evidence["scopes"]


def test_catalog_remains_sorted_by_path() -> None:
    catalog = api_v1.resource_catalog()
    paths = [row["path"] for row in catalog]
    assert paths == sorted(paths)
