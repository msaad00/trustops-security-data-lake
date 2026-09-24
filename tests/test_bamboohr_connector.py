"""BambooHR employment-record connector tests (fixture-backed + fake HTTP)."""

from __future__ import annotations

import base64
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import security_lakehouse.connector_runner as connector_runner
from security_lakehouse import netguard
from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.connector_state import append_config_event
from security_lakehouse.connectors_bamboohr import (
    DATASET_FIELDS,
    BambooHRClient,
    BambooHRFixtureClient,
    collect_bamboohr_evidence,
)
from security_lakehouse.data_policy import redact_payload
from security_lakehouse.hris import PERSONNEL_CONTROLS
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE = Path(__file__).parent / "fixtures" / "bamboohr"
COLLECTED = datetime(2026, 6, 3, tzinfo=UTC)


def _rows() -> list[dict[str, Any]]:
    return collect_bamboohr_evidence(BambooHRFixtureClient(FIXTURE, company_domain="acme"), collected_at=COLLECTED)


def _by_employee(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["attributes"]["employee_id"]: r for r in rows}


def test_collect_emits_one_schema_valid_employment_record_per_employee() -> None:
    rows = _rows()

    assert validate_raw_events(rows) == []
    assert sorted(_by_employee(rows)) == ["101", "102", "103", "104"]
    catalog = load_control_catalog()
    assert all(control in catalog for control in PERSONNEL_CONTROLS)
    for row in rows:
        assert row["source"] == "bamboohr"
        assert row["event_type"] == "hris.personnel.employment"
        assert row["entity"]["asset_type"] == "hris_employee"
        assert row["controls"] == PERSONNEL_CONTROLS
        assert row["status"] == "observed"


def test_termination_is_derived_from_termination_date_as_of_collection() -> None:
    employees = _by_employee(_rows())

    assert employees["101"]["attributes"]["is_terminated"] is False
    assert employees["102"]["attributes"]["is_terminated"] is True
    assert employees["102"]["attributes"]["termination_date"] == "2026-05-15"
    # Future-dated termination is not yet a termination.
    assert employees["103"]["attributes"]["is_terminated"] is False
    # BambooHR's zero date means "no termination date".
    assert employees["104"]["attributes"]["termination_date"] is None


def test_attributes_stay_inside_the_minimal_pii_boundary() -> None:
    allowed = {
        "employee_id",
        "employee_number",
        "work_email",
        "employment_status",
        "hire_date",
        "termination_date",
        "is_terminated",
        "department",
        "manager_id",
        "data_sensitivity",
    }
    for row in _rows():
        assert set(row["attributes"]) <= allowed
        assert row["attributes"]["data_sensitivity"] == "confidential"
    assert set(DATASET_FIELDS) == {
        "eeid",
        "employeeNumber",
        "email",
        "employmentStatus",
        "hireDate",
        "terminationDate",
        "jobInformationDepartment",
        "supervisorEid",
    }


def test_auditor_role_cannot_read_personnel_attributes() -> None:
    row = _rows()[0]
    redacted = redact_payload(row, role="auditor")
    assert redacted["attributes"]["redacted"] is True
    assert "work_email" not in redacted["attributes"]


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_live_client_posts_minimal_fields_with_basic_auth_and_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    records = json.loads((FIXTURE / "employee_dataset.json").read_text())
    pages = {
        1: {"data": records[:2], "meta": {"page": 1, "pageSize": 2, "totalPages": 2, "totalItems": 4}},
        2: {"data": records[2:4], "meta": {"page": 2, "pageSize": 2, "totalPages": 2, "totalItems": 4}},
    }
    seen: list[Any] = []

    def fake_open_public(request: Any, *, timeout: float, label: str) -> _FakeResponse:
        body = json.loads(request.data)
        seen.append((request, body))
        return _FakeResponse(json.dumps(pages[body["page"]]).encode())

    monkeypatch.setattr(netguard, "open_public", fake_open_public)

    rows = BambooHRClient("acme", api_key="secret-key").employees()

    assert [r["fields"]["eeid"] for r in rows] == ["101", "102", "103", "104"]
    request, body = seen[0]
    assert request.full_url == "https://acme.bamboohr.com/api/v2/datasets/employee/data"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Basic " + base64.b64encode(b"secret-key:x").decode()
    assert body["fields"] == list(DATASET_FIELDS)
    assert [b["page"] for _, b in seen] == [1, 2]


@pytest.mark.parametrize("domain", ["", "acme.evil.com", "acme/../x", "ACME@evil", "http://acme"])
def test_company_domain_must_be_a_bare_subdomain(domain: str) -> None:
    with pytest.raises(ValueError, match="company_domain"):
        BambooHRClient(domain, api_key="k")


def test_sync_requires_company_domain_and_api_key(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="bamboohr-personnel", state="enabled", actor="alice")

    with pytest.raises(connector_runner.ConnectorSyncError, match="company_domain"):
        connector_runner.run_connector_sync(tmp_path, connector_id="bamboohr-personnel")


def test_fixture_sync_materializes(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="bamboohr-personnel",
        state="enabled",
        actor="alice",
        credentials={"company_domain": "acme", "credential_ref": "BAMBOOHR_API_KEY"},
    )

    result = connector_runner.run_connector_sync(tmp_path, connector_id="bamboohr-personnel", fixture_dir=FIXTURE)

    assert result.result == "ok"
    assert result.evidence_count == 4
    assert validate_raw_events(read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)) == []
