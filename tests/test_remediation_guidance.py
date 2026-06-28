"""Per-control remediation guidance: resolver + API surface."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

from security_lakehouse import remediation_guidance as rg
from security_lakehouse.catalog import load_control_catalog


def test_resolves_by_risk_domain() -> None:
    control = {"control_id": "X-1", "risk_domain": "identity", "framework": "SOC 2", "title": "t"}
    out = rg.guidance_for_control(control)
    assert out["matched"] is True
    assert out["risk_domain"] == "identity"
    assert out["summary"]
    assert len(out["steps"]) >= 3
    assert "MFA" in " ".join(out["steps"])


def test_unknown_domain_falls_back_to_default() -> None:
    out = rg.guidance_for_control({"control_id": "X-2", "risk_domain": "made-up-domain"})
    assert out["matched"] is False
    assert out["summary"]  # default guidance is always present
    assert len(out["steps"]) >= 1


def test_every_catalog_control_resolves_to_steps() -> None:
    guidance = rg.load_guidance()
    for control in load_control_catalog().values():
        out = rg.guidance_for_control(control, guidance=guidance)
        assert out["steps"], f"{control['control_id']} resolved to no steps"


def test_guidance_file_is_well_formed() -> None:
    data = rg.load_guidance()
    assert data["default"]["steps"]
    for domain, entry in data["by_risk_domain"].items():
        assert entry["summary"], f"{domain} missing summary"
        assert entry["steps"], f"{domain} missing steps"


def test_remediation_endpoint(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from security_lakehouse.db.base import session_scope
    from security_lakehouse.db.repository import create_api_key, create_tenant, create_user
    from security_lakehouse.server_app import create_app
    from test_api_v1 import _seed_lake

    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="ro@acme.test", role="read_only")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # SOC2-CC6.1 is an identity-domain control in the shipped catalog.
    resp = client.get("/api/v1/controls/SOC2-CC6.1/remediation", headers=headers)
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()["data"]
    assert body["control_id"] == "SOC2-CC6.1"
    assert body["matched"] is True
    assert body["steps"]

    assert client.get("/api/v1/controls/NOPE-1/remediation", headers=headers).status_code == HTTPStatus.NOT_FOUND
