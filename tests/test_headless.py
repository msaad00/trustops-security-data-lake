"""Headless surface tests: self-describing v1 index + OpenAPI contract."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse import api_v1  # noqa: E402
from security_lakehouse.db.base import session_scope  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def test_resource_catalog_lists_core_resources() -> None:
    catalog = api_v1.resource_catalog()
    paths = {row["path"] for row in catalog}
    assert {
        "/api/v1/posture/current",
        "/api/v1/controls",
        "/api/v1/evidence/freshness",
        "/api/v1/snapshots",
        "/api/v1/frameworks/{framework_id}/detail",
    } <= paths
    snapshots = next(row for row in catalog if row["path"] == "/api/v1/snapshots")
    assert "POST" in snapshots["methods"]
    detail = next(row for row in catalog if row["resource"] == "framework.detail")
    assert detail["path_params"] == ["framework_id"]


def test_v1_index_requires_auth(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/v1").status_code == HTTPStatus.UNAUTHORIZED


def test_v1_index_describes_contract(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="a@acme.test", role="read_only")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
    body = client.get("/api/v1", headers={"Authorization": f"Bearer {token}"}).json()
    data = body["data"]
    assert data["api_version"] == "v1"
    assert any(row["resource"] == "posture.current" for row in data["resources"])
    assert data["openapi"] == "/openapi.json"
    assert data["streams"] == ["/api/v1/stream"]


def test_openapi_schema_documents_surface(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    spec = create_app(tmp_path, require_auth=False).openapi()
    assert spec["info"]["title"] == "TrustOps Security Data Lake"
    paths = spec["paths"]
    for documented in (
        "/api/v1",
        "/api/v1/auth/methods",
        "/api/v1/frameworks/{framework_id}/detail",
        "/api/v1/remediation/tasks",
    ):
        assert documented in paths, documented
