"""Microsoft Intune device-posture connector tests (fixture-backed + fake Graph)."""

from __future__ import annotations

import io
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import security_lakehouse.connector_runner as connector_runner
from security_lakehouse import connectors_intune, netguard
from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.connector_state import append_config_event, latest_run
from security_lakehouse.connectors_intune import (
    GRAPH_MANAGED_DEVICES_URL,
    IntuneClient,
    IntuneFixtureClient,
    collect_intune_evidence,
)
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE = Path(__file__).parent / "fixtures" / "intune"
TENANT = "22222222-2222-2222-2222-222222222222"
COLLECTED = datetime(2026, 6, 3, tzinfo=UTC)


def _rows() -> list[dict[str, Any]]:
    return collect_intune_evidence(IntuneFixtureClient(FIXTURE, tenant_id=TENANT), collected_at=COLLECTED)


def _event(rows: list[dict[str, Any]], device_id: str, signal: str) -> dict[str, Any]:
    matches = [
        r
        for r in rows
        if r["entity"]["asset_id"] == f"intune:device:{device_id}" and r["event_type"] == f"intune.device.{signal}"
    ]
    assert len(matches) == 1
    return matches[0]


def test_collect_emits_encryption_and_compliance_per_device() -> None:
    rows = _rows()

    assert validate_raw_events(rows) == []
    assert len(rows) == 10
    catalog = load_control_catalog()
    for row in rows:
        assert row["source"] == "intune"
        assert row["entity"]["asset_type"] == "managed_device"
        assert row["entity"]["org"] == TENANT
        assert row["controls"]
        assert all(control in catalog for control in row["controls"])


@pytest.mark.parametrize(
    ("device_id", "status", "severity"),
    [
        ("dev-win-compliant", "pass", "info"),
        ("dev-mac-noncompliant", "open", "high"),
        ("dev-unknown", "open", "high"),
    ],
)
def test_encryption_status(device_id: str, status: str, severity: str) -> None:
    event = _event(_rows(), device_id, "encryption")
    assert (event["status"], event["severity"]) == (status, severity)


@pytest.mark.parametrize(
    ("device_id", "status", "severity", "reason"),
    [
        ("dev-win-compliant", "pass", "info", None),
        ("dev-mac-noncompliant", "open", "high", "noncompliant"),
        ("dev-ios-grace", "open", "low", "in_grace_period"),
        ("dev-android-rooted", "open", "high", "jailbroken"),
        ("dev-unknown", "open", "medium", "compliance_not_reported"),
    ],
)
def test_compliance_status(device_id: str, status: str, severity: str, reason: str | None) -> None:
    event = _event(_rows(), device_id, "compliance")
    assert (event["status"], event["severity"]) == (status, severity)
    assert event["attributes"]["finding_reason"] == reason


def test_attributes_are_minimized() -> None:
    allowed = {
        "device_id",
        "device_name",
        "user_principal_name",
        "operating_system",
        "os_version",
        "owner_type",
        "management_agent",
        "azure_ad_device_id",
        "is_supervised",
        "last_sync",
        "enrolled",
        "is_encrypted",
        "compliance_state",
        "jailbroken",
        "finding_reason",
    }
    for row in _rows():
        assert set(row["attributes"]) <= allowed


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _fake_graph(monkeypatch: pytest.MonkeyPatch, pages: dict[str, dict[str, Any]]) -> list[Any]:
    seen: list[Any] = []

    def fake_open_public(request: Any, *, timeout: float, label: str) -> _FakeResponse:
        seen.append(request)
        return _FakeResponse(json.dumps(pages[request.full_url]).encode())

    monkeypatch.setattr(netguard, "open_public", fake_open_public)
    return seen


def test_live_client_selects_minimal_fields_and_follows_graph_next_links(monkeypatch: pytest.MonkeyPatch) -> None:
    devices = json.loads((FIXTURE / "managed_devices.json").read_text())
    first = GRAPH_MANAGED_DEVICES_URL
    second = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$skiptoken=abc"
    seen = _fake_graph(
        monkeypatch,
        {first: {"value": devices[:2], "@odata.nextLink": second}, second: {"value": devices[2:]}},
    )

    client = IntuneClient(TENANT, token_provider=lambda: "graph-token")

    assert [d["id"] for d in client.managed_devices()] == [d["id"] for d in devices]
    assert [r.full_url for r in seen] == [first, second]
    assert seen[0].get_header("Authorization") == "Bearer graph-token"
    selected = urllib.parse.parse_qs(urllib.parse.urlparse(first).query)["$select"][0].split(",")
    assert "isEncrypted" in selected
    assert not {"imei", "serialNumber", "phoneNumber", "wiFiMacAddress", "userDisplayName", "notes"} & set(selected)


def test_live_client_refuses_next_link_off_graph_host(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_graph(
        monkeypatch,
        {GRAPH_MANAGED_DEVICES_URL: {"value": [], "@odata.nextLink": "https://attacker.example/steal"}},
    )

    with pytest.raises(ValueError, match="graph.microsoft.com"):
        IntuneClient(TENANT, token_provider=lambda: "graph-token").managed_devices()


def test_sync_requires_tenant_for_live_collection(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="intune-devices", state="enabled", actor="alice")

    with pytest.raises(connector_runner.ConnectorSyncError, match="tenant_id"):
        connector_runner.run_connector_sync(tmp_path, connector_id="intune-devices")
    assert latest_run(tmp_path, "intune-devices", kind="sync")["result"] == "error"


def test_fixture_sync_materializes_and_evaluates_device_controls(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="intune-devices",
        state="enabled",
        actor="alice",
        credentials={"tenant_id": TENANT},
    )

    result = connector_runner.run_connector_sync(tmp_path, connector_id="intune-devices", fixture_dir=FIXTURE)

    assert result.result == "ok"
    assert result.evidence_count == 10
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert connectors_intune.ENCRYPTION_CONTROLS[0] in {c for r in raw_rows for c in r["controls"]}
