export type IntegrationPreset = {
  connectorId: string;
  title: string;
  authLabel: string;
  badges: string[];
  summary: string;
  providerSetup: string;
  trustOpsInput: string;
  advancedTitle: string;
  advancedDetails: string[];
};

const PRESETS: Record<string, IntegrationPreset> = {
  "aws-posture": {
    connectorId: "aws-posture",
    title: "AWS account",
    authLabel: "STS assume-role",
    badges: ["STS", "No long-lived keys"],
    summary:
      "Deploy the customer-owned AWS role, then save the account target. TrustOps verifies STS assume-role after deployment.",
    providerSetup:
      "CloudFormation, Terraform, or StackSets creates a read-only IAM role in the target account.",
    trustOpsInput: "Account ID for the default role, or a full Role ARN.",
    advancedTitle: "Organization rollout",
    advancedDetails: [
      "Use CloudFormation StackSets or Terraform workspaces for many AWS accounts.",
      "Each account sync creates a fresh STS assume-role session with the stored External ID.",
    ],
  },
  "gcp-posture": {
    connectorId: "gcp-posture",
    title: "GCP project",
    authLabel: "Workload identity federation",
    badges: ["Workload identity federation", "No long-lived keys"],
    summary:
      "Apply the read-only Terraform reader identity in your GCP project, then enter the project ID to stage the connector.",
    providerSetup:
      "Terraform grants Cloud Asset and IAM read permissions to the TrustOps workload identity.",
    trustOpsInput: "Project ID for the target project.",
    advancedTitle: "Folder or organization rollout",
    advancedDetails: [
      "Apply the same reader module across projects from Terraform or your platform workspace.",
      "TrustOps probes the configured project before sync lands IAM and asset posture evidence.",
    ],
  },
  "azure-posture": {
    connectorId: "azure-posture",
    title: "Azure subscription",
    authLabel: "Reader role",
    badges: ["Reader role", "No long-lived keys"],
    summary:
      "Grant Reader to the TrustOps Entra app or workload identity, then confirm the subscription. Scheduled sync uses fresh Azure tokens; no passwords are stored.",
    providerSetup:
      "Azure Cloud Shell grants Reader at subscription or management-group scope.",
    trustOpsInput: "Subscription ID printed by setup or returned after admin consent.",
    advancedTitle: "Management-group rollout",
    advancedDetails: [
      "Use management-group scope when the same TrustOps identity should read many subscriptions.",
      "No Azure password or client secret is stored in TrustOps.",
    ],
  },
  "snowflake-evidence-lake": {
    connectorId: "snowflake-evidence-lake",
    title: "Snowflake evidence lake",
    authLabel: "Key-pair or OAuth reference",
    badges: ["Key-pair or OAuth reference", "Secret reference only"],
    summary:
      "Connect a read-only Snowflake service identity, discover visible objects, then select the evidence views.",
    providerSetup:
      "Create a service user and role with USAGE plus SELECT on the evidence database, schema, and views.",
    trustOpsInput:
      "Account, service user, and secret reference for a mounted key-pair or OAuth token.",
    advancedTitle: "Evidence view mapping",
    advancedDetails: [
      "Discovery shows only objects visible to the read-only role.",
      "Advanced view names stay collapsed unless the warehouse schema is custom.",
    ],
  },
  "okta-identity": {
    connectorId: "okta-identity",
    title: "Okta identity",
    authLabel: "Okta API token reference",
    badges: ["Okta API token reference", "Read-only scopes"],
    summary:
      "Use a scoped Okta token reference to read users, factors, and MFA policy evidence.",
    providerSetup:
      "Create a read-only Okta API token with users, factors, and policy read scopes.",
    trustOpsInput: "Okta org URL and the runtime secret reference name.",
    advancedTitle: "System Log option",
    advancedDetails: [
      "Use Okta System Log as a separate event-stream connector when login events are needed.",
      "TrustOps stores the reference name, not the token value.",
    ],
  },
  "okta-system-log": {
    connectorId: "okta-system-log",
    title: "Okta System Log",
    authLabel: "Okta API token reference",
    badges: ["Okta API token reference", "Event stream"],
    summary:
      "Use a scoped Okta token reference to read authentication and session events.",
    providerSetup: "Grant okta.logs.read to a service token in Okta.",
    trustOpsInput: "Okta org URL and the runtime secret reference name.",
    advancedTitle: "Event freshness",
    advancedDetails: [
      "System Log has a shorter freshness SLO than identity posture.",
      "Keep the token read-only and rotate it in your secret manager.",
    ],
  },
  "identity-provider": {
    connectorId: "identity-provider",
    title: "Entra identity",
    authLabel: "Entra app or workload identity",
    badges: ["Entra app or workload identity", "Read-only directory"],
    summary:
      "Use provider-native OAuth client credentials or workload identity to read users, groups, assignments, and access reviews.",
    providerSetup:
      "Register an Entra application or managed identity with read-only Graph permissions.",
    trustOpsInput: "Tenant, client identity, and secret or federated credential reference.",
    advancedTitle: "SSO provider preset",
    advancedDetails: [
      "Use the same preset pattern for Okta, Entra, and Google Workspace identity sources.",
      "Human console SSO is separate from read-only evidence collection.",
    ],
  },
  "google-workspace-identity": {
    connectorId: "google-workspace-identity",
    title: "Google Workspace identity",
    authLabel: "Google Workspace OAuth reference",
    badges: ["Google Workspace OAuth reference", "Read-only directory"],
    summary:
      "Use a mounted OAuth token reference to read Workspace users, groups, and MFA posture.",
    providerSetup:
      "Authorize read-only Admin SDK Directory scopes for a service identity.",
    trustOpsInput: "Workspace customer ID and the runtime OAuth token reference.",
    advancedTitle: "Directory scopes",
    advancedDetails: [
      "Use directory.users.readonly, directory.groups.readonly, and directory.user.security.readonly.",
      "TrustOps stores the reference name, not the token value.",
    ],
  },
};

export function getIntegrationPreset(
  connectorId: string,
): IntegrationPreset | null {
  return PRESETS[connectorId] ?? null;
}
