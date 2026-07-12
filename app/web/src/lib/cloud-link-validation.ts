const GCP_PROJECT_RE = /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/;
const AZURE_SUBSCRIPTION_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function sanitizeAwsAccountId(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 12);
}

export function sanitizeAzureSubscriptionId(raw: string): string {
  return raw
    .replace(/[^0-9a-f-]/gi, "")
    .slice(0, 36)
    .toLowerCase();
}

export function sanitizeGcpProjectId(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "")
    .slice(0, 30);
}

export function awsAccountIdError(raw: string): string | null {
  const digits = sanitizeAwsAccountId(raw);
  if (!digits) return "Enter your 12-digit AWS account ID.";
  if (digits.length !== 12) return "AWS account ID must be exactly 12 digits.";
  return null;
}

export function azureSubscriptionIdError(raw: string): string | null {
  const trimmed = sanitizeAzureSubscriptionId(raw);
  if (!trimmed) return "Enter your Azure subscription ID.";
  if (!AZURE_SUBSCRIPTION_RE.test(trimmed)) {
    return "Use a valid subscription GUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).";
  }
  return null;
}

export function gcpProjectIdError(raw: string): string | null {
  const trimmed = sanitizeGcpProjectId(raw);
  if (!trimmed) return "Enter your GCP project ID.";
  if (!GCP_PROJECT_RE.test(trimmed)) {
    return "Use a valid GCP project ID (lowercase letters, numbers, hyphens; 6–30 chars).";
  }
  return null;
}

export function cloudLinkFieldError(
  connectorId: string,
  values: { accountId: string; subscriptionId: string; projectId: string },
): string | null {
  if (connectorId === "aws-posture") return awsAccountIdError(values.accountId);
  if (connectorId === "azure-posture") {
    return azureSubscriptionIdError(values.subscriptionId);
  }
  if (connectorId === "gcp-posture") return gcpProjectIdError(values.projectId);
  return "Unsupported cloud link connector.";
}
