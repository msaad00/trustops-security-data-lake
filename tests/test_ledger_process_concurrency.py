"""Independent server workers preserve ledger linkage and replay semantics."""

from __future__ import annotations

import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from security_lakehouse.assessment import verify_snapshot_chain
from security_lakehouse.tracking import list_events, verify_tracking_chain

_START = None


def _init_worker(barrier) -> None:
    global _START
    _START = barrier


def _write_from_process(lake: Path, kind: str, worker: int) -> list[str]:
    from security_lakehouse import assessment, ledger
    from security_lakehouse.tracking import append_event

    # Widen the read/append race window without changing the returned tip.
    # With serialization, only the lock holder can reach this delayed read.
    original = assessment._chain_tip if kind == "snapshot" else ledger.read_jsonl

    def delayed_read(*args, **kwargs):
        result = original(*args, **kwargs)
        time.sleep(0.03)
        return result

    module = assessment if kind == "snapshot" else ledger
    attribute = "_chain_tip" if kind == "snapshot" else "read_jsonl"
    results = []
    with patch.object(module, attribute, delayed_read):
        _START.wait(timeout=20)
        for index in range(4):
            if kind == "snapshot":
                result = assessment.write_assessment_snapshot(lake, reason=f"worker-{worker}-{index}")
                results.append(result.name)
            else:
                result = append_event(
                    lake,
                    violation_id=f"v-{worker}-{index}",
                    actor=f"worker-{worker}",
                    state="triaged",
                    idempotency_key="shared-retry" if kind == "replay" else None,
                )
                results.append(result["tracking_id"])
    return results


@pytest.mark.parametrize("kind", ["triage", "snapshot", "replay"])
def test_spawned_workers_preserve_chain_and_idempotency(tmp_path: Path, kind: str) -> None:
    if kind == "snapshot":
        from test_api_v1 import _seed_lake

        _seed_lake(tmp_path)
    context = multiprocessing.get_context("spawn")
    workers = 4
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
        initializer=_init_worker,
        initargs=(context.Barrier(workers),),
    ) as executor:
        futures = [executor.submit(_write_from_process, tmp_path, kind, worker) for worker in range(workers)]
        results = [identifier for future in futures for identifier in future.result(timeout=45)]

    expected = 1 if kind == "replay" else workers * 4
    verification = verify_snapshot_chain(tmp_path) if kind == "snapshot" else verify_tracking_chain(tmp_path)
    assert verification["ok"], verification["issues"]
    assert verification["length"] == expected
    assert len(set(results)) == expected
    if kind == "snapshot":
        assert len(list((tmp_path / "gold" / "snapshots").glob("*.json"))) == expected
    else:
        assert len(list_events(tmp_path)) == expected
