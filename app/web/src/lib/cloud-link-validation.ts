const GCP_PROJECT_RE = /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/;
const AZURE_SUBSCRIPTION_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const AWS_ROLE_ARN_RE =
  /^arn:aws(?:-us-gov|-cn)?:iam::[0-9]{12}:role\/[A-Za-z0-9+=,.@_\/-]{1,512}$/;

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

export function awsRoleArnError(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return "Paste the role ARN from the CloudFormation output.";
  if (!AWS_ROLE_ARN_RE.test(trimmed)) return "Use a valid AWS IAM role ARN.";
  return null;
}

export function awsRoleIdentifierError(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return "Enter your AWS account ID.";
  if (AWS_ROLE_ARN_RE.test(trimmed)) return null;
  if (trimmed.startsWith("arn:")) {
    return "Use a valid AWS IAM role ARN or a 12-digit AWS account ID.";
  }

  if (!/^[0-9\s-]+$/.test(trimmed)) {
    return "Use a valid AWS IAM role ARN or a 12-digit AWS account ID.";
  }
  const accountId = sanitizeAwsAccountId(trimmed);
  if (accountId.length !== 12) {
    return "AWS account ID must be exactly 12 digits.";
  }
  return null;
}

export function awsRoleArnFromIdentifier(
  raw: string,
  roleName: string,
): string {
  const trimmed = raw.trim();
  if (AWS_ROLE_ARN_RE.test(trimmed)) return trimmed;

  const accountId = sanitizeAwsAccountId(trimmed);
  return `arn:aws:iam::${accountId}:role/${roleName}`;
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
  values: { roleArn: string; subscriptionId: string; projectId: string },
): string | null {
  if (connectorId === "aws-posture") {
    return awsRoleIdentifierError(values.roleArn);
  }
  if (connectorId === "azure-posture") {
    return azureSubscriptionIdError(values.subscriptionId);
  }
  if (connectorId === "gcp-posture") return gcpProjectIdError(values.projectId);
  return "Unsupported cloud link connector.";
}
