"""AI governance platform API and aggregation tests."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.ai_governance import build_ai_governance_status, list_ai_inventory  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake, _write_jsonl  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_ai_events(lake: Path) -> None:
    _seed_lake(lake)
    _write_jsonl(
        lake / "silver" / "normalized_events.jsonl",
        [
            {
                "event_id": "evt-ai-001",
                "event_time": "2026-05-20T15:05:00Z",
                "event_type": "ai.model_inventory",
                "control_ids": ["NIST-AI-RMF-MAP-1.5", "ISO42001-8.1", "EU-AI-ACT-Art.10"],
                "asset_id": "model:customer-support-reranker:v3",
                "asset_owner": "ai-security",
                "asset_type": "ai_model",
                "environment": "prod",
                "source": "model-registry",
                "status": "passed",
                "severity": "low",
                "severity_score": 10,
                "evidence_ref": "s3://evidence/model-card.json",
                "raw_sha256": "abc",
                "attributes": {"model_card": True, "lineage_complete": True},
            },
            {
                "event_id": "evt-ai-002",
                "event_time": "2026-05-22T08:30:00Z",
                "event_type": "model.lineage",
                "control_ids": ["NIST-AI-RMF-MAP-1.5"],
                "asset_id": "model:customer-support-reranker:v3",
                "asset_owner": "ai-security",
                "asset_type": "ai_model",
                "environment": "prod",
                "source": "model-registry",
                "status": "passed",
                "severity": "info",
                "severity_score": 5,
                "evidence_ref": "s3://evidence/lineage.json",
                "raw_sha256": "def",
            },
            {
                "event_id": "evt-ai-003",
                "event_time": "2026-05-20T13:11:00Z",
                "event_type": "runtime.tool_call",
                "control_ids": ["NIST-AI-RMF-MANAGE-4.3", "EU-AI-ACT-Art.14"],
                "asset_id": "agent:finance-research",
                "asset_owner": "ai-security",
                "asset_type": "ai_agent",
                "environment": "prod",
                "source": "runtime-gateway",
                "status": "blocked",
                "severity": "high",
                "severity_score": 80,
                "evidence_ref": "s3://evidence/runtime.json",
                "raw_sha256": "ghi",
            },
            {
                "event_id": "evt-ai-004",
                "event_time": "2026-05-20T16:00:00Z",
                "event_type": "repository.ai_artifact",
                "control_ids": ["NIST-AI-RMF-MAP-1.5", "EU-AI-ACT-Art.10", "ISO42001-8.1"],
                "asset_id": "github:repo:acme/ml-platform",
                "asset_owner": "ai-security",
                "asset_type": "repository",
                "environment": "public",
                "source": "github-public-repo",
                "status": "observed",
                "severity": "info",
                "severity_score": 0,
                "evidence_ref": "https://github.com/acme/ml-platform",
                "raw_sha256": "jkl",
                "attributes": {"paths": ["modelcard.md"], "path_count": 1},
            },
        ],
    )


def test_build_ai_governance_status_fixture(tmp_path: Path) -> None:
    _seed_ai_events(tmp_path)
    data = build_ai_governance_status(lake=tmp_path)
    assert data["inventory"]["models"] >= 1
    assert data["inventory"]["agents"] >= 1
    assert data["events"]["model_inventory"] >= 1
    assert data["events"]["model_lineage"] >= 1
    assert data["events"]["agent_runtime"] >= 1
    assert data["events"]["repo_artifacts"] >= 1
    assert data["frameworks_total"] == 3
    assert data["aibom"]["shipped"] is False
    assert data["evidence_loops"]["inventory_events"] is True
    assert data["evidence_loops"]["lineage_events"] is True


def test_list_ai_inventory_fixture(tmp_path: Path) -> None:
    _seed_ai_events(tmp_path)
    rows = list_ai_inventory(lake=tmp_path)
    asset_ids = {row["asset_id"] for row in rows}
    assert "model:customer-support-reranker:v3" in asset_ids
    assert "agent:finance-research" in asset_ids


def test_ai_governance_api(tmp_path: Path) -> None:
    _seed_ai_events(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    with app.state.sessionmaker() as session:
        tenant = create_tenant(session, slug="ai-gov", name="AI Gov")
        user = create_user(session, tenant_id=tenant.id, email="read@ai-gov.test", role="read_only")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
        session.commit()
    resp = client.get("/api/v1/platform/ai-governance", headers=_bearer(token))
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()["data"]
    assert body["governance_score"] >= 0
    assert len(body["frameworks"]) == 3

    inv = client.get("/api/v1/platform/ai-governance/inventory", headers=_bearer(token))
    assert inv.status_code == HTTPStatus.OK
    assert len(inv.json()["data"]) >= 2
