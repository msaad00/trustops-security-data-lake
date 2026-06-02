"""Cron scheduler for workflows and connector syncs.

A workflow whose triggers include ``trigger.cron`` (with a ``schedule`` param)
becomes eligible for periodic execution. The scheduler ticks once per call,
fires every due workflow exactly once, and persists the last-fired timestamp
to ``gold/scheduler_state.jsonl`` so successive ticks don't double-fire.

An enabled connector becomes eligible for periodic sync when its connector
configuration options include ``sync_schedule``. The scheduler calls the same
connector runner used by the CLI, so scheduled evidence collection and manual
syncs share validation, run history, and raw-event materialization.

Two execution surfaces:
  * ``security-lakehouse scheduler tick --lake build/lakehouse`` runs the
    tick once and exits (intended for system cron / k8s CronJob).
  * ``security-lakehouse scheduler run --lake build/lakehouse`` runs a
    long-lived daemon ticking every N seconds.

Schedule grammar (intentionally small):
  * ``@hourly``       — every hour on the hour
  * ``@daily``        — every day at 00:00 UTC
  * ``every Nm``      — every N minutes (1..59)
  * ``every Nh``      — every N hours (1..23)

This keeps the in-process scheduler portable; production deployments that
need full crontab grammar should call ``scheduler tick`` from a real cron.
"""

from __future__ import annotations

import fcntl
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from security_lakehouse.connector_runner import run_connector_sync
from security_lakehouse.connector_state import build_catalog_view
from security_lakehouse.workflows import list_workflows, run_workflow

STATE_FILE = "scheduler_state.jsonl"
LOCK_FILE = ".scheduler.lock"
DEFAULT_TICK_SECONDS = 60

_INTERVAL_RE = re.compile(r"^every\s+(\d+)\s*(m|h)$", re.IGNORECASE)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def parse_schedule(schedule: str) -> timedelta | None:
    """Return the period for a schedule expression, or None if unrecognised."""
    if not schedule:
        return None
    text = schedule.strip().lower()
    if text == "@hourly":
        return timedelta(hours=1)
    if text == "@daily":
        return timedelta(days=1)
    match = _INTERVAL_RE.match(text)
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if value <= 0:
        return None
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    return None


@dataclass(frozen=True)
class ScheduledWorkflow:
    workflow_id: str
    schedule: str
    period: timedelta


@dataclass(frozen=True)
class ScheduledConnector:
    connector_id: str
    schedule: str
    period: timedelta
    repo: str | None
    fixture_dir: str | None
    token_env: str
    materialize: bool


def _scheduled_from_workflows(workflows: list[dict[str, Any]]) -> list[ScheduledWorkflow]:
    out: list[ScheduledWorkflow] = []
    for workflow in workflows:
        for node in workflow.get("nodes", []) or []:
            if str(node.get("node_type") or "") != "trigger.cron":
                continue
            schedule = str((node.get("params") or {}).get("schedule") or "")
            period = parse_schedule(schedule)
            if period is None:
                continue
            out.append(
                ScheduledWorkflow(
                    workflow_id=str(workflow.get("workflow_id") or ""),
                    schedule=schedule,
                    period=period,
                )
            )
            break  # one trigger.cron per workflow is enough
    return out


def _scheduled_from_connectors(lake_dir: str | Path) -> list[ScheduledConnector]:
    out: list[ScheduledConnector] = []
    for connector in build_catalog_view(lake_dir):
        if connector.get("state") != "enabled":
            continue
        options = connector.get("configured_options") or {}
        schedule = str(options.get("sync_schedule") or options.get("schedule") or "")
        period = parse_schedule(schedule)
        if period is None:
            continue
        out.append(
            ScheduledConnector(
                connector_id=str(connector.get("connector_id") or ""),
                schedule=schedule,
                period=period,
                repo=options.get("repo"),
                fixture_dir=options.get("fixture_dir"),
                token_env=str(options.get("token_env") or "GITHUB_TOKEN"),
                materialize=bool(options.get("materialize", True)),
            )
        )
    return out


def _state_key(target_kind: str, target_id: str) -> str:
    return f"{target_kind}:{target_id}"


