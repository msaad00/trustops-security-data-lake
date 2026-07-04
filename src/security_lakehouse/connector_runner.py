"""Connector sync runner.

This module turns catalog entries from static access contracts into executable
evidence collection runs. Registered runners collect from source APIs or
existing evidence lakes, write raw evidence into the managed raw-event file,
and optionally materialize bronze/silver/gold outputs.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from security_lakehouse import netguard
from security_lakehouse.connector_state import _safe_run_error, append_run_event, latest_config
from security_lakehouse.connectors import load_connector_catalog
from security_lakehouse.connectors_aws import (
    AWSClient,
    AWSFixtureClient,
    collect_aws_evidence,
)
from security_lakehouse.connectors_azure import (
    AzureCliClient,
    AzureClient,
    AzureFixtureClient,
    collect_azure_evidence,
)
from security_lakehouse.connectors_gcp import (
    GCPClient,
    GCPFixtureClient,
    collect_gcp_evidence,
)
from security_lakehouse.connectors_google_workspace import (
    GoogleWorkspaceClient,
    GoogleWorkspaceFixtureClient,
    collect_google_workspace_evidence,
)
from security_lakehouse.connectors_jira import (
    JiraClient,
    JiraFixtureClient,
    collect_jira_evidence,
)
from security_lakehouse.connectors_okta import (
    OktaClient,
    OktaFixtureClient,
    collect_okta_evidence,
)
from security_lakehouse.connectors_snowflake import (
    DEFAULT_VIEWS as SNOWFLAKE_DEFAULT_VIEWS,
)
from security_lakehouse.connectors_snowflake import (
    SnowflakeClient,
    SnowflakeFixtureClient,
    _probe_query_params,
    collect_snowflake_evidence,
)
from security_lakehouse.ingestion.merge import dedupe_by_key
from security_lakehouse.ingestion.watermark import read_watermark, write_watermark
from security_lakehouse.io import read_jsonl, write_jsonl
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.repo_governance import sync_repo_governance
from security_lakehouse.sinks import land_if_configured
from security_lakehouse.validation import validate_raw_events

CONNECTOR_RAW_FILE = "raw/connector_events.jsonl"

# Default ``token_env`` for the CLI sync entrypoint. Provider-specific
# installation or OAuth token environment variables are used unless an operator
# explicitly passes ``--token-env``.
DEFAULT_TOKEN_ENV = "__provider_default__"
GITHUB_APP_INSTALLATION_TOKEN_ENV = "TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"


def _resolve_provider_token(token_env: str, provider_env: str, env: dict[str, str]) -> str | None:
    """Resolve a third-party source token without cross-provider reuse.

    An explicit ``--token-env`` override wins; otherwise the provider-specific
    variable is used. The generic default is never read for a connector, so one
    source credential cannot silently become another source's auth header.
    """
    if token_env != DEFAULT_TOKEN_ENV:
        explicit = env.get(token_env)
        if explicit:
            return explicit
    return env.get(provider_env)


# Environment variable carrying the Okta org base URL for live collection. The
# token is read from ``token_env`` (defaults to OKTA_API_TOKEN for this runner).
OKTA_ORG_URL_ENV = "OKTA_ORG_URL"

# Environment variables carrying the AWS account id + region for live
# collection. Credentials resolve through boto3's standard provider chain,
# preferably SSO, assumed roles, workload identity, or instance roles.
AWS_ACCOUNT_ID_ENV = "AWS_ACCOUNT_ID"
AWS_REGION_ENV = "AWS_REGION"
# Optional cross-account assume-role auth (the hosted-GRC connect model): the
# customer deploys the read-only role and hands TrustOps only the Role ARN +
# External ID. TrustOps assumes it with its own ambient/base identity. These can
# come from the connector's stored credentials or be overridden by env.
AWS_ROLE_ARN_ENV = "AWS_ROLE_ARN"
AWS_EXTERNAL_ID_ENV = "AWS_EXTERNAL_ID"

# Environment variable carrying the Google Workspace customer id for live
# collection. The OAuth bearer token is read from ``token_env`` (defaults to
# GOOGLE_WORKSPACE_ACCESS_TOKEN for this runner).
GOOGLE_WORKSPACE_CUSTOMER_ID_ENV = "GOOGLE_WORKSPACE_CUSTOMER_ID"

# Environment variable carrying the GCP project id for live collection.
# Credentials resolve through Google's Application Default Credentials chain
# (GOOGLE_APPLICATION_CREDENTIALS / workload identity / metadata server).
GCP_PROJECT_ID_ENV = "GCP_PROJECT_ID"

# Environment variable carrying the Azure subscription id for live collection.
# Credentials resolve through DefaultAzureCredential (service-principal env vars
# AZURE_CLIENT_ID/AZURE_TENANT_ID/AZURE_CLIENT_SECRET, managed identity, CLI).
AZURE_SUBSCRIPTION_ID_ENV = "AZURE_SUBSCRIPTION_ID"

# Environment variables carrying the Jira Cloud site base URL and the account
# email used for HTTP Basic read auth. The read-only API token is read from
# ``token_env`` (defaults to JIRA_API_TOKEN for this runner).
JIRA_BASE_URL_ENV = "JIRA_BASE_URL"
JIRA_EMAIL_ENV = "JIRA_EMAIL"

# Environment variables carrying Snowflake connection metadata for read-only
# evidence-lake collection. Browser SSO is only for human POCs. Continuous
# automation should use a service user with key-pair auth or OAuth materialized
# by the runtime secret manager.
SNOWFLAKE_ACCOUNT_ENV = "SNOWFLAKE_ACCOUNT"
SNOWFLAKE_USER_ENV = "SNOWFLAKE_USER"
SNOWFLAKE_OAUTH_TOKEN_ENV = "SNOWFLAKE_OAUTH_TOKEN"
SNOWFLAKE_PRIVATE_KEY_FILE_ENV = "SNOWFLAKE_PRIVATE_KEY_FILE"
SNOWFLAKE_PRIVATE_KEY_FILE_PWD_ENV = "SNOWFLAKE_PRIVATE_KEY_FILE_PWD"
SNOWFLAKE_AUTHENTICATOR_ENV = "SNOWFLAKE_AUTHENTICATOR"
SNOWFLAKE_WAREHOUSE_ENV = "SNOWFLAKE_WAREHOUSE"
SNOWFLAKE_DATABASE_ENV = "SNOWFLAKE_DATABASE"
SNOWFLAKE_SCHEMA_ENV = "SNOWFLAKE_SCHEMA"
SNOWFLAKE_ROLE_ENV = "SNOWFLAKE_ROLE"


@dataclass(frozen=True)
class ConnectorSyncResult:
    """Result returned by a connector sync run."""

    connector_id: str
    result: str
    raw_path: str
    evidence_count: int
    materialized: bool
    run: dict[str, Any]
    # High-water cursor this connector has synced through (append/event-log
    # connectors only); ``None`` for snapshot connectors that replace state.
    watermark_cursor: str | None = None


def run_connector_sync(
    lake_dir: str | Path,
    *,
    connector_id: str,
    actor: str = "system",
    repo: str | None = None,
    fixture_dir: str | Path | None = None,
    token_env: str = DEFAULT_TOKEN_ENV,
    materialize: bool = True,
) -> ConnectorSyncResult:
    """Run one configured connector and persist its evidence + run event."""
    lake = Path(lake_dir)
    start = time.perf_counter()
    write_mode = _write_mode(connector_id)
    try:
        config = _require_enabled(lake, connector_id)
        credentials = dict(config.get("credentials") or {})
        options = dict(config.get("options") or {})
        effective_repo = repo or str(options.get("repo") or "").strip() or None
        effective_fixture = fixture_dir or options.get("fixture_dir")
        effective_token_env = token_env
        if token_env == DEFAULT_TOKEN_ENV:
            ref = str(credentials.get("credential_ref") or options.get("token_env") or "").strip()
            if ref:
                effective_token_env = ref
        # Append/event-log connectors resume from their last high-water cursor so
        # a sync only needs to fetch what is new; snapshot connectors always pull
        # the full current state, so they carry no watermark.
        since = read_watermark(lake, connector_id) if write_mode == "append" else None
        rows = _collect(
            connector_id,
            repo=effective_repo,
            fixture_dir=effective_fixture,
            token_env=effective_token_env,
            since=since,
            credentials=credentials,
            options=options,
        )
        raw_path = lake / CONNECTOR_RAW_FILE
        _upsert_raw_events(raw_path, rows, connector_id=connector_id, write_mode=write_mode)
        cursor = _advance_watermark(lake, connector_id, rows, write_mode=write_mode)
        if materialize:
            run_pipeline(raw_path, lake)
            _land_to_sink(lake, connector_id=connector_id)
            _fire_evidence_changed(lake, connector_id)
        run = append_run_event(
            lake,
            connector_id=connector_id,
            kind="sync",
            result="ok",
            actor=actor,
            duration_ms=_duration_ms(start),
            evidence_count=len(rows),
        )
        return ConnectorSyncResult(
            connector_id=connector_id,
            result="ok",
            raw_path=str(raw_path),
            evidence_count=len(rows),
            materialized=materialize,
            run=run,
            watermark_cursor=cursor,
        )
    except Exception as exc:
        run = append_run_event(
            lake,
            connector_id=connector_id,
            kind="sync",
            result="error",
            actor=actor,
            duration_ms=_duration_ms(start),
            error=_safe_run_error(exc),
        )
        raise ConnectorSyncError(str(exc), run=run) from exc


class ConnectorSyncError(RuntimeError):
    """Raised when a connector sync fails after recording a run event."""

    def __init__(self, message: str, *, run: dict[str, Any]) -> None:
        super().__init__(message)
        self.run = run


def _land_to_sink(lake: Path, *, connector_id: str | None = None) -> None:
    """Project the freshly materialized lake to a configured external sink.

    The local lake is the source of truth; configured evidence sinks are optional,
    idempotent projections, so a sink failure — warehouse down, transient auth —
    is reported to stderr and swallowed rather than failing the sync. No-op
    unless a Snowflake, ClickHouse, or DuckDB sink is configured.
    """
    env = dict(os.environ)
    if connector_id == "snowflake-evidence-lake":
        # Snowflake can be either an existing read-only evidence lake or an
        # optional write sink. A read-connector sync must not infer write-sink
        # intent from the same SNOWFLAKE_* runtime variables used for key-pair
        # auth, otherwise a least-privilege reader sees noisy sink failures.
        for key in (
            SNOWFLAKE_ACCOUNT_ENV,
            SNOWFLAKE_USER_ENV,
            SNOWFLAKE_PRIVATE_KEY_FILE_ENV,
            SNOWFLAKE_PRIVATE_KEY_FILE_PWD_ENV,
            SNOWFLAKE_ROLE_ENV,
            SNOWFLAKE_WAREHOUSE_ENV,
            SNOWFLAKE_DATABASE_ENV,
            SNOWFLAKE_SCHEMA_ENV,
        ):
            env.pop(key, None)
    try:
        landed = land_if_configured(lake, env)
    except Exception as exc:  # noqa: BLE001 - sink is optional; never fatal to collection
        print(
            f"warning: evidence sink load failed ({type(exc).__name__}); local lake is unaffected",
            file=sys.stderr,
        )
        return
    if landed:
        total = sum(sum(tables.values()) for tables in landed.values())
        print(f"evidence sink: landed {total} rows across {list(landed)} -> {landed}", file=sys.stderr)


def _fire_evidence_changed(lake: Path, connector_id: str) -> None:
    """Push side of continuous eval: a sync that landed evidence runs the
    ``trigger.evidence_changed`` workflows immediately, instead of waiting for the
    next cron tick. Best-effort — an automation failure never fails collection.
    """
    try:
        from security_lakehouse.workflows import run_evidence_changed_workflows  # noqa: PLC0415

        runs = run_evidence_changed_workflows(lake, connector_id=connector_id)
    except Exception as exc:  # noqa: BLE001 - automations are optional; never fatal to a sync
        print(f"warning: evidence_changed automations failed ({type(exc).__name__})", file=sys.stderr)
        return
    if runs:
        print(f"evidence_changed: fired {len(runs)} workflow(s) after {connector_id} sync", file=sys.stderr)


def _require_enabled(lake: Path, connector_id: str) -> dict[str, Any]:
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        raise ValueError(f"unknown connector_id {connector_id!r}")
    config = latest_config(lake, connector_id)
    if not config or config.get("state") != "enabled":
        raise ValueError("connector is not enabled; configure it before sync")
    return config


@dataclass(frozen=True)
class SyncInputs:
    """The sync-call inputs handed to a registered connector builder.

    A builder receives the full set of inputs ``run_connector_sync`` knows
    about (plus process ``env``) and is free to use whichever apply to it. This
    keeps the registry contract uniform so a new connector never has to change
    the dispatch site.
    """

    repo: str | None
    fixture_dir: str | Path | None
    token_env: str
    env: dict[str, str]
    # Last high-water cursor for append/event-log connectors, so a builder can
    # scope its pull to records newer than ``since`` (``None`` = full pull).
    since: str | None = None
    # Non-secret identity fields persisted at configure time (e.g. subscription_id,
    # account_id, project_id). Secret material is never stored here — it is
    # redacted to a fingerprint in connector_state — so builders read live secrets
    # from env/credential providers and fall back to these for identity scoping.
    credentials: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


# A connector builder takes the uniform :class:`SyncInputs` and returns the
# collected raw evidence rows. Builders construct the right client (fixture vs
# live) and delegate to that connector's ``collect_*`` function unchanged.
ConnectorBuilder = Callable[[SyncInputs], list[dict[str, Any]]]


# ---------------------------------------------------------------------------
# Connector registry — the single dispatch table for sync collection.
#
# To add a connector, you do NOT edit run_connector_sync or any if/elif chain:
#
#   1. Write ``connectors_<x>.py`` exposing a ``collect_<x>_evidence`` function
#      (and its live + fixture client classes), mirroring connectors_okta.py.
#   2. Add one ``REGISTRY["<x>-id"] = _build_<x>`` entry below, where
#      ``_build_<x>`` is a builder closure that reads the relevant fields off
#      ``SyncInputs`` and calls your ``collect_*`` function.
#
# Registering here wires sync dispatch. Mark the same connector_id with
# ``is_implemented`` in ``connectors/catalog.json`` so connector probes and the
# console can report adapter availability without importing this module.
# ---------------------------------------------------------------------------


def _build_github(inputs: SyncInputs) -> list[dict[str, Any]]:
    effective_repo = (inputs.repo or str(inputs.options.get("repo") or "")).strip()
    if not effective_repo:
        raise ValueError("github-security sync requires options.repo (owner/name)")
    token_env = GITHUB_APP_INSTALLATION_TOKEN_ENV if inputs.token_env == DEFAULT_TOKEN_ENV else inputs.token_env
    cred_ref = str(inputs.credentials.get("credential_ref") or "").strip()
    if cred_ref:
        token_env = cred_ref
    return sync_repo_governance(
        effective_repo,
        fixture_dir=inputs.fixture_dir,
        token_env=token_env,
        provider="github",
    )


def _build_gitlab(inputs: SyncInputs) -> list[dict[str, Any]]:
    effective_repo = (inputs.repo or str(inputs.options.get("repo") or "")).strip()
    if not effective_repo:
        raise ValueError("gitlab-security sync requires options.repo (namespace/project)")
    token_env = "TRUSTOPS_GITLAB_ACCESS_TOKEN" if inputs.token_env == DEFAULT_TOKEN_ENV else inputs.token_env
    cred_ref = str(inputs.credentials.get("credential_ref") or "").strip()
    if cred_ref:
        token_env = cred_ref
    return sync_repo_governance(
        effective_repo,
        fixture_dir=inputs.fixture_dir,
        token_env=token_env,
        provider="gitlab",
    )


def _build_okta(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_okta(
        fixture_dir=inputs.fixture_dir,
        token_env=inputs.token_env,
        env=inputs.env,
        credentials=inputs.credentials,
    )


def _build_aws(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_aws(fixture_dir=inputs.fixture_dir, env=inputs.env, credentials=inputs.credentials)


def _build_google_workspace(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_google_workspace(
        fixture_dir=inputs.fixture_dir,
        token_env=inputs.token_env,
        env=inputs.env,
        credentials=inputs.credentials,
    )


def _build_gcp(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_gcp(fixture_dir=inputs.fixture_dir, env=inputs.env, credentials=inputs.credentials)


def _build_azure(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_azure(fixture_dir=inputs.fixture_dir, env=inputs.env, credentials=inputs.credentials)


def _build_jira(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_jira(
        fixture_dir=inputs.fixture_dir,
        token_env=inputs.token_env,
        env=inputs.env,
        credentials=inputs.credentials,
    )


def _build_snowflake(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_snowflake(
        fixture_dir=inputs.fixture_dir,
        token_env=inputs.token_env,
        env=inputs.env,
        credentials=inputs.credentials,
        options=inputs.options,
    )


REGISTRY: dict[str, ConnectorBuilder] = {
    "snowflake-evidence-lake": _build_snowflake,
    "github-security": _build_github,
    "gitlab-security": _build_gitlab,
    "okta-identity": _build_okta,
    "aws-posture": _build_aws,
    "google-workspace-identity": _build_google_workspace,
    "gcp-posture": _build_gcp,
    "azure-posture": _build_azure,
    "jira-ticketing": _build_jira,
}


def registered_connector_ids() -> frozenset[str]:
    """The set of connector_ids with a sync builder registered in REGISTRY.

    Tests compare this against the catalog's ``is_implemented`` metadata so the
    runner dispatch table and UI/probe adapter flags cannot drift.
    """
    return frozenset(REGISTRY)


def _collect(
    connector_id: str,
    *,
    repo: str | None,
    fixture_dir: str | Path | None,
    token_env: str,
    since: str | None = None,
    credentials: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    builder = REGISTRY.get(connector_id)
    if builder is None:
        raise ValueError(f"no sync runner registered for connector_id {connector_id!r}")
    return builder(
        SyncInputs(
            repo=repo,
            fixture_dir=fixture_dir,
            token_env=token_env,
            env=dict(os.environ),
            since=since,
            credentials=dict(credentials or {}),
            options=dict(options or {}),
        )
    )


def _collect_okta(
    *,
    fixture_dir: str | Path | None,
    token_env: str,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    client: OktaClient | OktaFixtureClient
    creds = credentials or {}
    if fixture_dir:
        client = OktaFixtureClient(fixture_dir)
    else:
        org_url = str(env.get(OKTA_ORG_URL_ENV) or creds.get("org_url") or "").strip()
        effective_token_env = str(creds.get("credential_ref") or token_env)
        token = _resolve_provider_token(effective_token_env, "OKTA_API_TOKEN", env)
        if not org_url or not token:
            raise ValueError(
                "okta-identity sync requires --fixture-dir, or "
                f"{OKTA_ORG_URL_ENV}/org_url plus a read-only API token (OKTA_API_TOKEN or --token-env)"
            )
        netguard.assert_url_is_public(org_url, label="okta org url")
        client = OktaClient(org_url, token=token)
    return collect_okta_evidence(client)


def _collect_aws(
    *,
    fixture_dir: str | Path | None,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    creds = credentials or {}
    if fixture_dir:
        fixture_account = env.get(AWS_ACCOUNT_ID_ENV) or str(creds.get("account_id") or "") or "000000000000"
        return collect_aws_evidence(AWSFixtureClient(fixture_dir), account_id=fixture_account)
    # account_id and (optional) cross-account assume-role config come from the
    # connector's stored credentials, with env overrides for operators.
    account_id = env.get(AWS_ACCOUNT_ID_ENV) or str(creds.get("account_id") or "").strip()
    if not account_id:
        raise ValueError(
            "aws-posture sync requires --fixture-dir, a configured account_id, or "
            f"{AWS_ACCOUNT_ID_ENV}, plus read-only AWS credentials "
            "(SSO profile, assumed role, instance role, or the standard provider chain)"
        )
    role_arn = (env.get(AWS_ROLE_ARN_ENV) or str(creds.get("role_arn") or "")).strip() or None
    external_id = (env.get(AWS_EXTERNAL_ID_ENV) or str(creds.get("external_id") or "")).strip() or None
    client = AWSClient(region_name=env.get(AWS_REGION_ENV), role_arn=role_arn, external_id=external_id)
    return collect_aws_evidence(client, account_id=account_id)


def _collect_google_workspace(
    *,
    fixture_dir: str | Path | None,
    token_env: str,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    client: GoogleWorkspaceClient | GoogleWorkspaceFixtureClient
    creds = credentials or {}
    if fixture_dir:
        client = GoogleWorkspaceFixtureClient(fixture_dir)
    else:
        customer_id = str(env.get(GOOGLE_WORKSPACE_CUSTOMER_ID_ENV) or creds.get("customer_id") or "").strip()
        effective_token_env = str(creds.get("credential_ref") or token_env)
        access_token = _resolve_provider_token(effective_token_env, "GOOGLE_WORKSPACE_ACCESS_TOKEN", env)
        if not customer_id or not access_token:
            raise ValueError(
                "google-workspace-identity sync requires --fixture-dir, or "
                f"{GOOGLE_WORKSPACE_CUSTOMER_ID_ENV}/customer_id plus a read-only OAuth token "
                "(GOOGLE_WORKSPACE_ACCESS_TOKEN or --token-env)"
            )
        client = GoogleWorkspaceClient(customer_id, access_token=access_token)
    return collect_google_workspace_evidence(client)


def _collect_gcp(
    *,
    fixture_dir: str | Path | None,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    stored_project = str((credentials or {}).get("project_id") or "").strip()
    if fixture_dir:
        fixture_project = env.get(GCP_PROJECT_ID_ENV) or stored_project or "fixture-project"
        return collect_gcp_evidence(GCPFixtureClient(fixture_dir, project_id=fixture_project))
    # Prefer the env override, else the project_id captured at configure time so an
    # enabled connector syncs without re-exporting GCP_PROJECT_ID.
    project_id = env.get(GCP_PROJECT_ID_ENV) or stored_project
    if not project_id:
        raise ValueError(
            "gcp-posture sync requires --fixture-dir, a configured project_id, or "
            f"{GCP_PROJECT_ID_ENV}, plus read-only GCP credentials "
            "(GOOGLE_APPLICATION_CREDENTIALS / workload identity via Application Default Credentials)"
        )
    client = GCPClient(project_id)
    return collect_gcp_evidence(client, project_id=project_id)


def _collect_azure(
    *,
    fixture_dir: str | Path | None,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    stored_subscription = str((credentials or {}).get("subscription_id") or "").strip()
    if fixture_dir:
        subscription_id = (
            env.get(AZURE_SUBSCRIPTION_ID_ENV) or stored_subscription or "00000000-0000-0000-0000-000000000000"
        )
        return collect_azure_evidence(AzureFixtureClient(fixture_dir, subscription_id=subscription_id))
    # Prefer the env var (operator override) but fall back to the subscription_id
    # captured at configure time so an enabled connector syncs without re-exporting it.
    subscription_id = env.get(AZURE_SUBSCRIPTION_ID_ENV) or stored_subscription
    if not subscription_id:
        raise ValueError(
            "azure-posture sync requires --fixture-dir, a configured subscription_id, or "
            f"{AZURE_SUBSCRIPTION_ID_ENV}, plus read-only Azure credentials "
            "(DefaultAzureCredential: service-principal env vars / managed identity / az login)"
        )
    client: AzureClient | AzureCliClient
    try:
        client = AzureClient(subscription_id)
    except RuntimeError:
        client = AzureCliClient(subscription_id)
    return collect_azure_evidence(client)


def _collect_jira(
    *,
    fixture_dir: str | Path | None,
    token_env: str,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    client: JiraClient | JiraFixtureClient
    creds = credentials or {}
    if fixture_dir:
        client = JiraFixtureClient(fixture_dir)
    else:
        base_url = str(env.get(JIRA_BASE_URL_ENV) or creds.get("base_url") or "").strip()
        email = str(env.get(JIRA_EMAIL_ENV) or creds.get("email") or "").strip()
        effective_token_env = str(creds.get("credential_ref") or token_env)
        token = _resolve_provider_token(effective_token_env, "JIRA_API_TOKEN", env)
        if not base_url or not email or not token:
            raise ValueError(
                "jira-ticketing sync requires --fixture-dir, or "
                f"{JIRA_BASE_URL_ENV}/base_url plus {JIRA_EMAIL_ENV}/email and a read-only API token "
                "(JIRA_API_TOKEN or --token-env)"
            )
        netguard.assert_url_is_public(base_url, label="jira base url")
        client = JiraClient(base_url, email=email, token=token)
    return collect_jira_evidence(client)


def _collect_snowflake(
    *,
    fixture_dir: str | Path | None,
    token_env: str,
    env: dict[str, str],
    credentials: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    client: SnowflakeClient | SnowflakeFixtureClient
    credentials = credentials or {}
    options = options or {}
    account = str(credentials.get("account") or env.get(SNOWFLAKE_ACCOUNT_ENV) or "").strip() or None
    if fixture_dir:
        client = SnowflakeFixtureClient(fixture_dir, account=account or "fixture-snowflake")
    else:
        effective_credentials = {
            "account": account,
            "user": str(credentials.get("user") or env.get(SNOWFLAKE_USER_ENV) or "").strip(),
            "role": str(credentials.get("role") or env.get(SNOWFLAKE_ROLE_ENV) or "").strip(),
            "authenticator": str(
                credentials.get("authenticator") or env.get(SNOWFLAKE_AUTHENTICATOR_ENV) or ""
            ).strip(),
            "credential_ref": str(credentials.get("credential_ref") or "").strip(),
            "oauth_token_ref": str(credentials.get("oauth_token_ref") or "").strip(),
            "private_key_ref": str(credentials.get("private_key_ref") or "").strip(),
            "private_key_file_pwd_ref": str(credentials.get("private_key_file_pwd_ref") or "").strip(),
        }
        effective_options = {
            "warehouse": str(options.get("warehouse") or env.get(SNOWFLAKE_WAREHOUSE_ENV) or "").strip(),
            "database": str(options.get("database") or env.get(SNOWFLAKE_DATABASE_ENV) or "").strip(),
            "schema": str(options.get("schema") or env.get(SNOWFLAKE_SCHEMA_ENV) or "").strip(),
            "role": str(options.get("role") or env.get(SNOWFLAKE_ROLE_ENV) or "").strip(),
            "authenticator": str(options.get("authenticator") or env.get(SNOWFLAKE_AUTHENTICATOR_ENV) or "").strip(),
        }
        if token_env != DEFAULT_TOKEN_ENV and env.get(token_env):
            effective_credentials["credential_ref"] = token_env
        elif not effective_credentials["credential_ref"] and env.get(SNOWFLAKE_OAUTH_TOKEN_ENV):
            effective_credentials["credential_ref"] = SNOWFLAKE_OAUTH_TOKEN_ENV
        if not effective_credentials["private_key_ref"] and env.get(SNOWFLAKE_PRIVATE_KEY_FILE_ENV):
            effective_credentials["private_key_ref"] = SNOWFLAKE_PRIVATE_KEY_FILE_ENV
        if not effective_credentials["private_key_file_pwd_ref"] and env.get(SNOWFLAKE_PRIVATE_KEY_FILE_PWD_ENV):
            effective_credentials["private_key_file_pwd_ref"] = SNOWFLAKE_PRIVATE_KEY_FILE_PWD_ENV
        try:
            params = _probe_query_params(credentials=effective_credentials, options=effective_options, env=env)
        except ValueError as exc:
            raise ValueError(
                "snowflake-evidence-lake sync requires --fixture-dir, or "
                f"{SNOWFLAKE_ACCOUNT_ENV} plus {SNOWFLAKE_USER_ENV} with browser SSO "
                f"({SNOWFLAKE_AUTHENTICATOR_ENV}=externalbrowser), a Snowflake service-user key file "
                f"({SNOWFLAKE_PRIVATE_KEY_FILE_ENV}), or a read-only OAuth token "
                f"({SNOWFLAKE_OAUTH_TOKEN_ENV} or --token-env)"
            ) from exc
        views = {
            key: str(options.get(key) or env.get(f"SNOWFLAKE_VIEW_{key.upper()}") or default)
            for key, default in SNOWFLAKE_DEFAULT_VIEWS.items()
        }
        client = SnowflakeClient(query_params=params, views=views)
    return collect_snowflake_evidence(client, account=account)


# A connector whose evidence describes current state (IAM, config, inventory)
# is written as a per-run snapshot: the latest pull is the whole truth, so an
# entity removed at the source must disappear from the lake. Event-log evidence
# (audit/alert streams) is append-only: history is never overwritten.
SNAPSHOT_DATA_SHAPE = "current_state"


def _write_mode(connector_id: str) -> str:
    """Resolve the raw-write mode for ``connector_id`` from its catalog data shape.

    ``current_state`` → ``snapshot`` (replace this connector's prior rows so
    deletions propagate); anything else → ``append`` (the non-destructive default,
    used for event-log sources and any connector that does not declare a shape).
    """
    entry = load_connector_catalog().get(connector_id) or {}
    return "snapshot" if entry.get("data_shape") == SNAPSHOT_DATA_SHAPE else "append"


def _advance_watermark(lake: Path, connector_id: str, rows: list[dict[str, Any]], *, write_mode: str) -> str | None:
    """Advance an append connector's high-water cursor to the newest event time.

    Returns the cursor written (the max ``event_time`` across ``rows``), or
    ``None`` for a snapshot connector or a pull with no timestamped rows. The
    cursor is monotonic: an out-of-order or partial re-pull never moves it back,
    so the next sync resumes from the true high-water mark.
    """
    if write_mode != "append":
        return None
    cursors = [str(row.get("event_time")) for row in rows if row.get("event_time")]
    if not cursors:
        return read_watermark(lake, connector_id)
    cursor = max(cursors)
    prior = read_watermark(lake, connector_id)
    if prior is not None and cursor <= prior:
        return prior
    write_watermark(lake, connector_id, cursor)
    return cursor


def _dedupe_latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse a single pull to one row per event_id, last occurrence winning."""
    indexed = list(enumerate(rows))
    deduped = dedupe_by_key(indexed, key=lambda pair: str(pair[1]["event_id"]), recency=lambda pair: pair[0])
    return [row for _position, row in deduped]


