"""Snowflake evidence-lake connector tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from security_lakehouse import connector_runner, connector_state
from security_lakehouse.connectors_snowflake import (
    SnowflakeFixtureClient,
    _probe_query_params,
    collect_snowflake_evidence,
    probe_snowflake_access,
)
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "snowflake"


def test_collect_snowflake_fixture_evidence_validates() -> None:
    rows = collect_snowflake_evidence(
        SnowflakeFixtureClient(FIXTURE_DIR, account="acme_snowflake"),
        collected_at=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
    )

    assert len(rows) == 8
    assert validate_raw_events(rows) == []
    assert {row["source"] for row in rows} == {"snowflake"}
    assert {row["event_type"] for row in rows} == {
        "snowflake.asset.risk",
        "snowflake.audit.event",
        "snowflake.control.posture",
        "snowflake.evidence.bundle",
    }
    assert any(row["status"] == "open" and row["severity"] == "high" for row in rows)
    assert any(row["entity"]["asset_id"] == "snowflake:warehouse:trustops_wh" for row in rows)


def test_snowflake_sync_writes_raw_evidence_and_materializes(tmp_path: Path) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )

    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        fixture_dir=FIXTURE_DIR,
    )

    assert result.result == "ok"
    assert result.evidence_count == 8
    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert len(raw_rows) == 8
    assert validate_raw_events(raw_rows) == []
    assert (tmp_path / "silver" / "normalized_events.jsonl").is_file()
    assert (tmp_path / "gold" / "control_posture.jsonl").is_file()
    assert (tmp_path / "gold" / "asset_risk.jsonl").is_file()
    run = connector_state.latest_run(tmp_path, "snowflake-evidence-lake", kind="sync")
    assert run is not None
    assert run["result"] == "ok"
    assert run["evidence_count"] == 8


def test_snowflake_live_requires_account_and_user_for_sso_or_oauth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    for name in (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_OAUTH_TOKEN",
        "SNOWFLAKE_PRIVATE_KEY_FILE",
        "SNOWFLAKE_AUTHENTICATOR",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(connector_runner.ConnectorSyncError, match="SNOWFLAKE_ACCOUNT"):
        connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake", materialize=False)


def test_snowflake_live_defaults_to_externalbrowser_without_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    captured: dict[str, object] = {}

    class FakeSnowflakeClient:
        def __init__(self, *, query_params: dict[str, object], views: dict[str, str]) -> None:
            captured["query_params"] = query_params
            captured["views"] = views

    monkeypatch.setattr(connector_runner, "SnowflakeClient", FakeSnowflakeClient)
    monkeypatch.setattr(connector_runner, "collect_snowflake_evidence", lambda client, account=None: [])
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "acme-trustops")
    monkeypatch.setenv("SNOWFLAKE_USER", "trustops.reader@example.com")
    monkeypatch.delenv("SNOWFLAKE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("SNOWFLAKE_AUTHENTICATOR", raising=False)

    result = connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake", materialize=False)

    assert result.result == "ok"
    assert captured["query_params"] == {
        "account": "acme-trustops",
        "user": "trustops.reader@example.com",
        "authenticator": "externalbrowser",
        "token": None,
        "warehouse": None,
        "database": None,
        "schema": None,
        "role": None,
    }


def test_snowflake_live_uses_oauth_when_token_env_is_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    captured: dict[str, object] = {}

    class FakeSnowflakeClient:
        def __init__(self, *, query_params: dict[str, object], views: dict[str, str]) -> None:
            captured["query_params"] = query_params

    monkeypatch.setattr(connector_runner, "SnowflakeClient", FakeSnowflakeClient)
    monkeypatch.setattr(connector_runner, "collect_snowflake_evidence", lambda client, account=None: [])
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "acme-trustops")
    monkeypatch.setenv("SNOWFLAKE_USER", "trustops.reader@example.com")
    monkeypatch.setenv("SNOWFLAKE_OAUTH_TOKEN", "read-only-oauth-token")

    result = connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake", materialize=False)

    assert result.result == "ok"
    assert captured["query_params"]["authenticator"] == "oauth"
    assert captured["query_params"]["token"] == "read-only-oauth-token"


def test_snowflake_live_uses_key_pair_file_for_service_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    captured: dict[str, object] = {}

    class FakeSnowflakeClient:
        def __init__(self, *, query_params: dict[str, object], views: dict[str, str]) -> None:
            captured["query_params"] = query_params

    monkeypatch.setattr(connector_runner, "SnowflakeClient", FakeSnowflakeClient)
    monkeypatch.setattr(connector_runner, "collect_snowflake_evidence", lambda client, account=None: [])
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "acme-trustops")
    monkeypatch.setenv("SNOWFLAKE_USER", "TRUSTOPS_INGEST_SVC")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_FILE", "/run/secrets/trustops_snowflake_key.p8")
    monkeypatch.delenv("SNOWFLAKE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("SNOWFLAKE_AUTHENTICATOR", raising=False)

    result = connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake", materialize=False)

    assert result.result == "ok"
    assert captured["query_params"]["authenticator"] == "SNOWFLAKE_JWT"
    assert captured["query_params"]["private_key_file"] == "/run/secrets/trustops_snowflake_key.p8"
    assert captured["query_params"]["token"] is None


def test_snowflake_probe_resolves_oauth_ref_from_environment() -> None:
    params = _probe_query_params(
        credentials={
            "account": "acme-trustops",
            "user": "trustops.reader@example.com",
            "credential_ref": "SNOWFLAKE_OAUTH_TOKEN",
        },
        options={
            "warehouse": "TRUSTOPS_READ_WH",
            "database": "TRUSTOPS_SECURITY_LAKE",
            "schema": "EVIDENCE",
            "role": "TRUSTOPS_READER",
        },
        env={"SNOWFLAKE_OAUTH_TOKEN": "read-only-oauth-token"},
    )

    assert params == {
        "account": "acme-trustops",
        "user": "trustops.reader@example.com",
        "authenticator": "oauth",
        "token": "read-only-oauth-token",
        "warehouse": "TRUSTOPS_READ_WH",
        "database": "TRUSTOPS_SECURITY_LAKE",
        "schema": "EVIDENCE",
        "role": "TRUSTOPS_READER",
    }


def test_snowflake_probe_resolves_private_key_ref_from_environment() -> None:
    params = _probe_query_params(
        credentials={
            "account": "acme-trustops",
            "user": "TRUSTOPS_INGEST_SVC",
            "private_key_ref": "SNOWFLAKE_PRIVATE_KEY_FILE",
            "private_key_file_pwd_ref": "SNOWFLAKE_PRIVATE_KEY_FILE_PWD",
        },
        options={
            "warehouse": "TRUSTOPS_READ_WH",
            "database": "TRUSTOPS_SECURITY_LAKE",
            "schema": "EVIDENCE",
            "role": "TRUSTOPS_READER",
        },
        env={
            "SNOWFLAKE_PRIVATE_KEY_FILE": "/run/secrets/trustops_snowflake_key.p8",
            "SNOWFLAKE_PRIVATE_KEY_FILE_PWD": "key-password",
        },
    )

    assert params == {
        "account": "acme-trustops",
        "user": "TRUSTOPS_INGEST_SVC",
        "authenticator": "SNOWFLAKE_JWT",
        "token": None,
        "warehouse": "TRUSTOPS_READ_WH",
        "database": "TRUSTOPS_SECURITY_LAKE",
        "schema": "EVIDENCE",
        "role": "TRUSTOPS_READER",
        "private_key_file": "/run/secrets/trustops_snowflake_key.p8",
        "private_key_file_pwd": "key-password",
    }


def test_snowflake_probe_rejects_missing_private_key_ref_without_connection() -> None:
    with pytest.raises(ValueError, match="SNOWFLAKE_PRIVATE_KEY_FILE"):
        probe_snowflake_access(
            credentials={
                "account": "acme-trustops",
                "user": "TRUSTOPS_INGEST_SVC",
                "private_key_ref": "SNOWFLAKE_PRIVATE_KEY_FILE",
            },
            options={
                "warehouse": "TRUSTOPS_READ_WH",
                "database": "TRUSTOPS_SECURITY_LAKE",
                "schema": "EVIDENCE",
            },
            env={},
        )


def test_snowflake_probe_rejects_missing_oauth_ref_without_connection() -> None:
    with pytest.raises(ValueError, match="SNOWFLAKE_OAUTH_TOKEN"):
        probe_snowflake_access(
            credentials={
                "account": "acme-trustops",
                "user": "trustops.reader@example.com",
                "credential_ref": "SNOWFLAKE_OAUTH_TOKEN",
            },
            options={
                "warehouse": "TRUSTOPS_READ_WH",
                "database": "TRUSTOPS_SECURITY_LAKE",
                "schema": "EVIDENCE",
            },
            env={},
        )