def _read_state(lake_dir: str | Path) -> dict[str, datetime]:
    path = _gold(lake_dir) / STATE_FILE
    if not path.is_file():
        return {}
    latest: dict[str, datetime] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        target_kind = str(row.get("target_kind") or "workflow")
        target_id = str(row.get("target_id") or row.get("workflow_id") or "")
        last = row.get("last_fired_at")
        if not target_id or not last:
            continue
        try:
            parsed = datetime.fromisoformat(str(last).replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            continue
        key = _state_key(target_kind, target_id)
        existing = latest.get(key)
        if existing is None or parsed > existing:
            latest[key] = parsed
    return latest


def _write_state(lake_dir: str | Path, *, target_kind: str, target_id: str, fired_at: datetime) -> None:
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    record = {
        "target_kind": target_kind,
        "target_id": target_id,
        "last_fired_at": _utc_iso(fired_at),
    }
    if target_kind == "workflow":
        record["workflow_id"] = target_id
    if target_kind == "connector":
        record["connector_id"] = target_id
    with (gold / STATE_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def _lock_path(lake_dir: str | Path) -> Path:
    return _gold(lake_dir) / LOCK_FILE


def tick(
    lake_dir: str | Path,
    *,
    now: datetime | None = None,
    runner: Any | None = None,
    connector_runner: Any | None = None,
) -> list[dict[str, Any]]:
    """Fire every due workflow and connector once.

    Returns one record per attempted run. ``runner`` remains the workflow
    runner override used by tests; ``connector_runner`` is the equivalent
    override for scheduled connector syncs.

    The read-state -> fire -> write-state critical section is guarded by a
    non-blocking advisory file lock (``gold/.scheduler.lock``) so two
    concurrent ticks (cron overlap, ``concurrencyPolicy: Allow``, daemon plus
    a manual API tick) cannot both observe the same ``last_fired`` and
    double-fire. A tick that cannot acquire the lock is a no-op and returns a
    single ``{"skipped_locked": True}`` record instead of firing.
    """
    lock_path = _lock_path(lake_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = lock_path.open("w", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return [{"target_kind": None, "skipped_locked": True, "fired": []}]
        try:
            return _tick_locked(
                lake_dir,
                now=now,
                runner=runner,
                connector_runner=connector_runner,
            )
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
    finally:
        lock_fd.close()


def _tick_locked(
    lake_dir: str | Path,
    *,
    now: datetime | None = None,
    runner: Any | None = None,
    connector_runner: Any | None = None,
) -> list[dict[str, Any]]:
    moment = (now or _utc_now()).astimezone(UTC)
    scheduled = _scheduled_from_workflows(list_workflows(lake_dir))
    state = _read_state(lake_dir)
    results: list[dict[str, Any]] = []
    for entry in scheduled:
        last_fired = state.get(_state_key("workflow", entry.workflow_id))
        due_at = (last_fired + entry.period) if last_fired else moment
        if last_fired is not None and moment < due_at:
            continue
        try:
            run = (runner or run_workflow)(lake_dir, workflow_id=entry.workflow_id, actor="scheduler")
            outcome = run.get("result") if isinstance(run, dict) else "ok"
            _write_state(lake_dir, target_kind="workflow", target_id=entry.workflow_id, fired_at=moment)
            results.append(
                {
                    "target_kind": "workflow",
                    "workflow_id": entry.workflow_id,
                    "schedule": entry.schedule,
                    "fired_at": _utc_iso(moment),
                    "result": outcome,
                    "error": None,
                }
            )
        except Exception:  # noqa: BLE001 - scheduler results must not expose exception details
            results.append(
                {
                    "target_kind": "workflow",
                    "workflow_id": entry.workflow_id,
                    "schedule": entry.schedule,
                    "fired_at": _utc_iso(moment),
                    "result": "error",
                    "error": "internal error",
                }
            )
    sync_runner = connector_runner or run_connector_sync
    for entry in _scheduled_from_connectors(lake_dir):
        last_fired = state.get(_state_key("connector", entry.connector_id))
        due_at = (last_fired + entry.period) if last_fired else moment
        if last_fired is not None and moment < due_at:
            continue
        try:
            run = sync_runner(
                lake_dir,
                connector_id=entry.connector_id,
                actor="scheduler",
                repo=entry.repo,
                fixture_dir=entry.fixture_dir,
                token_env=entry.token_env,
                materialize=entry.materialize,
            )
            outcome = getattr(run, "result", None) or (run.get("result") if isinstance(run, dict) else "ok")
            evidence_count = getattr(run, "evidence_count", None)
            if evidence_count is None and isinstance(run, dict):
                evidence_count = run.get("evidence_count")
            _write_state(lake_dir, target_kind="connector", target_id=entry.connector_id, fired_at=moment)
            results.append(
                {
                    "target_kind": "connector",
                    "connector_id": entry.connector_id,
                    "schedule": entry.schedule,
                    "fired_at": _utc_iso(moment),
                    "result": outcome,
                    "evidence_count": evidence_count,
                    "error": None,
                }
            )
        except Exception:  # noqa: BLE001 - scheduler results must not expose exception details
            results.append(
                {
                    "target_kind": "connector",
                    "connector_id": entry.connector_id,
                    "schedule": entry.schedule,
                    "fired_at": _utc_iso(moment),
                    "result": "error",
                    "evidence_count": None,
                    "error": "internal error",
                }
            )
    return results


def run_forever(
    lake_dir: str | Path,
    *,
    tick_seconds: int = DEFAULT_TICK_SECONDS,
    iterations: int | None = None,
    sleeper: Any | None = None,
) -> int:
    """Daemon loop. ``iterations`` caps the loop for tests."""
    count = 0
    sleep = sleeper or time.sleep
    while iterations is None or count < iterations:
        tick(lake_dir)
        sleep(tick_seconds)
        count += 1
    return count
