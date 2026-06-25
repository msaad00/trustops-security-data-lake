"""Azure posture-evidence connector runner tests (fixture-backed)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import security_lakehouse.connector_runner as connector_runner
from security_lakehouse.connector_state import (
    append_config_event,
    has_adapter,
    latest_run,
    run_probe,
)
from security_lakehouse.connectors_azure import AzureCliClient, AzureClient, AzureFixtureClient, collect_azure_evidence
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE = Path(__file__).parent / "fixtures" / "azure"
SUBSCRIPTION = "11111111-1111-1111-1111-111111111111"


def _by_type(rows: list[dict], event_type: str) -> list[dict]:
    return [r for r in rows if r["event_type"] == event_type]


def _role(rows: list[dict], role_name: str) -> dict:
    matches = [r for r in _by_type(rows, "azure.cloud.role_assignment") if r["attributes"]["role_name"] == role_name]
    assert len(matches) == 1
    return matches[0]


def test_collect_azure_evidence_is_schema_valid_and_mapped() -> None:
    client = AzureFixtureClient(FIXTURE, subscription_id=SUBSCRIPTION)
    rows = collect_azure_evidence(
        client,
        collected_at=datetime(2026, 6, 3, tzinfo=UTC),
    )

    assert validate_raw_events(rows) == []
    # 3 role assignments + 2 policy assignments + 2 resources = 7 events.
    assert len(rows) == 7

    role = _by_type(rows, "azure.cloud.role_assignment")
    policy = _by_type(rows, "azure.cloud.policy_assignment")
    resource = _by_type(rows, "azure.cloud.resource")
    assert len(role) == 3
    assert len(policy) == 2
    assert len(resource) == 2

    # Every emitted event is azure-scoped and maps to a catalog control.
    for row in rows:
        assert row["source"] == "azure"
        assert "SOC2-CC6.1" in row["controls"]
        assert row["entity"]["org"] == SUBSCRIPTION

    # Owner at subscription scope is a high open identity finding for review.
    owner = _role(rows, "Owner")
    assert owner["status"] == "open"
    assert owner["severity"] == "high"
    assert owner["attributes"]["privileged_role"] is True
    assert owner["attributes"]["subscription_scope"] is True

    # Reader at subscription scope is observed/info (not privileged).
    reader = _role(rows, "Reader")
    assert reader["status"] == "observed"
    assert reader["severity"] == "info"
    assert reader["attributes"]["privileged_role"] is False

    # Contributor scoped to a resource group is not a subscription-scope finding.
    contributor = _role(rows, "Contributor")
    assert contributor["status"] == "observed"
    assert contributor["severity"] == "info"
    assert contributor["attributes"]["privileged_role"] is True
    assert contributor["attributes"]["subscription_scope"] is False

    # An enforcing policy is observed; a DoNotEnforce policy is an open finding.
    enforced = [p for p in policy if p["attributes"]["is_enforced"]]
    not_enforced = [p for p in policy if not p["attributes"]["is_enforced"]]
    assert len(enforced) == 1
    assert len(not_enforced) == 1
    assert enforced[0]["status"] == "observed"
    assert enforced[0]["severity"] == "info"
    assert not_enforced[0]["status"] == "open"
    assert not_enforced[0]["severity"] == "medium"
    assert not_enforced[0]["attributes"]["enforcement_mode"] == "DoNotEnforce"

    # Resources are observed inventory and point at the read-only resource id.
    sample = resource[0]
    assert sample["entity"]["asset_type"] == "cloud_resource"
    assert sample["status"] == "observed"
    assert sample["evidence"]["evidence_ref"] == sample["attributes"]["resource_id"]
    assert sample["evidence"]["evidence_ref"].startswith(f"/subscriptions/{SUBSCRIPTION}")


def test_azure_connector_sync_writes_raw_and_materializes_lake(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="alice")
    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="azure-posture",
        fixture_dir=FIXTURE,
    )
    assert result.result == "ok"
    assert result.evidence_count == 7
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == 7
    assert all(r["source"] == "azure" for r in raw_rows)
    assert (tmp_path / "bronze" / "raw_events.jsonl").is_file()
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "current_posture.json").is_file()

    run = latest_run(tmp_path, "azure-posture", kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == 7


def test_azure_sync_preserves_evidence_refs_and_generic_evidence_types(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="alice")
    connector_runner.run_connector_sync(tmp_path, connector_id="azure-posture", fixture_dir=FIXTURE)

    silver_rows = read_jsonl(tmp_path / "silver" / "normalized_events.jsonl")
    role_rows = [row for row in silver_rows if row["event_type"] == "azure.cloud.role_assignment"]
    assert role_rows
    assert all(row["evidence_ref"].startswith(f"/subscriptions/{SUBSCRIPTION}") for row in role_rows)
    assert all({"cloud.config", "identity.access_review"} <= set(row["evidence_types"]) for row in role_rows)

    control_tests = {row["control_id"]: row for row in read_jsonl(tmp_path / "gold" / "control_tests.jsonl")}
    soc2 = control_tests["SOC2-CC6.1"]
    assert "cloud.config" in soc2["observed_evidence_types"]
    assert "identity.access_review" in soc2["observed_evidence_types"]
    assert "cloud.config" not in soc2["missing_evidence_types"]
    assert "identity.access_review" not in soc2["missing_evidence_types"]

    hipaa = control_tests["HIPAA-164.308(a)(4)"]
    assert hipaa["result"] == "pass"
    assert hipaa["freshness_status"] == "fresh"

    assets = read_jsonl(tmp_path / "gold" / "asset_risk.jsonl")
    cloud_resource = next(row for row in assets if row["asset_type"] == "cloud_resource")
    assert "SOC2-CC6.1" in cloud_resource["applicable_control_ids"]
    assert "NIST-AI-RMF-MAP-1.5" in cloud_resource["applicable_control_ids"]


def test_azure_connector_sync_falls_back_to_az_cli_when_sdk_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenAzureClient:
        def __init__(self, subscription_id: str) -> None:
            raise RuntimeError("azure sdk import failed")

    class FixtureBackedAzureCliClient(AzureFixtureClient):
        def __init__(self, subscription_id: str) -> None:
            super().__init__(FIXTURE, subscription_id=subscription_id)

    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", SUBSCRIPTION)
    monkeypatch.setattr(connector_runner, "AzureClient", BrokenAzureClient)
    monkeypatch.setattr(connector_runner, "AzureCliClient", FixtureBackedAzureCliClient)

    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    result = connector_runner.run_connector_sync(tmp_path, connector_id="azure-posture")

    assert result.result == "ok"
    assert result.evidence_count == 7
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 7
    assert all(row["entity"]["org"] == SUBSCRIPTION for row in raw_rows)


def test_azure_connector_sync_upserts_stable_event_ids(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    first = connector_runner.run_connector_sync(tmp_path, connector_id="azure-posture", fixture_dir=FIXTURE)
    second = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="azure-posture",
        fixture_dir=FIXTURE,
        materialize=False,
    )
    assert first.evidence_count == second.evidence_count == 7
    assert len(read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)) == 7


def test_azure_connector_sync_requires_enabled_connector(tmp_path: Path) -> None:
    with pytest.raises(connector_runner.ConnectorSyncError, match="not enabled") as exc:
        connector_runner.run_connector_sync(tmp_path, connector_id="azure-posture", fixture_dir=FIXTURE)
    assert exc.value.run["result"] == "error"


def test_azure_connector_sync_without_fixture_or_creds_errors(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    with pytest.raises(connector_runner.ConnectorSyncError, match="requires --fixture-dir"):
        connector_runner.run_connector_sync(tmp_path, connector_id="azure-posture")


def test_azure_client_policy_assignments_degrade_when_policy_sdk_missing() -> None:
    client = AzureClient.__new__(AzureClient)
    client._policy = None

    assert client.policy_assignments() == []


def test_azure_cli_client_reads_cloud_shell_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_which(executable: str) -> str:
        assert executable == "az"
        return "/usr/bin/az"

    def fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> SimpleNamespace:
        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 90
        calls.append(cmd)
        if cmd[1:4] == ["role", "assignment", "list"]:
            payload: list[dict[str, Any]] = [{"id": "role-1", "roleDefinitionName": "Reader"}]
        elif cmd[1:4] == ["policy", "assignment", "list"]:
            payload = [{"id": "policy-1", "properties": {"enforcementMode": "Default"}}]
        elif cmd[1:3] == ["resource", "list"]:
            payload = [{"id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/a"}]
        else:  # pragma: no cover - defensive branch for unexpected command shape
            payload = []
        return SimpleNamespace(stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("security_lakehouse.connectors_azure.shutil.which", fake_which)
    monkeypatch.setattr("security_lakehouse.connectors_azure.subprocess.run", fake_run)

    client = AzureCliClient("sub")

    assert client.role_assignments() == [{"id": "role-1", "roleDefinitionName": "Reader"}]
    assert client.policy_assignments() == [{"id": "policy-1", "properties": {"enforcementMode": "Default"}}]
    assert client.resources() == [
        {"id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/a"}
    ]
    assert all("--subscription" in call for call in calls)
    assert all(call[-4:] == ["--subscription", "sub", "--output", "json"] for call in calls)


def test_azure_adapter_is_registered_and_probe_reports_ok(tmp_path: Path) -> None:
    assert has_adapter("azure-posture") is True
    # Before enablement the probe is skipped (no synthetic collection signal).
    skipped = run_probe(tmp_path, connector_id="azure-posture")
    assert skipped["result"] == "skipped"
    assert "not enabled" in skipped["error"]

    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    ok = run_probe(tmp_path, connector_id="azure-posture")
    # Adapter-available -> probe is "ok", not "skipped", and reports no count.
    assert ok["result"] == "ok"
    assert ok["evidence_count"] is None
