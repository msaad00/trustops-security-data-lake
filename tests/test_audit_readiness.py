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
from security_lakehouse.db import vendor_assessments as vendor_assessment_db  # noqa: E402
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
    assert "vendor_risk" in body
    assert body["vendor_risk"]["total"] == 0


def test_audit_readiness_vendor_gaps(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="vendor-audit", name="Vendor Audit")
        create_user(session, tenant_id=tenant.id, email="admin@vendor-audit.test", role="admin")
        vendor_assessment_db.create_assessment(
            session,
            tenant_id=tenant.id,
            vendor_name="Cloud SaaS",
            template_id="soc2-vendor-standard",
            due_at=datetime.now(UTC) - timedelta(days=3),
        )
        session.commit()
        data = build_audit_readiness(lake=tmp_path, session=session, tenant_id=tenant.id)
    assert data["vendor_risk"]["total"] == 1
    assert data["vendor_risk"]["overdue"] == 1
    assert any(gap["id"] == "vendor_overdue" for gap in data["gaps"])


def test_audit_readiness_personnel_summary(tmp_path: Path) -> None:
    from security_lakehouse.db import access_reviews as access_reviews_db
    from security_lakehouse.services import access_reviews as access_review_services

    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="personnel-audit", name="Personnel Audit")
        create_user(session, tenant_id=tenant.id, email="admin@personnel-audit.test", role="admin")
        campaign = access_review_services.create_campaign(session, tenant_id=tenant.id, name="Q2 users")
        access_review_services.set_campaign_status(
            session, tenant_id=tenant.id, campaign_id=campaign["id"], status="active"
        )
        access_reviews_db.add_item(
            session,
            tenant_id=tenant.id,
            campaign_id=campaign["id"],
            subject_id="user-1",
            subject_name="Alice",
        )
        session.commit()
        data = build_audit_readiness(lake=tmp_path, session=session, tenant_id=tenant.id)

    assert data["personnel"]["active_campaigns"] == 1
    assert data["personnel"]["pending_certifications"] == 1
    assert any(gap["id"] == "personnel_idp" for gap in data["gaps"])
    personnel_row = next(row for row in data["workflow_coverage"]["checklist"] if row["id"] == "personnel_tracking")
    assert personnel_row["shipped"] is True


def test_audit_readiness_stale_evidence_gap(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="stale-audit", name="Stale Audit")
        create_user(session, tenant_id=tenant.id, email="admin@stale-audit.test", role="admin")
        session.commit()
        data = build_audit_readiness(lake=tmp_path, session=session, tenant_id=tenant.id)
    assert data["evidence_freshness"]["stale_count"] > 0
    assert any(gap["id"] == "stale_evidence" for gap in data["gaps"])


def test_audit_readiness_auditor_share_gap(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="share-audit", name="Share Audit")
        create_user(session, tenant_id=tenant.id, email="admin@share-audit.test", role="admin")
        session.commit()
        data = build_audit_readiness(lake=tmp_path, session=session, tenant_id=tenant.id)
    assert any(gap["id"] == "auditor_share" for gap in data["gaps"])


def test_audit_readiness_api_requires_auth(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/v1/platform/audit-readiness")
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
