"""GCP cloud-posture connector runner tests (fixture-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import pytest

from security_lakehouse.connector_runner import CONNECTOR_RAW_FILE, ConnectorSyncError, run_connector_sync
from security_lakehouse.connector_state import (
    append_config_event,
    has_adapter,
    latest_run,
    run_probe,
)
from security_lakehouse.connectors_gcp import GCPFixtureClient, collect_gcp_evidence
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE = Path(__file__).parent / "fixtures" / "gcp"
PROJECT = "fixture-project"


def _by_asset(rows: list[dict], event_type: str) -> dict[str, dict]:
    return {r["entity"]["asset_id"]: r for r in rows if r["event_type"] == event_type}


def test_collect_gcp_evidence_is_schema_valid_and_mapped() -> None:
    client = GCPFixtureClient(FIXTURE, project_id=PROJECT)
    rows = collect_gcp_evidence(
        client,
        collected_at=datetime(2026, 5, 28, tzinfo=UTC),
    )

    assert validate_raw_events(rows) == []
    # 3 IAM bindings + 2 org policies + 2 assets.
    assert len(rows) == 7

    iam = _by_asset(rows, "gcp.cloud.iam_binding")
    # Org-policy events share one project asset_id, so key them by constraint.
    policy = {r["attributes"]["constraint"]: r for r in rows if r["event_type"] == "gcp.cloud.org_policy"}
    asset = _by_asset(rows, "gcp.cloud.asset")
    assert len(iam) == 3
    assert len(policy) == 2
    assert len(asset) == 2

    # Every emitted event maps to controls that exist in the catalog.
    for row in rows:
        assert row["source"] == "gcp"
        assert "SOC2-CC6.1" in row["controls"]

    # A privileged role binding (roles/owner) is a high open finding for review.
    owner = iam[f"gcp:project:{PROJECT}:role/roles/owner"]
    assert owner["status"] == "open"
    assert owner["severity"] == "high"
    assert owner["attributes"]["privileged"] is True
    assert owner["attributes"]["member_count"] == 2

    # A non-privileged role binding is observed, not a finding.
    viewer = iam[f"gcp:project:{PROJECT}:role/roles/viewer"]
    assert viewer["status"] == "observed"
    assert viewer["severity"] == "info"
    assert viewer["attributes"]["privileged"] is False

    # An expected constraint that is not enforced is an open medium config finding.
    weak = policy["constraints/iam.disableServiceAccountKeyCreation"]
    assert weak["entity"]["asset_type"] == "account_config"
    assert weak["status"] == "open"
    assert weak["severity"] == "medium"
    assert weak["attributes"]["needs_enforcement"] is True

    # An enforced expected constraint passes.
    strong = policy["constraints/compute.requireOsLogin"]
    assert strong["status"] == "pass"
    assert strong["severity"] == "info"
    assert strong["attributes"]["enforced"] is True

    # Asset events are cloud resources scoped to the project and read-only refs.
    sample = next(iter(asset.values()))
    assert sample["entity"]["asset_type"] == "cloud_resource"
    assert urlparse(sample["evidence"]["evidence_ref"]).netloc == "cloudasset.googleapis.com"
    assert owner["evidence"]["evidence_ref"].endswith(":getIamPolicy")


def test_gcp_connector_sync_writes_raw_and_materializes_lake(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="gcp-posture", state="enabled", actor="alice")
    result = run_connector_sync(
        tmp_path,
        connector_id="gcp-posture",
        fixture_dir=FIXTURE,
    )
    assert result.result == "ok"
    assert result.evidence_count == 7
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == 7
    assert all(r["source"] == "gcp" for r in raw_rows)
    assert (tmp_path / "bronze" / "raw_events.jsonl").is_file()
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "current_posture.json").is_file()

    run = latest_run(tmp_path, "gcp-posture", kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == 7


def test_gcp_connector_sync_upserts_stable_event_ids(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="gcp-posture", state="enabled", actor="a")
    first = run_connector_sync(tmp_path, connector_id="gcp-posture", fixture_dir=FIXTURE)
    second = run_connector_sync(
        tmp_path,
        connector_id="gcp-posture",
        fixture_dir=FIXTURE,
        materialize=False,
    )
    assert first.evidence_count == second.evidence_count == 7
    assert len(read_jsonl(tmp_path / CONNECTOR_RAW_FILE)) == 7


def test_gcp_connector_sync_requires_enabled_connector(tmp_path: Path) -> None:
    with pytest.raises(ConnectorSyncError, match="not enabled") as exc:
        run_connector_sync(tmp_path, connector_id="gcp-posture", fixture_dir=FIXTURE)
    assert exc.value.run["result"] == "error"


def test_gcp_connector_sync_without_fixture_or_creds_errors(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    append_config_event(tmp_path, connector_id="gcp-posture", state="enabled", actor="a")
    with pytest.raises(ConnectorSyncError, match="requires --fixture-dir"):
        run_connector_sync(tmp_path, connector_id="gcp-posture")


def test_gcp_adapter_is_registered_and_probe_reports_ok(tmp_path: Path) -> None:
    assert has_adapter("gcp-posture") is True
    # Before enablement the probe is skipped (no synthetic collection signal).
    skipped = run_probe(tmp_path, connector_id="gcp-posture")
    assert skipped["result"] == "skipped"
    assert "not enabled" in skipped["error"]

    append_config_event(tmp_path, connector_id="gcp-posture", state="enabled", actor="a")
    ok = run_probe(tmp_path, connector_id="gcp-posture")
    # Adapter-available -> probe is "ok", not "skipped", and reports no count.
    assert ok["result"] == "ok"
    assert ok["evidence_count"] is None


def test_gcp_required_config_is_project_id_only() -> None:
    # GCP authenticates via Application Default Credentials, so the only required
    # config is the project scope — no credential_ref (the same identity model as
    # aws-posture / azure-posture).
    from security_lakehouse.connector_state import _missing_required_config

    assert _missing_required_config("gcp-posture", "gcp_adc_reader", {}, {}) == ["project_id"]
    assert _missing_required_config("gcp-posture", "gcp_adc_reader", {"project_id": "p"}, {}) == []


def test_gcp_client_org_policies_and_assets_degrade_when_apis_unavailable() -> None:
    # A least-privilege reader (or a project with the Org Policy / Cloud Asset
    # APIs disabled) must not fail the whole sync: those two collectors degrade
    # to empty while IAM-binding evidence still flows.
    from security_lakehouse.connectors_gcp import GCPClient

    client = GCPClient.__new__(GCPClient)
    client.project_id = PROJECT

    class _ApiDisabled:
        def list_policies(self, **_kwargs: object) -> list[object]:
            raise RuntimeError("Org Policy API has not been used in project ... or it is disabled")

        def list_assets(self, **_kwargs: object) -> list[object]:
            raise RuntimeError("Cloud Asset API has not been used in project ... or it is disabled")

    client._org_policies = _ApiDisabled()
    client._assets = _ApiDisabled()
    assert client.org_policies() == []
    assert client.assets() == []

    # An absent org-policy client (package/API unavailable) is also non-fatal.
    client._org_policies = None
    assert client.org_policies() == []


def test_gcp_collect_is_iam_only_valid_when_org_and_assets_degrade() -> None:
    # Mirrors the live degraded path: IAM bindings collect and map to controls,
    # privileged roles surface as findings, with org-policy/asset collectors empty.
    class _IamOnlyClient:
        project_id = PROJECT

        def iam_bindings(self) -> list[dict[str, object]]:
            return [
                {"role": "roles/owner", "members": ["user:admin@example.com"]},
                {"role": "roles/viewer", "members": ["serviceAccount:reader@example.com"]},
            ]

        def org_policies(self) -> list[dict[str, object]]:
            return []

        def assets(self) -> list[dict[str, object]]:
            return []

    rows = collect_gcp_evidence(_IamOnlyClient(), project_id=PROJECT)
    assert validate_raw_events(rows) == []
    bindings = [r for r in rows if r["event_type"] == "gcp.cloud.iam_binding"]
    assert len(bindings) == 2
    owner = next(r for r in bindings if r["attributes"]["role"] == "roles/owner")
    assert owner["severity"] == "high"
    # Sole "user:" member => human identity.
    assert owner["attributes"]["identity_type"] == "human"
    # Sole "serviceAccount:" member => service identity.
    viewer = next(r for r in bindings if r["attributes"]["role"] == "roles/viewer")
    assert viewer["attributes"]["identity_type"] == "service"
