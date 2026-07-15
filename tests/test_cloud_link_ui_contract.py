"""Regression contract for clear cloud-account linking in the console."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PANEL = ROOT / "app/web/src/components/connectors/CloudLinkPanel.tsx"
DRAWER = ROOT / "app/web/src/components/drawers/ConnectorDrawer.tsx"


def test_aws_linking_explains_authorization_and_role_boundary() -> None:
    panel = PANEL.read_text(encoding="utf-8")

    assert "Account ID identifies the target; it does not grant access." in panel
    assert "Open AWS guided deploy" in panel
    assert "AWS Console" in panel
    assert "CLI script" in panel
    assert "AWS CLI deploy command" in panel
    assert "Copy deploy command" in panel
    assert "sanitizeAwsRoleName" in panel
    assert "awsQuickCreateUrl" in panel
    assert "Role name" in panel
    assert "Grant set" in panel
    assert "IAM posture read-only" in panel
    assert "mktemp /tmp/trustops-posture-readonly-role" in panel
    assert "ROLLBACK_FAILED" in panel
    assert "TemplateURL" not in panel
    assert "Save role connection" in panel
    assert "Stage credentials" not in panel
    assert "AWS role ARN" in panel
    assert "AWS account ID" not in panel
    assert "TRUSTOPS_AWS_TEMPLATE_URL" in panel


def test_enabled_cloud_connector_hides_onboarding_and_duplicate_credentials() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const usesManagedCloudLink = supportsCloudLink(connector.connector_id);" in drawer
    assert "!hasStagedServerCredentials && (" in drawer
    assert "<CloudLinkPanel" in drawer
    assert "!usesManagedCloudLink && (" in drawer


def test_aws_drawer_has_one_linear_setup_flow_and_no_duplicate_sync_action() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    labels = [drawer.index(f'label: "{label}"') for label in ("Authorize", "Verify", "Scope", "Sync")]
    assert labels == sorted(labels)
    assert 'label: "Access"' not in drawer
    assert 'label: "Validate"' not in drawer
    assert drawer.count("Sync evidence") == 1
    assert "const showDiscoveryAction = !usesManagedCloudLink && needsDiscovery;" in drawer
    assert "{showDiscoveryAction ? (" in drawer


def test_managed_cloud_drawer_uses_progressive_disclosure() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const showManagedCloudConfiguration =" in drawer
    assert "!hasStagedServerCredentials && (" in drawer
    assert "<CloudLinkPanel" in drawer
    assert "(!usesManagedCloudLink || showManagedCloudConfiguration)" in drawer
    assert '<summary className="ui-label cursor-pointer list-none">' in drawer
    assert "Scope & automation" in drawer
    assert 'className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.72fr)]"' in drawer
    assert "runHistoryRows.length > 0 && (" in drawer


def test_connected_cloud_drawer_is_compact_and_non_redundant() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const showConnectedCloudSummary =" in drawer
    assert "usesManagedCloudLink && isEnabled;" in drawer
    assert 'aria-label="Connected connector view"' in drawer
    assert '"Overview", "Details", "Runs"' in drawer
    assert '"Overview", "Details", "History"' not in drawer
    assert "connectedTab ===" in drawer
    assert "Connection details" in drawer
    assert "Connector run log" in drawer
    assert "Sync lands raw connector evidence." in drawer
    assert "Eval produces gold" in drawer
    assert "controls, pass/fail metrics, and proof exports." in drawer
    assert "showConnectedCloudSummary ? (" in drawer
    assert "max-h-80 overflow-auto" in drawer
    assert "open={!usesManagedCloudLink && !showConnectedCloudSummary}" in drawer
    assert "Run history" not in drawer
    assert "see history" not in drawer
