/** Connection and scope field definitions for the connector drawer. */

export interface ConnectorFieldDef {
  name: string;
  label: string;
  placeholder: string;
  secret?: boolean;
  required?: boolean;
  hint?: string;
}

export const CONNECTOR_CREDENTIAL_FIELDS: Record<string, ConnectorFieldDef[]> =
  {
    "clickhouse-telemetry-lake": [
      {
        name: "host",
        label: "ClickHouse host",
        placeholder: "https://cluster.example.clickhouse.cloud:8443",
        required: true,
      },
      {
        name: "user",
        label: "Read-only user",
        placeholder: "trustops_reader",
      },
      {
        name: "credential_ref",
        label: "Scoped credential reference",
        placeholder: "TRUSTOPS_CLICKHOUSE_TOKEN",
        required: true,
        hint: "Environment variable name holding the read-only token.",
      },
    ],
    "snowflake-evidence-lake": [
      {
        name: "account",
        label: "Snowflake account",
        placeholder: "MJFAYEE-YS65534",
        required: true,
      },
      {
        name: "user",
        label: "Service user",
        placeholder: "TRUSTOPS_INGEST_SVC",
        required: true,
      },
      {
        name: "private_key_ref",
        label: "Credential reference",
        placeholder: "SNOWFLAKE_PRIVATE_KEY_FILE",
        required: true,
        hint: "Key-pair file path or OAuth token env var for the service user.",
      },
      {
        name: "role",
        label: "Read-only role (optional)",
        placeholder: "TRUSTOPS_READER",
      },
      {
        name: "private_key_file_pwd_ref",
        label: "Key password env var (optional)",
        placeholder: "SNOWFLAKE_PRIVATE_KEY_FILE_PWD",
      },
    ],
    "aws-posture": [
      {
        name: "account_id",
        label: "AWS account ID",
        placeholder: "123456789012",
        required: true,
      },
      {
        name: "role_arn",
        label: "Read-only role ARN (optional)",
        placeholder:
          "arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole",
        hint: "Cross-account assume-role; pair with external ID in the trust policy.",
      },
      {
        name: "external_id",
        label: "External ID (optional, with role ARN)",
        placeholder: "shared secret used in the role trust policy",
      },
    ],
    "azure-posture": [
      {
        name: "subscription_id",
        label: "Azure subscription ID",
        placeholder: "00000000-0000-0000-0000-000000000000",
        required: true,
        hint: "Reader role or federated workload identity on this subscription.",
      },
    ],
    "gcp-posture": [
      {
        name: "project_id",
        label: "GCP project ID",
        placeholder: "my-project-123456",
        required: true,
        hint: "Uses Application Default Credentials (WIF or service account).",
      },
    ],
    "github-security": [
      {
        name: "credential_ref",
        label: "GitHub App installation token env",
        placeholder: "TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN",
        required: true,
        hint: "Read-only GitHub App token with repository metadata scopes.",
      },
    ],
    "gitlab-security": [
      {
        name: "credential_ref",
        label: "GitLab access token env",
        placeholder: "TRUSTOPS_GITLAB_ACCESS_TOKEN",
        required: true,
        hint: "Read-only project token with api read_repository scope.",
      },
    ],
    "okta-identity": [
      {
        name: "org_url",
        label: "Okta org URL",
        placeholder: "https://your-org.okta.com",
        required: true,
      },
      {
        name: "credential_ref",
        label: "API token env var",
        placeholder: "OKTA_API_TOKEN",
        required: true,
        hint: "Read-only Okta API token (okta.users.read, okta.policies.read).",
      },
    ],
    "okta-system-log": [
      {
        name: "org_url",
        label: "Okta org URL",
        placeholder: "https://your-org.okta.com",
        required: true,
      },
      {
        name: "credential_ref",
        label: "API token env var",
        placeholder: "OKTA_API_TOKEN",
        required: true,
      },
    ],
    "google-workspace-identity": [
      {
        name: "customer_id",
        label: "Google Workspace customer ID",
        placeholder: "C01234567",
        required: true,
      },
      {
        name: "credential_ref",
        label: "OAuth access token env",
        placeholder: "GOOGLE_WORKSPACE_ACCESS_TOKEN",
        required: true,
        hint: "Read-only directory scopes; token mounted by your secret manager.",
      },
    ],
    "jira-ticketing": [
      {
        name: "base_url",
        label: "Jira site URL",
        placeholder: "https://your-org.atlassian.net",
        required: true,
      },
      {
        name: "email",
        label: "Jira account email",
        placeholder: "grc-bot@your-org.com",
        required: true,
      },
      {
        name: "credential_ref",
        label: "API token env var",
        placeholder: "JIRA_API_TOKEN",
        required: true,
        hint: "Read-only Jira Cloud API token for the service account.",
      },
    ],
  };

