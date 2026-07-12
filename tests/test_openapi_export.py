"""OpenAPI export drift checks for committed docs/api/openapi.v1.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from security_lakehouse.server_app import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "docs" / "api" / "openapi.v1.json"
CATALOG = ROOT / "docs" / "api" / "resource-catalog.v1.json"


def _generate_openapi() -> dict:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        return create_app(tmp, require_auth=False).openapi()


def test_committed_openapi_file_exists() -> None:
    assert COMMITTED.is_file(), "run: make openapi-export"


def test_committed_openapi_matches_generator() -> None:
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    generated = _generate_openapi()
    assert committed == generated


def test_openapi_documents_fastapi_surface() -> None:
    spec = json.loads(COMMITTED.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    for path in (
        "/api/v1",
        "/api/v1/agent-runs",
        "/api/v1/audit-log",
    ):
        assert path in paths, path


def test_committed_resource_catalog_matches_generator() -> None:
    from security_lakehouse import api_v1

    assert CATALOG.is_file(), "run: make openapi-export"
    committed = json.loads(CATALOG.read_text(encoding="utf-8"))
    generated = {"resources": api_v1.resource_catalog()}
    assert committed == generated


def test_resource_catalog_supports_agent_skills() -> None:
    from security_lakehouse import api_v1

    paths = {row["path"] for row in api_v1.resource_catalog()}
    for path in (
        "/api/v1/posture/current",
        "/api/v1/connectors/{connector_id}/probe",
        "/api/v1/connectors/{connector_id}/configure",
        "/api/v1/connectors/{connector_id}/sync",
        "/api/v1/ingestion/eval",
        "/api/v1/agent-runs",
    ):
        assert path in paths, path
