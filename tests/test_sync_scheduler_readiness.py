"""Framework sync + workflow scheduler + staged readiness gate tests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from security_lakehouse.connector_state import append_config_event, latest_run
from security_lakehouse.framework_sync import sync_frameworks
from security_lakehouse.readiness import STAGES, build_readiness_view
from security_lakehouse.scheduler import (
    parse_schedule,
    run_forever,
    tick,
)
from security_lakehouse.workflows import save_workflow

# --- framework_sync -----------------------------------------------------------


def _fixture_registry(tmp_path: Path, with_sha: str | None = None) -> Path:
    payload = {
        "frameworks": [
            {
                "framework_id": "demo",
                "name": "Demo",
                "version": "1.0",
                "official_source_url": "https://example.com/demo",
                "official_source_name": "Demo Source",
                "implementation_status": "implemented",
                "effective_date": "2026-01-01",
                "superseded_by": None,
                "pulled_at": None,
                "source_sha256": with_sha,
                "copyright_guardrail": "test",
                "sync_cadence_days": 30,
            }
        ]
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_sync_skips_when_network_disabled(tmp_path: Path) -> None:
    path = _fixture_registry(tmp_path)
    results = sync_frameworks(path)
    assert len(results) == 1
    assert results[0].state == "skipped"
    assert "network disabled" in (results[0].reason or "")


def test_sync_updates_registry_with_fetcher(tmp_path: Path) -> None:
    path = _fixture_registry(tmp_path)
    body = b"<official text>"
    expected_sha = hashlib.sha256(body).hexdigest()
    results = sync_frameworks(path, fetcher=lambda _url: body)
    assert results[0].state == "updated"
    assert results[0].new_sha == expected_sha
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["frameworks"][0]["source_sha256"] == expected_sha
    assert updated["frameworks"][0]["pulled_at"]


def test_sync_unchanged_when_sha_matches(tmp_path: Path) -> None:
    body = b"<official text>"
    sha = hashlib.sha256(body).hexdigest()
    path = _fixture_registry(tmp_path, with_sha=sha)
    results = sync_frameworks(path, fetcher=lambda _url: body)
    assert results[0].state == "unchanged"


def test_sync_fetcher_error_marks_framework_error(tmp_path: Path) -> None:
    path = _fixture_registry(tmp_path)

    def boom(_url: str) -> bytes:
        raise OSError("connection refused")

    results = sync_frameworks(path, fetcher=boom)
    assert results[0].state == "error"
    assert "connection refused" in (results[0].reason or "")


# --- scheduler -----------------------------------------------------------------


@pytest.mark.parametrize(
    "expression,expected_minutes",
    [
        ("@hourly", 60),
        ("@daily", 60 * 24),
        ("every 5m", 5),
        ("every 2h", 120),
    ],
)
def test_parse_schedule(expression: str, expected_minutes: int) -> None:
    period = parse_schedule(expression)
    assert period is not None
    assert period.total_seconds() == expected_minutes * 60


def test_parse_schedule_rejects_bad_input() -> None:
    assert parse_schedule("") is None
    assert parse_schedule("@yearly") is None
    assert parse_schedule("every 0m") is None
    assert parse_schedule("every banana") is None


def _save_cron_workflow(lake: Path, schedule: str) -> str:
    workflow = save_workflow(
        lake,
        workflow_id=None,
        name="auto-cron",
        description="",
        nodes=[
            {"id": "n1", "node_type": "trigger.cron", "params": {"schedule": schedule}},
            {"id": "n2", "node_type": "trigger.cron", "params": {"schedule": schedule}},
        ],
        edges=[],
    )
    return workflow["workflow_id"]


def test_scheduler_fires_due_workflow_once(tmp_path: Path) -> None:
    workflow_id = _save_cron_workflow(tmp_path, "every 5m")
    fired: list[dict] = []

    def runner(_lake, *, workflow_id: str, actor: str) -> dict:
        record = {"workflow_id": workflow_id, "actor": actor, "result": "ok"}
        fired.append(record)
        return record

    # First tick — last_fired is None so it fires immediately
    first = tick(tmp_path, runner=runner)
    assert len(first) == 1
    assert first[0]["workflow_id"] == workflow_id

    # Second tick at the same moment — not due yet
    second = tick(tmp_path, runner=runner)
    assert second == []
    assert len(fired) == 1


def test_scheduler_skips_workflows_without_cron(tmp_path: Path) -> None:
    save_workflow(
        tmp_path,
        workflow_id=None,
        name="manual",
        description="",
        nodes=[
            {"id": "n1", "node_type": "check.evidence_exists", "params": {"control_id": "x"}},
        ],
        edges=[],
    )
    assert tick(tmp_path, runner=lambda *_a, **_k: {"result": "ok"}) == []


def test_scheduler_records_error_when_runner_raises(tmp_path: Path) -> None:
    _save_cron_workflow(tmp_path, "every 5m")

    def boom(*_a, **_k) -> dict:
        raise RuntimeError("simulated failure")

    result = tick(tmp_path, runner=boom)
    assert len(result) == 1
    assert result[0]["result"] == "error"
    assert result[0]["error"] == "internal error"


def test_run_forever_obeys_iteration_cap(tmp_path: Path) -> None:
    ticks = run_forever(tmp_path, tick_seconds=1, iterations=3, sleeper=lambda _s: None)
    assert ticks == 3


def test_scheduler_respects_period_with_synthetic_now(tmp_path: Path) -> None:
    workflow_id = _save_cron_workflow(tmp_path, "every 5m")
    base = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
    captured: list[dict] = []

    def runner(_lake, *, workflow_id: str, actor: str) -> dict:
        rec = {"workflow_id": workflow_id, "actor": actor, "result": "ok"}
        captured.append(rec)
        return rec

    # t0: fires
    tick(tmp_path, now=base, runner=runner)
    # t0 + 2min: not yet due (period is 5min)
    tick(tmp_path, now=base + timedelta(minutes=2), runner=runner)
    # t0 + 6min: due again
    tick(tmp_path, now=base + timedelta(minutes=6), runner=runner)
    assert len(captured) == 2
    assert all(c["workflow_id"] == workflow_id for c in captured)


def test_scheduler_fires_due_connector_sync_once(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        options={
            "sync_schedule": "every 5m",
            "repo": "acme/model-service",
            "fixture_dir": str(Path(__file__).parent / "fixtures" / "github-governance"),
            "materialize": False,
        },
    )
    fired: list[dict] = []

    def connector_runner(_lake, **kwargs) -> dict:
        fired.append(kwargs)
        return {"result": "ok", "evidence_count": 5}

    base = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
    first = tick(tmp_path, now=base, connector_runner=connector_runner)
    second = tick(tmp_path, now=base + timedelta(minutes=2), connector_runner=connector_runner)
    third = tick(tmp_path, now=base + timedelta(minutes=6), connector_runner=connector_runner)

    assert [row["target_kind"] for row in first] == ["connector", "lake_eval"]
    assert first[0]["connector_id"] == "github-security"
    assert first[0]["evidence_count"] == 5
    assert second == []
    assert len(third) == 1
    assert third[0]["target_kind"] == "connector"
    assert len(fired) == 2
    assert fired[0]["actor"] == "scheduler"
    assert fired[0]["repo"] == "acme/model-service"
    assert fired[0]["materialize"] is False


def test_scheduler_connector_sync_runs_real_github_fixture(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        options={
            "sync_schedule": "every 5m",
            "repo": "acme/model-service",
            "fixture_dir": str(Path(__file__).parent / "fixtures" / "github-governance"),
            "materialize": False,
        },
    )

    result = tick(tmp_path)

    assert len(result) == 2
    assert result[0]["target_kind"] == "connector"
    assert result[0]["connector_id"] == "github-security"
    assert result[0]["result"] == "ok"
    assert result[0]["evidence_count"] == 5
    assert latest_run(tmp_path, "github-security", kind="sync")["result"] == "ok"


def test_scheduler_records_connector_error_without_advancing_state(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="enabled",
        actor="alice",
        options={"sync_schedule": "every 5m", "repo": "acme/model-service"},
    )

    def boom(_lake, **_kwargs) -> dict:
        raise RuntimeError("token denied")

    base = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
    first = tick(tmp_path, now=base, connector_runner=boom)
    second = tick(tmp_path, now=base + timedelta(minutes=1), connector_runner=boom)

    assert first[0]["target_kind"] == "connector"
    assert first[0]["result"] == "error"
    assert first[0]["error"] == "internal error"
    assert second[0]["result"] == "error"


# --- readiness -----------------------------------------------------------------


def test_readiness_view_has_one_row_per_framework() -> None:
    view = build_readiness_view()
    assert len(view) >= 2
    for row in view:
        assert row["stage"] in STAGES
        assert isinstance(row["gates"], dict)
        assert set(row["gates"]) == set(STAGES)


def test_readiness_blocks_on_missing_source_pulled() -> None:
    # The shipped registry has source_sha256=null, so every framework should
    # report source_pulled=False as the earliest unmet gate.
    view = build_readiness_view()
    for row in view:
        assert row["gates"]["source_pulled"] is False
        assert row["stage"] == "source_pulled"
        assert row["is_ready"] is False
