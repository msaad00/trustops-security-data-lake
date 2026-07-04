"""Audit readiness API."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.audit_readiness import build_audit_readiness  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_build_audit_readiness_fixture(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="auditco", name="Audit Co")
        create_user(session, tenant_id=tenant.id, email="admin@auditco.test", role="admin")
        session.commit()
        data = build_audit_readiness(lake=tmp_path, session=session, tenant_id=tenant.id)
    assert "audit_score" in data
    assert data["control_tests"]["total"] >= 0
    assert len(data["workflow_coverage"]["checklist"]) >= 8


def test_audit_readiness_api(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="api-audit", name="API Audit")
        user = create_user(session, tenant_id=tenant.id, email="read@api-audit.test", role="read_only")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
        session.commit()
    resp = client.get("/api/v1/platform/audit-readiness", headers=_bearer(token))
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()["data"]
    assert body["workflow_coverage"]["score"] >= 0
    assert any(row["id"] == "continuous_controls" for row in body["workflow_coverage"]["checklist"])
