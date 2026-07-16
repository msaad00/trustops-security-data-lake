"""Regression contract for clear cloud-account linking in the console."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PANEL = ROOT / "app/web/src/components/connectors/CloudLinkPanel.tsx"
DRAWER = ROOT / "app/web/src/components/drawers/ConnectorDrawer.tsx"
VALIDATION = ROOT / "app/web/src/lib/cloud-link-validation.ts"


def test_aws_linking_explains_authorization_and_role_boundary() -> None:
    panel = PANEL.read_text(encoding="utf-8")

    assert "TrustOps verifies STS assume-role after deployment." in panel
    assert "Deploy in AWS, then confirm the account." in panel
    assert "Open AWS guided deploy" in panel
    assert "AWS Console" in panel
    assert "CloudFormation CLI" in panel
    assert "Terraform CLI" in panel
    assert "Deployment method" in panel
    assert "CloudShell deploy script" in panel
    assert "Copy CloudShell script" in panel
    assert "Preview script" in panel
    assert "Run in the target AWS account; the final line prints" in panel
    assert 'useState<AwsDeployMode>("cloudformation")' in panel
    assert 'setAwsDeployMode("cloudformation")' in panel
    assert "AWS CLI deploy command" not in panel
    assert "Terraform deploy command" in panel
    assert "sanitizeAwsRoleName" in panel
    assert "awsQuickCreateUrl" in panel
    assert "awsTerraformCommand" in panel
    assert "Advanced options" in panel
    assert "Advanced role settings" not in panel
    assert "Read-only IAM posture" in panel
    assert "IAM posture read-only" in panel
    assert "mktemp /tmp/trustops-posture-readonly-role" in panel
    assert "ROLLBACK_FAILED" in panel
    assert "TemplateURL" not in panel
    assert "Save AWS account" in panel
    assert "Stage credentials" not in panel
    assert "AWS account ID" in panel
    assert "Use the account ID when you keep the default role name." in panel
    assert "Use a custom Role ARN" in panel
    assert "Account coverage" not in panel
    assert "Scale rollout" not in panel
    assert "Scale with StackSets or Terraform" in panel
    assert "CloudFormation StackSets" in panel
    assert "Terraform workspaces" in panel
    assert "Bulk account import" in panel
    assert "Multiple AWS accounts?" not in panel
    assert "Create one connection per account." not in panel
    assert "View trust details" not in panel
    assert "AWS role ARN" not in panel
    assert "TRUSTOPS_AWS_TEMPLATE_URL" in panel
    assert 'aria-label="AWS deployment method"' not in panel


def test_aws_linking_accepts_account_id_or_role_arn() -> None:
    validation = VALIDATION.read_text(encoding="utf-8")
    panel = PANEL.read_text(encoding="utf-8")

    assert "awsRoleIdentifierError" in validation
    assert "awsRoleArnFromIdentifier" in validation
    assert 'trimmed.startsWith("arn:")' in validation
    assert "/^[0-9\\s-]+$/" in validation
    assert "AWS account ID must be exactly 12 digits." in validation
    assert "return `arn:aws:iam::${accountId}:role/${roleName}`;" in validation
    assert "awsRoleArnFromIdentifier(awsRoleIdentifier, awsRoleName)" in panel
    assert "awsRoleIdentifierError(awsRoleIdentifier)" in panel
    assert 'placeholder="030225640638"' in panel
    assert 'placeholder="arn:aws:iam::123456789012:role/CustomTrustOpsRole"' in panel


def test_enabled_cloud_connector_hides_onboarding_and_duplicate_credentials() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const usesManagedCloudLink = supportsCloudLink(connector.connector_id);" in drawer
    assert "const showCloudLinkPanel =" in drawer
    assert "(!hasStagedServerCredentials || editCloudSetup)" in drawer
    assert "(isEnabled && editCloudSetup)" in drawer
    assert "<CloudLinkPanel" in drawer
    assert "!usesManagedCloudLink && (" in drawer
    assert "Edit setup" in drawer
    assert "Hide setup" in drawer


def test_enabled_cloud_connector_can_edit_and_reverify_setup() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const hasPendingConfigChanges =" in drawer
    assert "isEnabled && !hasPendingConfigChanges" in drawer
    assert "? latestProbeOk" in drawer
    assert "hasPendingConfigChanges" in drawer
    assert ": probeGateSatisfied" in drawer
    assert "payload.credentials = stagedCredentials;" in drawer
    assert "hasPendingConfigChanges && !probeGateSatisfied" in drawer
    assert "Test connection before saving these changes." in drawer
    assert "setCreds({});" in drawer
    assert "setSavedOptionsBaseline(stagedOptions);" in drawer
    assert "Save changes" in drawer
    assert "New setup staged" in drawer
    assert "Test connection, then save changes." in drawer
    assert "Edit setup" in drawer
    assert "Add another account" not in drawer
    assert 'connectedTab === "Config" && editCloudSetup' in drawer
    assert "const showInlineCloudSetup =" in drawer
    assert "!showInlineCloudSetup && (" in drawer


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
    assert "showCloudLinkPanel &&" in drawer
    assert "!showInlineCloudSetup && (" in drawer
    assert "<CloudLinkPanel" in drawer
    assert "(!usesManagedCloudLink || showManagedCloudConfiguration)" in drawer
    assert '<summary className="ui-label cursor-pointer list-none">' in drawer
    assert "Scope & automation" in drawer
    assert 'className="mt-3 grid items-start gap-2 2xl:grid-cols-[minmax(0,1fr)_minmax(18rem,0.72fr)]"' in drawer
    assert "runHistoryRows.length > 0 && (" in drawer


def test_aws_probe_errors_are_actionable_in_drawer() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "function runErrorDetail" in drawer
    assert "AWS STS probe failed." in drawer
    assert "role trust policy" in drawer
    assert "network access to AWS STS" in drawer
    assert "Configure AWS credentials for the TrustOps runtime" in drawer
    assert "Probe error: ${runErrorDetail(run)}" in drawer


def test_connected_cloud_drawer_is_compact_and_non_redundant() -> None:
    drawer = DRAWER.read_text(encoding="utf-8")

    assert "const showConnectedCloudSummary =" in drawer
    assert "usesManagedCloudLink && isEnabled;" in drawer
    assert 'aria-label="Connected connector view"' in drawer
    assert '"Overview", "Config", "Runs"' in drawer
    assert '"Overview", "Details", "History"' not in drawer
    assert "connectedTab ===" in drawer
    assert "compact?: boolean" in drawer
    assert "<LatestSyncProof" in drawer
    assert "runnable={isRunnable}" in drawer
    assert "compact\n                />" in drawer
    assert "rounded-full border border-line bg-panel px-2.5 py-1" in drawer
    assert "Connection details" in drawer
    assert "Schedule and scope" in drawer
    assert "Authorization" in drawer
    assert "Read-only role" in drawer
    assert "STS per run" in drawer
    assert "Organization rollout" in drawer
    assert "Every probe, sync, and scheduled run creates a fresh AWS" in drawer
    assert "Connector run log" in drawer
    assert "Sync lands raw connector evidence." in drawer
    assert "Eval produces gold" in drawer
    assert "controls, pass/fail metrics, and proof exports." in drawer
    assert "showConnectedCloudSummary ? (" in drawer
    assert "max-h-80 overflow-auto" in drawer
    assert "open={!usesManagedCloudLink && !showConnectedCloudSummary}" in drawer
    assert "Run history" not in drawer
    assert "see history" not in drawer
