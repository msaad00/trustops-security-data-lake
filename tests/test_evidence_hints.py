"""Connector evidence hint resolution tests."""

from __future__ import annotations

from security_lakehouse.evidence_hints import resolve_connector_hints


def test_identity_control_recommends_idp_connectors() -> None:
    hints = resolve_connector_hints(
        framework_id="soc2",
        control={
            "risk_domain": "identity",
            "asset_types": ["iam_role", "identity_user"],
        },
        article_ids=["CC6.1"],
        enabled_connector_ids={"okta-identity"},
    )
    connector_ids = [row["connector_id"] for row in hints]
    assert "okta-identity" in connector_ids
    assert hints[0]["configured"] is True
    assert any(row["connector_id"] == "aws-posture" for row in hints)


def test_cmmc_family_overrides_prefer_cloud_and_idp() -> None:
    hints = resolve_connector_hints(
        framework_id="cmmc-2-level2",
        control={"risk_domain": "identity", "asset_types": ["iam_role"]},
        article_ids=["3.1.1"],
        enabled_connector_ids=set(),
    )
    connector_ids = [row["connector_id"] for row in hints]
    assert connector_ids[0] in {"okta-identity", "aws-posture", "google-workspace-identity"}
    assert "okta-identity" in connector_ids
    assert "aws-posture" in connector_ids


def test_hints_cap_at_six_connectors() -> None:
    hints = resolve_connector_hints(
        framework_id="fedramp-moderate",
        control={
            "risk_domain": "controls-operations",
            "asset_types": ["cloud_resource", "repo", "audit_log", "data_store"],
        },
        article_ids=["AC-2"],
        enabled_connector_ids=set(),
    )
    assert len(hints) <= 6
    assert all(row["name"] for row in hints)
