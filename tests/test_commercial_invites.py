"""Commercial hosted invite API."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.commercial import invites as invite_services  # noqa: E402
from security_lakehouse.db.base import session_scope  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRUSTOPS_COMMERCIAL_HOSTED", "1")
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    tokens: dict[str, str] = {}
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        for role in ("read_only", "admin"):
            user = create_user(session, tenant_id=tenant.id, email=f"{role}@acme.test", role=role)
            _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
            tokens[role] = token
        tokens["tenant_id"] = tenant.id
    return client, tokens


def test_create_invite_requires_admin(env) -> None:
    client, tokens = env
    body = {"email": "new-hire@acme.test", "role": "contributor"}
    assert client.post("/api/v1/invites", json=body, headers=_bearer(tokens["read_only"])).status_code == (
        HTTPStatus.FORBIDDEN
    )
    created = client.post("/api/v1/invites", json=body, headers=_bearer(tokens["admin"]))
    assert created.status_code == HTTPStatus.CREATED
    assert created.json()["data"]["email"] == "new-hire@acme.test"
    assert created.json()["data"]["status"] == "pending"


def test_list_and_accept_invite(env) -> None:
    client, tokens = env
    admin = _bearer(tokens["admin"])
    created = client.post(
        "/api/v1/invites",
        json={"email": "joiner@acme.test", "role": "read_only"},
        headers=admin,
    )
    assert created.status_code == HTTPStatus.CREATED
    listed = client.get("/api/v1/invites", headers=admin)
    assert listed.status_code == HTTPStatus.OK
    assert any(row["email"] == "joiner@acme.test" for row in listed.json()["data"])

    with session_scope(client.app.state.sessionmaker) as session:
        _row, plaintext = invite_services.create_invite(
            session,
            tenant_id=tokens["tenant_id"],
            email="accept-me@acme.test",
            role="contributor",
            invited_by="admin@acme.test",
        )
        session.commit()

    accepted = client.post("/api/v1/invites/accept", json={"token": plaintext, "display_name": "Accept Me"})
    assert accepted.status_code == HTTPStatus.OK
    assert accepted.json()["data"]["email"] == "accept-me@acme.test"


def test_commercial_disabled_returns_501(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUSTOPS_COMMERCIAL_HOSTED", raising=False)
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="solo", name="Solo")
        user = create_user(session, tenant_id=tenant.id, email="admin@solo.test", role="admin")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
    resp = client.post(
        "/api/v1/invites",
        json={"email": "x@solo.test"},
        headers=_bearer(token),
    )
    assert resp.status_code == HTTPStatus.NOT_IMPLEMENTED


def test_scim_returns_501_when_disabled(env) -> None:
    client, tokens = env
    resp = client.get("/api/v1/scim/v2/Users", headers=_bearer(tokens["admin"]))
    assert resp.status_code == HTTPStatus.NOT_IMPLEMENTED


def test_scim_config_for_admin(env, monkeypatch: pytest.MonkeyPatch) -> None:
    client, tokens = env
    resp = client.get("/api/v1/platform/scim", headers=_bearer(tokens["admin"]))
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["data"]["enabled"] is False

    monkeypatch.setenv("TRUSTOPS_SCIM_ENABLED", "1")
    resp2 = client.get("/api/v1/platform/scim", headers=_bearer(tokens["admin"]))
    assert resp2.json()["data"]["enabled"] is True
