"""AWS posture-evidence connector runner tests (fixture-backed)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from security_lakehouse.connector_runner import CONNECTOR_RAW_FILE, ConnectorSyncError, run_connector_sync
from security_lakehouse.connector_state import (
    append_config_event,
    has_adapter,
    latest_run,
    run_probe,
)
from security_lakehouse.connectors_aws import AWSClient, AWSFixtureClient, collect_aws_evidence
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE = Path(__file__).parent / "fixtures" / "aws"
ACCOUNT = "123456789012"


def _by_asset(rows: list[dict], event_type: str) -> dict[str, dict]:
    return {r["entity"]["asset_id"]: r for r in rows if r["event_type"] == event_type}


def test_collect_aws_evidence_is_schema_valid_and_mapped() -> None:
    client = AWSFixtureClient(FIXTURE)
    rows = collect_aws_evidence(
        client,
        account_id=ACCOUNT,
        collected_at=datetime(2026, 5, 28, tzinfo=UTC),
    )

    assert validate_raw_events(rows) == []
    # 3 users -> 3 identity + 3 mfa events; 1 account -> 1 password-policy event.
    assert len(rows) == 7

    identity = _by_asset(rows, "aws.iam.user_access")
    mfa = _by_asset(rows, "aws.iam.mfa_enrollment")
    policy = [r for r in rows if r["event_type"] == "aws.iam.password_policy"]
    assert len(identity) == 3
    assert len(mfa) == 3
    assert len(policy) == 1

    # Every emitted event maps to controls that exist in the catalog.
    for row in rows:
        assert row["source"] == "aws"
        assert "SOC2-CC6.1" in row["controls"]

    # MFA-enrolled user passes; user without an MFA device is a high open finding.
    enrolled = mfa["aws:iam:user/ada-lovelace"]
    assert enrolled["status"] == "pass"
    assert enrolled["severity"] == "info"
    assert enrolled["attributes"]["mfa_enrolled"] is True
    assert enrolled["attributes"]["mfa_device_count"] == 1

    missing = mfa["aws:iam:user/grace-hopper"]
    assert missing["status"] == "open"
    assert missing["severity"] == "high"
    assert missing["attributes"]["needs_mfa"] is True

    # Admin-path principal is surfaced as a high open identity finding for review.
    admin = identity["aws:iam:user/break-glass-admin"]
    assert admin["status"] == "open"
    assert admin["severity"] == "high"
    assert admin["attributes"]["privileged"] is True

    # The weak fixture password policy is an open medium config finding.
    pwd = policy[0]
    assert pwd["entity"]["asset_id"] == f"aws:account:{ACCOUNT}"
    assert pwd["entity"]["asset_type"] == "account_config"
    assert pwd["status"] == "open"
    assert pwd["severity"] == "medium"
    assert pwd["attributes"]["password_policy_strong"] is False
    assert "minimum_password_length_below_14" in pwd["attributes"]["weaknesses"]

    # Asset + evidence shapes are AWS-scoped and point at the read-only ARN.
    sample = identity["aws:iam:user/ada-lovelace"]
    assert sample["entity"]["asset_type"] == "identity_account"
    assert sample["evidence"]["evidence_ref"] == "arn:aws:iam::123456789012:user/ada-lovelace"
    assert pwd["evidence"]["evidence_ref"].endswith(":account-password-policy")


def test_aws_connector_sync_writes_raw_and_materializes_lake(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="aws-posture", state="enabled", actor="alice")
    result = run_connector_sync(
        tmp_path,
        connector_id="aws-posture",
        fixture_dir=FIXTURE,
    )
    assert result.result == "ok"
    assert result.evidence_count == 7
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == 7
    assert all(r["source"] == "aws" for r in raw_rows)
    assert (tmp_path / "bronze" / "raw_events.jsonl").is_file()
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "current_posture.json").is_file()

    run = latest_run(tmp_path, "aws-posture", kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == 7


def test_aws_connector_sync_upserts_stable_event_ids(tmp_path: Path) -> None:
    append_config_event(tmp_path, connector_id="aws-posture", state="enabled", actor="a")
    first = run_connector_sync(tmp_path, connector_id="aws-posture", fixture_dir=FIXTURE)
    second = run_connector_sync(
        tmp_path,
        connector_id="aws-posture",
        fixture_dir=FIXTURE,
        materialize=False,
    )
    assert first.evidence_count == second.evidence_count == 7
    assert len(read_jsonl(tmp_path / CONNECTOR_RAW_FILE)) == 7


def test_aws_connector_sync_requires_enabled_connector(tmp_path: Path) -> None:
    with pytest.raises(ConnectorSyncError, match="not enabled") as exc:
        run_connector_sync(tmp_path, connector_id="aws-posture", fixture_dir=FIXTURE)
    assert exc.value.run["result"] == "error"


def test_aws_connector_sync_without_fixture_or_creds_errors(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AWS_ACCOUNT_ID", raising=False)
    append_config_event(tmp_path, connector_id="aws-posture", state="enabled", actor="a")
    with pytest.raises(ConnectorSyncError, match="requires --fixture-dir"):
        run_connector_sync(tmp_path, connector_id="aws-posture")


def test_aws_adapter_is_registered_and_probe_reports_ok(tmp_path: Path) -> None:
    assert has_adapter("aws-posture") is True
    # Before enablement the probe is skipped (no synthetic collection signal).
    skipped = run_probe(tmp_path, connector_id="aws-posture")
    assert skipped["result"] == "skipped"
    assert "not enabled" in skipped["error"]

    append_config_event(tmp_path, connector_id="aws-posture", state="enabled", actor="a")
    ok = run_probe(tmp_path, connector_id="aws-posture")
    # Adapter-available -> probe is "ok", not "skipped", and reports no count.
    assert ok["result"] == "ok"
    assert ok["evidence_count"] is None


class _FakeBoto3:
    """Minimal boto3 stand-in to exercise AWSClient auth modes offline."""

    def __init__(self) -> None:
        self.assume_calls: list[dict] = []
        self.iam_from = ""  # "client" (ambient) or "session" (assumed)
        self.session_creds: dict | None = None

    def client(self, service: str, region_name=None):  # noqa: ANN001
        if service == "sts":
            outer = self

            class _STS:
                def assume_role(self, **kwargs):  # noqa: ANN003
                    outer.assume_calls.append(kwargs)
                    return {
                        "Credentials": {
                            "AccessKeyId": "ASIA_TMP",
                            "SecretAccessKey": "secret_tmp",
                            "SessionToken": "token_tmp",
                        }
                    }

            return _STS()
        if service == "iam":
            self.iam_from = "client"
            return SimpleNamespace(get_paginator=lambda *_a, **_k: None)
        raise AssertionError(f"unexpected client {service}")

    def Session(self, **creds):  # noqa: N802, ANN003
        self.session_creds = creds
        outer = self

        class _Session:
            def client(self, service: str):  # noqa: ANN001
                assert service == "iam"
                outer.iam_from = "session"
                return SimpleNamespace(get_paginator=lambda *_a, **_k: None)

        return _Session()


def test_aws_client_assumes_role_with_external_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # The hosted-GRC connect model: hand TrustOps a Role ARN + External ID and it
    # assumes the read-only role via STS — no static key, no ambient identity.
    fake = _FakeBoto3()
    monkeypatch.setitem(sys.modules, "boto3", fake)

    AWSClient(role_arn="arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole", external_id="ext-secret-123")

    assert len(fake.assume_calls) == 1
    call = fake.assume_calls[0]
    assert call["RoleArn"].endswith(":role/TrustOpsPostureReadOnlyRole")
    assert call["ExternalId"] == "ext-secret-123"
    assert call["RoleSessionName"] == "trustops-posture"
    # IAM client is built from the assumed short-lived session, not ambient.
    assert fake.iam_from == "session"
    assert fake.session_creds["aws_session_token"] == "token_tmp"


def test_aws_client_uses_ambient_chain_without_role_arn(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeBoto3()
    monkeypatch.setitem(sys.modules, "boto3", fake)

    AWSClient()

    # No assume-role call; IAM client comes straight from the provider chain.
    assert fake.assume_calls == []
    assert fake.iam_from == "client"


def test_mfa_finding_only_applies_to_console_users(tmp_path: Path) -> None:
    # MFA is a console (human) control. A key-only service identity with no login
    # profile must not be flagged for "no MFA"; only a console user is.
    fixture = tmp_path / "aws"
    fixture.mkdir()
    (fixture / "iam_users.json").write_text(
        json.dumps(
            [
                {"UserName": "human-admin", "Arn": f"arn:aws:iam::{ACCOUNT}:user/human-admin"},
                {"UserName": "svc-scanner", "Arn": f"arn:aws:iam::{ACCOUNT}:user/svc-scanner"},
            ]
        ),
        encoding="utf-8",
    )
    (fixture / "mfa_devices.json").write_text(json.dumps({"human-admin": [], "svc-scanner": []}), encoding="utf-8")
    # Only the human has a console login profile.
    (fixture / "login_profiles.json").write_text(json.dumps(["human-admin"]), encoding="utf-8")

    rows = collect_aws_evidence(AWSFixtureClient(fixture), account_id=ACCOUNT)
    assert validate_raw_events(rows) == []
    mfa = {r["attributes"]["user_name"]: r for r in rows if r["event_type"] == "aws.iam.mfa_enrollment"}

    # Console user without MFA -> high open finding.
    assert mfa["human-admin"]["status"] == "open"
    assert mfa["human-admin"]["severity"] == "high"
    assert mfa["human-admin"]["attributes"]["needs_mfa"] is True
    assert mfa["human-admin"]["attributes"]["console_access"] is True
    assert mfa["human-admin"]["attributes"]["identity_type"] == "human"

    # Service identity (no console login) -> not a finding; MFA marked N/A.
    assert mfa["svc-scanner"]["status"] == "pass"
    assert mfa["svc-scanner"]["severity"] == "info"
    assert mfa["svc-scanner"]["attributes"]["needs_mfa"] is False
    assert mfa["svc-scanner"]["attributes"]["console_access"] is False
    assert mfa["svc-scanner"]["attributes"]["mfa_not_applicable"] is True
    assert mfa["svc-scanner"]["attributes"]["identity_type"] == "service"


def test_aws_client_console_access_reads_login_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    # GetLoginProfile success => console user; NoSuchEntity (raises) => programmatic.
    class _IAM:
        def get_login_profile(self, *, UserName: str):  # noqa: N803
            if UserName == "human":
                return {"LoginProfile": {"UserName": "human"}}
            raise RuntimeError("NoSuchEntity")

    client = AWSClient.__new__(AWSClient)
    client._iam = _IAM()
    assert client.console_access("human") is True
    assert client.console_access("svc") is False
