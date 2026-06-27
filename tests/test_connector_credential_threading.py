"""Connector syncs read identity scope from stored credentials, not just env.

A connector configured through the UI/API persists its non-secret identity scope
(subscription_id / account_id / project_id). A later sync must use that stored
scope without the operator re-exporting an env var.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import security_lakehouse.connector_runner as connector_runner
from security_lakehouse.connector_state import append_config_event
from security_lakehouse.connectors_gcp import GCPFixtureClient

GCP_FIXTURE = Path(__file__).parent / "fixtures" / "gcp"


def test_gcp_sync_uses_stored_project_id_when_env_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    captured: dict[str, str] = {}

    class FixtureBackedGCPClient(GCPFixtureClient):
        def __init__(self, project_id: str) -> None:
            captured["project_id"] = project_id
            super().__init__(GCP_FIXTURE, project_id=project_id)

    monkeypatch.setattr(connector_runner, "GCPClient", FixtureBackedGCPClient)

    append_config_event(
        tmp_path,
        connector_id="gcp-posture",
        state="enabled",
        actor="a",
        credentials={"project_id": "proj-123456"},
    )
    result = connector_runner.run_connector_sync(tmp_path, connector_id="gcp-posture")

    assert result.result == "ok"
    assert captured["project_id"] == "proj-123456"
