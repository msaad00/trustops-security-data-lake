/**
 * Neutral vendor marks for connector sources (enterprise GRC-style integration tiles).
 *
 * These are text marks with vendor-recognizable accent colors — not official
 * product logos. See docs/THIRD_PARTY_ASSETS.md.
 */

export interface ConnectorVisual {
  vendor: string;
  mark: string;
  accent: string;
  bg: string;
  categoryLabel: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  warehouse: "Data warehouse",
  analytics_lake: "Analytics lake",
  evidence_store: "Evidence store",
  developer_platform: "Developer platform",
  identity: "Identity",
  cloud: "Cloud posture",
  workflow: "Workflow",
  detections: "Detections",
  runtime_security: "Runtime security",
  starter_mode: "Local evidence",
};

export const CONNECTOR_VISUALS: Record<string, ConnectorVisual> = {
  "snowflake-evidence-lake": {
    vendor: "Snowflake",
    mark: "SF",
    accent: "#29B5E8",
    bg: "#ecfeff",
    categoryLabel: "Data warehouse",
  },
  "clickhouse-telemetry-lake": {
    vendor: "ClickHouse",
    mark: "CH",
    accent: "#FFCC01",
    bg: "#fffbeb",
    categoryLabel: "Analytics lake",
  },
  "object-storage-evidence": {
    vendor: "Object storage",
    mark: "S3",
    accent: "#FF9900",
    bg: "#fff7ed",
    categoryLabel: "Evidence store",
  },
  "github-security": {
    vendor: "GitHub",
    mark: "GH",
    accent: "#24292f",
    bg: "#f6f8fa",
    categoryLabel: "Developer platform",
  },
  "okta-identity": {
    vendor: "Okta",
    mark: "OKTA",
    accent: "#007DC1",
    bg: "#eff6ff",
    categoryLabel: "Identity",
  },
  "okta-system-log": {
    vendor: "Okta",
    mark: "LOG",
    accent: "#007DC1",
    bg: "#eff6ff",
    categoryLabel: "Identity",
  },
  "aws-posture": {
    vendor: "Amazon Web Services",
    mark: "AWS",
    accent: "#FF9900",
    bg: "#fff7ed",
    categoryLabel: "Cloud posture",
  },
  "identity-provider": {
    vendor: "Identity provider",
    mark: "IdP",
    accent: "#6366f1",
    bg: "#eef2ff",
    categoryLabel: "Identity",
  },
  ticketing: {
    vendor: "Ticketing",
    mark: "TMS",
    accent: "#6366f1",
    bg: "#eef2ff",
    categoryLabel: "Workflow",
  },
  "siem-alerts": {
    vendor: "SIEM",
    mark: "SIEM",
    accent: "#dc2626",
    bg: "#fef2f2",
    categoryLabel: "Detections",
  },
  "runtime-gateway": {
    vendor: "Runtime gateway",
    mark: "RT",
    accent: "#7c3aed",
    bg: "#f5f3ff",
    categoryLabel: "Runtime security",
  },
  "managed-local-evidence": {
    vendor: "Local lake",
    mark: "LOC",
    accent: "#64748b",
    bg: "#f1f5f9",
    categoryLabel: "Local evidence",
  },
  "google-workspace-identity": {
    vendor: "Google Workspace",
    mark: "G",
    accent: "#4285F4",
    bg: "#eff6ff",
    categoryLabel: "Identity",
  },
  "gcp-posture": {
    vendor: "Google Cloud",
    mark: "GCP",
    accent: "#4285F4",
    bg: "#eff6ff",
    categoryLabel: "Cloud posture",
  },
  "azure-posture": {
    vendor: "Microsoft Azure",
    mark: "AZ",
    accent: "#0078D4",
    bg: "#eff6ff",
    categoryLabel: "Cloud posture",
  },
  "jira-ticketing": {
    vendor: "Atlassian Jira",
    mark: "Jira",
    accent: "#0052CC",
    bg: "#eff6ff",
    categoryLabel: "Workflow",
  },
};

export function connectorVisual(
  connectorId: string,
  fallback?: { name?: string; category?: string },
): ConnectorVisual {
  const known = CONNECTOR_VISUALS[connectorId];
  if (known) return known;
  const name = fallback?.name ?? connectorId;
  const category = fallback?.category ?? "connector";
  return {
    vendor: name,
    mark: name.slice(0, 3).toUpperCase(),
    accent: "#2563eb",
    bg: "#eff6ff",
    categoryLabel: CATEGORY_LABELS[category] ?? category.replace(/_/g, " "),
  };
}
