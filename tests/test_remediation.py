"""Remediation workflow tests: data model + API (RBAC, SLA/overdue, lifecycle)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.db import remediation  # noqa: E402
from security_lakehouse.db.base import session_scope  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def env(tmp_path: Path):
    _seed_lake(tmp_path)
    app = create_app(tmp_path)  # auth required
    client = TestClient(app)
    tokens: dict[str, str] = {}
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        for role in ("read_only", "auditor", "contributor", "security_admin", "admin"):
            user = create_user(session, tenant_id=tenant.id, email=f"{role}@acme.test", role=role)
            _key, token = create_api_key(
                session, tenant_id=tenant.id, user_id=user.id, expires_at=datetime.now(UTC) + timedelta(minutes=10)
            )
            tokens[role] = token
    return app, client, tokens


# --- data-model layer --------------------------------------------------------


def test_task_overdue_is_derived(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        overdue = remediation.create_task(session, tenant_id=tenant.id, title="late", due_at=past)
        on_time = remediation.create_task(session, tenant_id=tenant.id, title="soon", due_at=future)
        assert overdue.is_overdue() is True
        assert on_time.is_overdue() is False
        # resolving clears overdue
        remediation.update_task(session, tenant_id=tenant.id, task_id=overdue.id, changes={"status": "resolved"})
        assert overdue.is_overdue() is False
        assert overdue.resolved_at is not None


def test_task_list_filters(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        remediation.create_task(session, tenant_id=tenant.id, title="a", owner="alice", priority="high")
        remediation.create_task(session, tenant_id=tenant.id, title="b", owner="bob")
        assert len(remediation.list_tasks(session, tenant_id=tenant.id)) == 2
        assert len(remediation.list_tasks(session, tenant_id=tenant.id, owner="alice")) == 1


def test_invalid_priority_and_status_rejected(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        with pytest.raises(ValueError, match="priority"):
            remediation.create_task(session, tenant_id=tenant.id, title="x", priority="urgent")
        task = remediation.create_task(session, tenant_id=tenant.id, title="x")
        with pytest.raises(ValueError, match="status"):
            remediation.update_task(session, tenant_id=tenant.id, task_id=task.id, changes={"status": "wat"})


def test_exception_active_and_revoke(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        exc = remediation.create_exception(
            session, tenant_id=tenant.id, control_id="SOC2-CC6.1", reason="risk-accepted"
        )
        assert exc.is_active() is True
        remediation.revoke_exception(session, tenant_id=tenant.id, exception_id=exc.id)
        assert exc.is_active() is False
        assert exc.status == "revoked"


# --- API layer ---------------------------------------------------------------


def test_tasks_require_auth(env) -> None:
    _app, client, _tokens = env
    assert client.get("/api/v1/remediation/tasks").status_code == HTTPStatus.UNAUTHORIZED


def test_task_crud_and_rbac(env) -> None:
    _app, client, tokens = env
    # read_only can list but not create
    assert client.get("/api/v1/remediation/tasks", headers=_bearer(tokens["read_only"])).status_code == HTTPStatus.OK
    denied = client.post("/api/v1/remediation/tasks", json={"title": "x"}, headers=_bearer(tokens["read_only"]))
    assert denied.status_code == HTTPStatus.FORBIDDEN

    created = client.post(
        "/api/v1/remediation/tasks",
        json={"title": "Rotate keys", "control_id": "SOC2-CC6.1", "priority": "high"},
        headers=_bearer(tokens["contributor"]),
    )
    assert created.status_code == HTTPStatus.CREATED
    task = created.json()["data"]
    assert task["status"] == "open"
    assert task["overdue"] is False

    patched = client.patch(
        f"/api/v1/remediation/tasks/{task['id']}",
        json={"status": "resolved"},
        headers=_bearer(tokens["contributor"]),
    )
    assert patched.status_code == HTTPStatus.OK
    assert patched.json()["data"]["status"] == "resolved"
    assert patched.json()["data"]["resolved_at"] is not None


def test_task_bad_status_is_400(env) -> None:
    _app, client, tokens = env
    created = client.post("/api/v1/remediation/tasks", json={"title": "x"}, headers=_bearer(tokens["contributor"]))
    task_id = created.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/remediation/tasks/{task_id}", json={"status": "nope"}, headers=_bearer(tokens["contributor"])
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_evidence_request_lifecycle(env) -> None:
    _app, client, tokens = env
    created = client.post(
        "/api/v1/remediation/evidence-requests",
        json={"control_id": "SOC2-CC6.1", "requested_from": "platform"},
        headers=_bearer(tokens["contributor"]),
    )
    assert created.status_code == HTTPStatus.CREATED
    req_id = created.json()["data"]["id"]
    fulfilled = client.patch(
        f"/api/v1/remediation/evidence-requests/{req_id}",
        json={"status": "fulfilled"},
        headers=_bearer(tokens["contributor"]),
    )
    assert fulfilled.json()["data"]["status"] == "fulfilled"
    assert fulfilled.json()["data"]["fulfilled_at"] is not None


def test_exceptions_require_control_manage(env) -> None:
    _app, client, tokens = env
    body = {"control_id": "SOC2-CC6.1", "reason": "accepted"}
    # contributor lacks control_manage
    assert (
        client.post("/api/v1/remediation/exceptions", json=body, headers=_bearer(tokens["contributor"])).status_code
        == HTTPStatus.FORBIDDEN
    )
    created = client.post("/api/v1/remediation/exceptions", json=body, headers=_bearer(tokens["security_admin"]))
    assert created.status_code == HTTPStatus.CREATED
    exc_id = created.json()["data"]["id"]
    assert created.json()["data"]["active"] is True
    revoked = client.delete(f"/api/v1/remediation/exceptions/{exc_id}", headers=_bearer(tokens["security_admin"]))
    assert revoked.status_code == HTTPStatus.OK
    assert revoked.json()["data"]["status"] == "revoked"


@pytest.mark.parametrize("role", ["admin", "security_admin", "contributor", "auditor", "read_only"])
def test_evidence_request_operator_permissions(env, role: str) -> None:
    _app, client, tokens = env
    response = client.post(
        "/api/v1/remediation/evidence-requests",
        headers=_bearer(tokens[role]),
        json={"control_id": "SOC2-CC6.1", "requested_from": "evidence-owner"},
    )
    allowed = role in {"admin", "security_admin", "contributor"}
    assert response.status_code == (HTTPStatus.CREATED if allowed else HTTPStatus.FORBIDDEN)
    if allowed:
        created = response.json()["data"]
        listed = client.get("/api/v1/remediation/evidence-requests", headers=_bearer(tokens[role])).json()["data"]
        assert any(row["id"] == created["id"] and row["control_id"] == "SOC2-CC6.1" for row in listed)
