"""Connector sync runner.

This module turns catalog entries from static access contracts into executable
evidence collection runs. The first concrete runner is intentionally narrow:
``github-security`` delegates to the authenticated repository governance
collector and writes raw evidence into the lake's managed raw-event file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_lakehouse.connector_state import append_run_event, has_adapter, latest_config
from security_lakehouse.connectors import load_connector_catalog
from security_lakehouse.io import read_jsonl, write_jsonl
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.repo_governance import sync_repo_governance
from security_lakehouse.validation import validate_raw_events

CONNECTOR_RAW_FILE = "raw/connector_events.jsonl"


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


def _collect(
    connector_id: str,
    *,
    repo: str | None,
    fixture_dir: str | Path | None,
    token_env: str,
) -> list[dict[str, Any]]:
    if not has_adapter(connector_id):
        raise ValueError(f"no sync runner registered for connector_id {connector_id!r}")
    if not repo:
        raise ValueError("github-security sync requires --repo")
    return sync_repo_governance(repo, fixture_dir=fixture_dir, token_env=token_env)


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