def _upsert_raw_events(
    raw_path: Path,
    rows: list[dict[str, Any]],
    *,
    connector_id: str,
    write_mode: str,
) -> list[dict[str, Any]]:
    # Stamp ownership so a snapshot replace can scope to this connector's rows
    # without disturbing evidence collected by any other connector.
    for row in rows:
        row["connector_id"] = connector_id
    existing = read_jsonl(raw_path) if raw_path.exists() else []
    fresh = _dedupe_latest(rows)

    if write_mode == "snapshot":
        # Snapshot replace: drop this connector's prior rows (so entities deleted
        # at the source vanish) and any row this pull re-delivers; keep everyone
        # else's evidence untouched. This is what gives current-state connectors
        # deletion detection instead of an ever-growing union.
        incoming_ids = {str(row["event_id"]) for row in fresh}
        retained = [
            row
            for row in existing
            if row.get("connector_id") != connector_id and str(row.get("event_id")) not in incoming_ids
        ]
        merged = retained + fresh
    else:
        # Append (idempotent): dedup existing + incoming on event_id, last write
        # wins, so an overlapping re-pull never double-counts and history stays.
        indexed = list(enumerate(existing + fresh))
        deduped = dedupe_by_key(indexed, key=lambda pair: str(pair[1]["event_id"]), recency=lambda pair: pair[0])
        merged = [row for _position, row in deduped]

    errors = validate_raw_events(merged)
    if errors:
        raise ValueError("connector raw evidence validation failed:\n" + "\n".join(errors))
    write_jsonl(raw_path, merged)
    return merged


def _duration_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))
