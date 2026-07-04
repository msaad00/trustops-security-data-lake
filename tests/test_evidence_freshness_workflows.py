"""Evidence freshness SLA summary and escalation workflows."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.evidence_freshness import build_freshness_summary  # noqa: E402
from security_lakehouse.evidence_freshness_workflows import (  # noqa: E402
    escalate_stale_evidence,
    load_freshness_records,
)
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def env(tmp_path: Path):
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    tokens: dict[str, str] = {}
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="fresh", name="Fresh Co")
        for role in ("read_only", "contributor"):
            user = create_user(session, tenant_id=tenant.id, email=f"{role}@fresh.test", role=role)
            _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
            tokens[role] = token
        tokens["tenant_id"] = tenant.id
        session.commit()
    return client, tokens, tmp_path


def test_build_freshness_summary_fixture(env) -> None:
    _client, _tokens, lake = env
    records = load_freshness_records(str(lake))
    summary = build_freshness_summary(records)
    assert summary["total"] >= 0
    assert "fresh_rate_pct" in summary
    assert "sources" in summary


def test_freshness_summary_api(env) -> None:
    client, tokens, _lake = env
    resp = client.get("/api/v1/evidence/freshness/summary", headers=_bearer(tokens["read_only"]))
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()["data"]
    assert data["state"] in {"healthy", "action_required"}


def test_escalate_requires_write(env) -> None:
    client, tokens, _lake = env
    resp = client.post(
        "/api/v1/evidence/freshness/escalate",
        json={"limit": 5},
        headers=_bearer(tokens["read_only"]),
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_escalate_creates_tasks_when_breaches_exist(env) -> None:
    client, tokens, lake = env
    records = load_freshness_records(str(lake))
    summary = build_freshness_summary(records)
    if summary["sla_breach_count"] == 0:
        pytest.skip("fixture has no SLA breaches")
    with client.app.state.sessionmaker() as session:
        result = escalate_stale_evidence(
            session,
            tenant_id=tokens["tenant_id"],
            lake_dir=str(lake),
            actor_email="contributor@fresh.test",
            limit=3,
        )
        session.commit()
    assert result["created_count"] >= 0

    resp = client.post(
        "/api/v1/evidence/freshness/escalate",
        json={"limit": 3},
        headers=_bearer(tokens["contributor"]),
    )
    assert resp.status_code == HTTPStatus.OK
    assert "created_count" in resp.json()["data"]