export const CONNECTOR_SCOPE_FIELDS: Record<string, ConnectorFieldDef[]> = {
  "aws-posture": [
    {
      name: "region",
      label: "Region",
      placeholder: "us-east-1",
    },
  ],
  "github-security": [
    {
      name: "repo",
      label: "Repository (owner/name)",
      placeholder: "acme-corp/platform",
      required: true,
      hint: "Single repo per connector; add another connector row for more repos.",
    },
  ],
  "gitlab-security": [
    {
      name: "repo",
      label: "Project path (group/project)",
      placeholder: "acme/platform",
      required: true,
      hint: "GitLab project path; URL-encode nested groups if needed.",
    },
    {
      name: "api_url",
      label: "GitLab API URL (optional)",
      placeholder: "https://gitlab.com/api/v4",
      hint: "Self-managed GitLab base API URL; defaults to gitlab.com.",
    },
  ],
  "snowflake-evidence-lake": [
    {
      name: "warehouse",
      label: "Warehouse",
      placeholder: "TRUSTOPS_READ_WH",
      required: true,
    },
    {
      name: "database",
      label: "Database",
      placeholder: "TRUSTOPS_SECURITY_LAKE",
      required: true,
    },
    {
      name: "schema",
      label: "Schema",
      placeholder: "EVIDENCE",
      required: true,
    },
    {
      name: "audit_events",
      label: "Audit events view",
      placeholder: "TRUSTOPS_AUDIT_EVENTS",
      required: true,
    },
    {
      name: "control_posture",
      label: "Control posture view",
      placeholder: "TRUSTOPS_CONTROL_POSTURE",
      required: true,
    },
    {
      name: "asset_risk",
      label: "Asset risk view",
      placeholder: "TRUSTOPS_ASSET_RISK",
      required: true,
    },
    {
      name: "evidence_bundles",
      label: "Evidence bundles view",
      placeholder: "TRUSTOPS_EVIDENCE_BUNDLES",
      required: true,
    },
  ],
};

export const SYNC_SCHEDULE_FIELD: ConnectorFieldDef = {
  name: "sync_schedule",
  label: "Sync schedule",
  placeholder: "every 15m",
  hint: "Ingest-only cadence: @hourly, @daily, every 15m. Defaults to split ingest/eval when set.",
};

export const EVAL_SCHEDULE_FIELD: ConnectorFieldDef = {
  name: "eval_schedule",
  label: "Eval schedule",
  placeholder: "every 6h",
  hint: "Lake-wide materialize + evaluate cadence (default every 6h when sync is set).",
};

export function schedulerFieldsFor(isRunnable: boolean): ConnectorFieldDef[] {
  return isRunnable ? [SYNC_SCHEDULE_FIELD, EVAL_SCHEDULE_FIELD] : [];
}

export function fallbackCredentialFields(
  credentialType: string,
): ConnectorFieldDef[] {
  if (credentialType.includes("oauth"))
    return [
      {
        name: "client_id",
        label: "Client ID",
        placeholder: "client id",
        required: true,
      },
      {
        name: "client_secret_ref",
        label: "Client secret reference",
        placeholder: "TRUSTOPS_CLIENT_SECRET",
        required: true,
      },
      {
        name: "refresh_token_ref",
        label: "Refresh token reference",
        placeholder: "TRUSTOPS_REFRESH_TOKEN",
        required: true,
      },
    ];
  if (credentialType.includes("key_pair"))
    return [
      {
        name: "account",
        label: "Account",
        placeholder: "account",
        required: true,
      },
      {
        name: "user",
        label: "User",
        placeholder: "read-only user",
        required: true,
      },
      {
        name: "private_key",
        label: "Private key reference",
        placeholder: "TRUSTOPS_PRIVATE_KEY",
        secret: true,
        required: true,
      },
    ];
  if (credentialType.includes("token"))
    return [
      {
        name: "credential_ref",
        label: "Credential reference",
        placeholder: "TRUSTOPS_API_TOKEN",
        required: true,
        hint: "Environment variable name; raw secrets are not stored in the lake.",
      },
    ];
  if (credentialType.includes("local"))
    return [
      {
        name: "lake_path",
        label: "Lake path",
        placeholder: "/lake/trustops",
        required: true,
      },
    ];
  return [
    {
      name: "api_key",
      label: "API key reference",
      placeholder: "TRUSTOPS_API_KEY",
      required: true,
    },
  ];
}

export function credentialFieldsFor(
  connectorId: string,
  credentialType: string,
): ConnectorFieldDef[] {
  return (
    CONNECTOR_CREDENTIAL_FIELDS[connectorId] ??
    fallbackCredentialFields(credentialType)
  );
}

export function scopeFieldsFor(connectorId: string): ConnectorFieldDef[] {
  return CONNECTOR_SCOPE_FIELDS[connectorId] ?? [];
}
