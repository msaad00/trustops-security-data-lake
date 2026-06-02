"""Advisory-lock contention tests for the cron scheduler.

The scheduler docstring promises each due target fires *exactly once*. Two
concurrent ticks (cron overlap, ``concurrencyPolicy: Allow``, daemon plus a
manual API tick) must not both observe the same ``last_fired`` and double-fire.
These tests cover the non-blocking ``fcntl.flock`` guard around the
read-state -> fire -> write-state critical section.
"""

from __future__ import annotations

import fcntl
from pathlib import Path

from security_lakehouse.scheduler import _lock_path, tick
from security_lakehouse.workflows import save_workflow


def _save_cron_workflow(lake: Path, schedule: str) -> str:
    workflow = save_workflow(
        lake,
        workflow_id=None,
        name="auto-cron",
        description="",
        nodes=[{"id": "n1", "node_type": "trigger.cron", "params": {"schedule": schedule}}],
        edges=[],
    )
    return workflow["workflow_id"]


def test_single_tick_fires_due_target_normally(tmp_path: Path) -> None:
    workflow_id = _save_cron_workflow(tmp_path, "every 5m")
    fired: list[dict] = []

    def runner(_lake, *, workflow_id: str, actor: str) -> dict:
        record = {"workflow_id": workflow_id, "actor": actor, "result": "ok"}
        fired.append(record)
        return record

    result = tick(tmp_path, runner=runner)

    assert len(result) == 1
    assert result[0]["workflow_id"] == workflow_id
    assert result[0].get("skipped_locked") is not True
    assert len(fired) == 1


def test_contended_tick_skips_without_firing_or_mutating_state(tmp_path: Path) -> None:
    workflow_id = _save_cron_workflow(tmp_path, "every 5m")
    fired: list[dict] = []

    def runner(_lake, *, workflow_id: str, actor: str) -> dict:
        record = {"workflow_id": workflow_id, "actor": actor, "result": "ok"}
        fired.append(record)
        return record

    state_path = tmp_path / "gold" / "scheduler_state.jsonl"
    lock_path = _lock_path(tmp_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Simulate a concurrent tick that already holds the exclusive lock.
    with lock_path.open("w", encoding="utf-8") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)

        result = tick(tmp_path, runner=runner)

        assert result == [{"target_kind": None, "skipped_locked": True, "fired": []}]
        assert fired == []  # did not fire while the lock was held
        assert not state_path.exists()  # did not mutate persisted state

        fcntl.flock(held.fileno(), fcntl.LOCK_UN)

    # After the lock is released, a tick fires the still-due target normally.
    result = tick(tmp_path, runner=runner)
    assert len(result) == 1
    assert result[0]["workflow_id"] == workflow_id
    assert result[0].get("skipped_locked") is not True
    assert len(fired) == 1
    assert state_path.exists()
