"""Connector sync runner.

This module turns catalog entries from static access contracts into executable
evidence collection runs. The first concrete runner is intentionally narrow:
``github-security`` delegates to the authenticated repository governance
collector and writes raw evidence into the lake's managed raw-event file.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_lakehouse.connector_state import append_run_event, latest_config
from security_lakehouse.connectors import load_connector_catalog
from security_lakehouse.connectors_aws import (
    AWSClient,
    AWSFixtureClient,
    collect_aws_evidence,
)
from security_lakehouse.connectors_okta import (
    OktaClient,
    OktaFixtureClient,
    collect_okta_evidence,
)
from security_lakehouse.io import read_jsonl, write_jsonl
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.repo_governance import sync_repo_governance
from security_lakehouse.validation import validate_raw_events

CONNECTOR_RAW_FILE = "raw/connector_events.jsonl"

# Environment variable carrying the Okta org base URL for live collection. The
# token is read from ``token_env`` (defaults to OKTA_API_TOKEN for this runner).
OKTA_ORG_URL_ENV = "OKTA_ORG_URL"

# Environment variables carrying the AWS account id + region for live
# collection. Credentials resolve through boto3's standard provider chain
# (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN / profiles).
AWS_ACCOUNT_ID_ENV = "AWS_ACCOUNT_ID"
AWS_REGION_ENV = "AWS_REGION"


@dataclass(frozen=True)
class ConnectorSyncResult:
    """Result returned by a connector sync run."""

    connector_id: str
    result: str
    raw_path: str
    evidence_count: int
    materialized: bool
    run: dict[str, Any]


def run_connector_sync(
    lake_dir: str | Path,
    *,
    connector_id: str,
    actor: str = "system",
    repo: str | None = None,
    fixture_dir: str | Path | None = None,
    token_env: str = "GITHUB_TOKEN",
    materialize: bool = True,
) -> ConnectorSyncResult:
    """Run one configured connector and persist its evidence + run event."""
    lake = Path(lake_dir)
    start = time.perf_counter()
    try:
        _require_enabled(lake, connector_id)
        rows = _collect(connector_id, repo=repo, fixture_dir=fixture_dir, token_env=token_env)
        raw_path = lake / CONNECTOR_RAW_FILE
        _upsert_raw_events(raw_path, rows)
        if materialize:
            run_pipeline(raw_path, lake)
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
        )
    except Exception as exc:
        run = append_run_event(
            lake,
            connector_id=connector_id,
            kind="sync",
            result="error",
            actor=actor,
            duration_ms=_duration_ms(start),
            error=str(exc),
        )
        raise ConnectorSyncError(str(exc), run=run) from exc


class ConnectorSyncError(RuntimeError):
    """Raised when a connector sync fails after recording a run event."""

    def __init__(self, message: str, *, run: dict[str, Any]) -> None:
        super().__init__(message)
        self.run = run


def _require_enabled(lake: Path, connector_id: str) -> None:
    catalog = load_connector_catalog()
    if connector_id not in catalog:
        raise ValueError(f"unknown connector_id {connector_id!r}")
    config = latest_config(lake, connector_id)
    if not config or config.get("state") != "enabled":
        raise ValueError("connector is not enabled; configure it before sync")


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
# ``connector_state.IMPLEMENTED_ADAPTERS`` derives its id set from this
# registry's keys, so registering here is the single source of truth for which
# connectors report a real adapter to the probe/console.
# ---------------------------------------------------------------------------


def _build_github(inputs: SyncInputs) -> list[dict[str, Any]]:
    if not inputs.repo:
        raise ValueError("github-security sync requires --repo")
    return sync_repo_governance(inputs.repo, fixture_dir=inputs.fixture_dir, token_env=inputs.token_env)


def _build_okta(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_okta(fixture_dir=inputs.fixture_dir, token_env=inputs.token_env, env=inputs.env)


def _build_aws(inputs: SyncInputs) -> list[dict[str, Any]]:
    return _collect_aws(fixture_dir=inputs.fixture_dir, env=inputs.env)


REGISTRY: dict[str, ConnectorBuilder] = {
    "github-security": _build_github,
    "okta-identity": _build_okta,
    "aws-posture": _build_aws,
}


def registered_connector_ids() -> frozenset[str]:
    """The set of connector_ids with a sync builder registered in REGISTRY.

    This is the single source of truth for "has a real collection adapter" and
    is consumed by ``connector_state.IMPLEMENTED_ADAPTERS`` / ``has_adapter``.
    """
    return frozenset(REGISTRY)


def _collect(
    connector_id: str,
    *,
    repo: str | None,
    fixture_dir: str | Path | None,
    token_env: str,
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
        )
    )


def _collect_okta(
    *,
    fixture_dir: str | Path | None,
    token_env: str,
    env: dict[str, str],
) -> list[dict[str, Any]]:
    client: OktaClient | OktaFixtureClient
    if fixture_dir:
        client = OktaFixtureClient(fixture_dir)
    else:
        org_url = env.get(OKTA_ORG_URL_ENV)
        # The CLI default token_env is GITHUB_TOKEN; fall back to the Okta var
        # when the caller did not override it for this connector.
        token = env.get(token_env) or env.get("OKTA_API_TOKEN")
        if not org_url or not token:
            raise ValueError(
                "okta-identity sync requires --fixture-dir, or "
                f"{OKTA_ORG_URL_ENV} plus a read-only API token (OKTA_API_TOKEN or --token-env)"
            )
        client = OktaClient(org_url, token=token)
    return collect_okta_evidence(client)


def _collect_aws(
    *,
    fixture_dir: str | Path | None,
    env: dict[str, str],
) -> list[dict[str, Any]]:
    if fixture_dir:
        fixture_account = env.get(AWS_ACCOUNT_ID_ENV) or "000000000000"
        return collect_aws_evidence(AWSFixtureClient(fixture_dir), account_id=fixture_account)
    account_id = env.get(AWS_ACCOUNT_ID_ENV)
    if not account_id:
        raise ValueError(
            "aws-posture sync requires --fixture-dir, or "
            f"{AWS_ACCOUNT_ID_ENV} plus read-only AWS credentials "
            "(AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY via the standard provider chain)"
        )
    client = AWSClient(region_name=env.get(AWS_REGION_ENV))
    return collect_aws_evidence(client, account_id=account_id)


def _upsert_raw_events(raw_path: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = read_jsonl(raw_path) if raw_path.exists() else []
    by_id: dict[str, dict[str, Any]] = {str(row["event_id"]): row for row in existing}
    order = [str(row["event_id"]) for row in existing]
    for row in rows:
        event_id = str(row["event_id"])
        if event_id not in by_id:
            order.append(event_id)
        by_id[event_id] = row
    merged = [by_id[event_id] for event_id in order]
    errors = validate_raw_events(merged)
    if errors:
        raise ValueError("connector raw evidence validation failed:\n" + "\n".join(errors))
    write_jsonl(raw_path, merged)
    return merged


def _duration_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))
