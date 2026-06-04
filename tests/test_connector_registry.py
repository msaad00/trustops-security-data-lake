"""Connector sync registry tests.

The registry in ``connector_runner.REGISTRY`` is the single dispatch table for
connector sync collection, and the single source of truth for which connectors
report a real adapter. These tests pin that contract: the registry holds exactly
the real adapters, ``has_adapter`` agrees with the registry, an unknown
connector still raises the documented ValueError, and a fixture sync for each
real connector still flows through the registry path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse import connector_runner, connector_state
from security_lakehouse.connectors import load_connector_catalog
from security_lakehouse.io import read_jsonl
from security_lakehouse.validation import validate_raw_events

REAL_ADAPTERS = {"github-security", "okta-identity", "aws-posture", "jira-ticketing"}
FIXTURES = Path(__file__).parent / "fixtures"


def test_registry_contains_exactly_the_real_adapters() -> None:
    assert set(connector_runner.REGISTRY) == REAL_ADAPTERS
    assert connector_runner.registered_connector_ids() == frozenset(REAL_ADAPTERS)


def test_implemented_adapters_catalog_flags_agree_with_registry() -> None:
    # connector_state deliberately avoids importing connector_runner to prevent
    # an import cycle; this pins the catalog metadata to the runner registry.
    catalog = load_connector_catalog()
    implemented_from_catalog = {
        connector_id for connector_id, definition in catalog.items() if definition.get("is_implemented")
    }
    assert connector_runner.registered_connector_ids() == frozenset(implemented_from_catalog)
    assert frozenset(REAL_ADAPTERS) == connector_state.IMPLEMENTED_ADAPTERS


def test_has_adapter_agrees_with_registry() -> None:
    for connector_id in REAL_ADAPTERS:
        assert connector_state.has_adapter(connector_id) is True
    # A catalog connector without a registered builder is contract-only.
    assert connector_state.has_adapter("snowflake-evidence-lake") is False
    assert connector_state.has_adapter("not-a-real-connector") is False


def test_unknown_connector_id_raises_no_runner_registered(tmp_path: Path) -> None:
    # An enabled connector that the catalog knows but the registry does not must
    # still raise the exact "no sync runner registered" message via the runner.
    connector_state.append_config_event(
        tmp_path,
        connector_id="snowflake-evidence-lake",
        state="enabled",
        actor="alice",
    )
    with pytest.raises(connector_runner.ConnectorSyncError, match="no sync runner registered") as exc:
        connector_runner.run_connector_sync(tmp_path, connector_id="snowflake-evidence-lake")
    assert exc.value.run["result"] == "error"


@pytest.mark.parametrize(
    ("connector_id", "fixture", "extra"),
    [
        ("github-security", "github-governance", {"repo": "acme/model-service"}),
        ("okta-identity", "okta", {}),
        ("aws-posture", "aws", {}),
        ("jira-ticketing", "jira", {}),
    ],
)
def test_fixture_sync_flows_through_registry(
    tmp_path: Path,
    connector_id: str,
    fixture: str,
    extra: dict[str, str],
) -> None:
    connector_state.append_config_event(tmp_path, connector_id=connector_id, state="enabled", actor="alice")
    result = connector_runner.run_connector_sync(
        tmp_path,
        connector_id=connector_id,
        fixture_dir=FIXTURES / fixture,
        **extra,
    )
    assert result.result == "ok"
    assert result.evidence_count > 0
    assert result.materialized is True

    raw_rows = read_jsonl(tmp_path / connector_runner.CONNECTOR_RAW_FILE)
    assert validate_raw_events(raw_rows) == []
    assert len(raw_rows) == result.evidence_count

    run = connector_state.latest_run(tmp_path, connector_id, kind="sync")
    assert run["result"] == "ok"
    assert run["evidence_count"] == result.evidence_count
