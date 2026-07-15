"""Regression contract for clear cloud-account linking in the console."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PANEL = ROOT / "app/web/src/components/connectors/CloudLinkPanel.tsx"
DRAWER = ROOT / "app/web/src/components/drawers/ConnectorDrawer.tsx"


def test_aws_linking_explains_authorization_and_role_boundary() -> None:
    panel = PANEL.read_text(encoding="utf-8")

    assert "Account ID identifies the target; it does not grant access." in panel
    assert "Deploy read-only role" in panel
    assert "Save role connection" in panel
    assert "Stage credentials" not in panel
    assert "AWS role ARN" in panel
    assert "AWS account ID" not in panel


def test_enabled_cloud_connector_hides_onboarding_and_duplicate_credentials() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const usesManagedCloudLink = supportsCloudLink(connector.connector_id);" in drawer
    assert "usesManagedCloudLink && !isEnabled" in drawer
    assert "!usesManagedCloudLink && (" in drawer
