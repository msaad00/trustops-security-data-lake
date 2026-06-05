"""Ingestion strategy: velocity → method decision table + cost guard."""

from __future__ import annotations

from security_lakehouse.cli import main
from security_lakehouse.ingestion.strategy import (
    METHOD_CUSTOM_PULL,
    METHOD_NATIVE,
    METHOD_SCHEDULED,
    METHOD_STREAMING,
    freshness_slo_label,
    plan_catalog,
    resolve_method,
)


def test_resolve_method_decision_table() -> None:
    assert resolve_method("high_event_stream", False) == METHOD_STREAMING
    assert resolve_method("high_event_stream", True) == METHOD_STREAMING
    assert resolve_method("medium_api", True) == METHOD_NATIVE
    assert resolve_method("medium_api", False) == METHOD_CUSTOM_PULL
    assert resolve_method("low_current_state", True) == METHOD_SCHEDULED
    assert resolve_method("low_current_state", False) == METHOD_SCHEDULED


def test_streaming_only_reachable_from_high_event_stream() -> None:
    # The cost guard: streaming is the *only* high-velocity path and is never
    # reached from medium/low velocity, regardless of native_connector.
    for velocity in ("medium_api", "low_current_state", "unknown"):
        for native in (True, False):
            assert resolve_method(velocity, native) != METHOD_STREAMING


def test_freshness_slo_label() -> None:
    assert freshness_slo_label(0.5) == "30s"
    assert freshness_slo_label(15) == "15m"
    assert freshness_slo_label(60) == "1h"
    assert freshness_slo_label(120) == "2h"
    assert freshness_slo_label(90) == "1.5h"


def test_plan_catalog_covers_every_connector_with_a_cost_note() -> None:
    plans = plan_catalog()
    assert len(plans) >= 15
    for p in plans:
        assert p.method in {METHOD_STREAMING, METHOD_NATIVE, METHOD_CUSTOM_PULL, METHOD_SCHEDULED}
        assert p.cost_note  # every plan carries a one-line why
        # streaming must be backed by a declared high-velocity source
        if p.method == METHOD_STREAMING:
            assert p.velocity == "high_event_stream"


def test_cli_ingestion_plan_prints_method(capsys) -> None:
    rc = main(["ingestion", "plan"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Snowpipe Streaming" in out
    assert "clickhouse-telemetry-lake" in out


def test_cli_ingestion_plan_json(capsys) -> None:
    import json

    rc = main(["ingestion", "plan", "--json"])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert any(r["connector_id"] == "clickhouse-telemetry-lake" for r in rows)
    assert all("cost_note" in r and "method" in r for r in rows)
