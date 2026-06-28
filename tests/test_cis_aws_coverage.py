"""CIS AWS Foundations Benchmark coverage is genuine, not just catalogued.

Proves the chain end to end: the AWS connector tags its posture findings with the
CIS control IDs, those IDs resolve to real catalog controls with a valid policy
rule, and a failing finding drives the mapped CIS control to ``fail`` through the
normal pipeline — the same path that already powers SOC 2 / ISO / HIPAA.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.connectors_aws import (
    ACCESS_KEY_CONTROLS,
    MFA_CONTROLS,
    POLICY_CONTROLS,
    AWSFixtureClient,
    collect_aws_evidence,
)
from security_lakehouse.controls import load_control_map
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.policy import validate_rule

FIXTURE = Path(__file__).parent / "fixtures" / "aws"
ACCOUNT = "123456789012"

CIS_FINDING_CONTROLS = {
    "aws.iam.mfa_enrollment": "CIS-AWS-1.10",
    "aws.iam.access_key_hygiene": "CIS-AWS-1.14",
    "aws.iam.password_policy": "CIS-AWS-1.8",
}


def test_cis_controls_are_in_the_catalog_with_valid_rules() -> None:
    catalog = load_control_catalog()
    for control_id in CIS_FINDING_CONTROLS.values():
        assert control_id in catalog, f"{control_id} missing from the control catalog"
        control = catalog[control_id]
        assert control["framework_id"] == "cis_aws"
        assert control["official_source_ref"] == "cis_aws"
        # The declared evaluation rule must be one the policy engine accepts.
        assert validate_rule(control["evaluation_rule"]) == []


def test_connector_finding_constants_include_cis_ids() -> None:
    # Every AWS finding type that maps to a CIS recommendation carries its ID.
    assert "CIS-AWS-1.10" in MFA_CONTROLS
    assert "CIS-AWS-1.8" in POLICY_CONTROLS
    assert "CIS-AWS-1.14" in ACCESS_KEY_CONTROLS


def test_emitted_aws_findings_carry_their_cis_control_ids() -> None:
    rows = collect_aws_evidence(
        AWSFixtureClient(FIXTURE),
        account_id=ACCOUNT,
        collected_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    by_type: dict[str, list[dict]] = {}
    for row in rows:
        by_type.setdefault(row["event_type"], []).append(row)

    # The base fixture exercises MFA + password-policy findings; assert each
    # emitted event of those types carries its mapped CIS control.
    for event_type in ("aws.iam.mfa_enrollment", "aws.iam.password_policy"):
        events = by_type.get(event_type, [])
        assert events, f"no {event_type} events emitted"
        cis_id = CIS_FINDING_CONTROLS[event_type]
        for event in events:
            assert cis_id in event["controls"], f"{event_type} missing {cis_id}"


def test_failing_mfa_finding_fails_the_mapped_cis_control(tmp_path: Path) -> None:
    rows = collect_aws_evidence(
        AWSFixtureClient(FIXTURE),
        account_id=ACCOUNT,
        collected_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    # The fixture includes a console user without MFA -> an open CIS-AWS-1.10 finding.
    raw = tmp_path / "raw" / "events.jsonl"
    raw.parent.mkdir(parents=True)
    raw.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n", encoding="utf-8")

    out = tmp_path / "out"
    run_pipeline(raw, out)
    rows = [__import__("json").loads(line) for line in (out / "gold" / "control_tests.jsonl").read_text().splitlines()]
    control_tests = {t["control_id"]: t for t in rows}
    assert "CIS-AWS-1.10" in control_tests
    assert control_tests["CIS-AWS-1.10"]["result"] == "fail"


def test_cis_controls_resolve_through_control_map() -> None:
    control_map = load_control_map()
    for control_id in CIS_FINDING_CONTROLS.values():
        assert control_id in control_map
        assert control_map[control_id]["framework"] == "CIS AWS Foundations Benchmark"
