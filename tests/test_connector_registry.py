"""Connector sync registry tests.

The registry in ``connector_runner.REGISTRY`` is the single dispatch table for
connector sync collection, and the single source of truth for which connectors
report a real adapter. These tests pin that contract: the registry holds exactly
the three real adapters, ``has_adapter`` agrees with the registry, an unknown
connector still raises the documented ValueError, and a fixture sync for each
real connector still flows through the registry path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse import connector_state
from security_lakehouse.connector_runner import (
    CONNECTOR_RAW_FILE,
    REGISTRY,
    ConnectorSyncError,
    registered_connector_ids,
    run_connector_sync,
)
from security_lakehouse.connector_state import (
    append_config_event,
    has_adapter,
    latest_run,
)
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

REAL_ADAPTERS = {"github-security", "okta-identity", "aws-posture"}
FIXTURES = Path(__file__).parent / "fixtures"


def test_registry_contains_exactly_the_three_real_adapters() -> None:
    assert set(REGISTRY) == REAL_ADAPTERS
    assert registered_connector_ids() == frozenset(REAL_ADAPTERS)


def test_implemented_adapters_derives_from_registry() -> None:
    # IMPLEMENTED_ADAPTERS is no longer a hardcoded frozenset; it must mirror
    # the registry keys exactly (single source of truth).
    assert registered_connector_ids() == connector_state.IMPLEMENTED_ADAPTERS
    assert frozenset(REAL_ADAPTERS) == connector_state.IMPLEMENTED_ADAPTERS


def test_has_adapter_agrees_with_registry() -> None:
    for connector_id in REAL_ADAPTERS:
        assert has_adapter(connector_id) is True
    # A catalog connector without a registered builder is contract-only.
    assert has_adapter("snowflake-evidence-lake") is False
    assert has_adapter("not-a-real-connector") is False


def test_unknown_connector_id_raises_no_runner_registered(tmp_path: Path) -> None:
    # An enabled connector that the catalog knows but the registry does not must
    # still raise the exact "no sync runner registered" message via the runner.
    append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    with pytest.raises(ConnectorSyncError, match="no sync runner registered") as exc:
        run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake")
    assert exc.value.run["result"] == "error"


@pytest.mark.parametrize(
    ("connector_id", "fixture", "extra"),
    [
        ("github-security", "github-governance", {"repo": "acme/model-service"}),
        ("okta-identity", "okta", {}),
        ("aws-posture", "aws", {}),
    ],
)
def test_fixture_sync_flows_through_registry(
    tmp_path: Path,
    connector_id: str,
    fixture: str,
    extra: dict[str, str],
) -> None:
    append_config_event(tmp_path, connector_id=connector_id, state="enabled", actor="alice")
    result = run_connector_sync(
        tmp_path,
        connector_id=connector_id,
        fixture_dir=FIXTURES / fixture,
        **extra,
    )
    assert result.result == "ok"
    assert result.evidence_count > 0
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == result.evidence_count

    run = latest_run(tmp_path, connector_id, kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == result.evidence_count
