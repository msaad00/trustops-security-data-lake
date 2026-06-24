"""Azure posture-evidence connector runner tests (fixture-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from security_lakehouse.connector_runner import CONNECTOR_RAW_FILE, ConnectorSyncError, run_connector_sync
from security_lakehouse.connector_state import (
    append_config_event,
    has_adapter,
    latest_run,
    run_probe,
)
from security_lakehouse.connectors_azure import AzureClient, AzureFixtureClient, collect_azure_evidence
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
    result = run_connector_sync(
        tmp_path,
        connector_id="azure-posture",
        fixture_dir=FIXTURE,
    )
    assert result.result == "ok"
    assert result.evidence_count == 7
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == 7
    assert all(r["source"] == "azure" for r in raw_rows)
    assert (tmp_path / "bronze" / "raw_events.jsonl").is_file()
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "current_posture.json").is_file()

    run = latest_run(tmp_path, "azure-posture", kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == 7


def test_azure_connector_sync_upserts_stable_event_ids(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    first = run_connector_sync(tmp_path, connector_id="azure-posture", fixture_dir=FIXTURE)
    second = run_connector_sync(
        tmp_path,
        connector_id="azure-posture",
        fixture_dir=FIXTURE,
        materialize=False,
    )
    assert first.evidence_count == second.evidence_count == 7
    assert len(read_jsonl(tmp_path / CONNECTOR_RAW_FILE)) == 7


def test_azure_connector_sync_requires_enabled_connector(tmp_path: Path) -> None:
    with pytest.raises(ConnectorSyncError, match="not enabled") as exc:
        run_connector_sync(tmp_path, connector_id="azure-posture", fixture_dir=FIXTURE)
    assert exc.value.run["result"] == "error"


def test_azure_connector_sync_without_fixture_or_creds_errors(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    append_config_event(tmp_path, connector_id="azure-posture", state="enabled", actor="a")
    with pytest.raises(ConnectorSyncError, match="requires --fixture-dir"):
        run_connector_sync(tmp_path, connector_id="azure-posture")


def test_azure_client_policy_assignments_degrade_when_policy_sdk_missing() -> None:
    client = AzureClient.__new__(AzureClient)
    client._policy = None

    assert client.policy_assignments() == []


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
