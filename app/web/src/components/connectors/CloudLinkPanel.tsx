"use client";

import { useEffect, useMemo, useState } from "react";
import { Copy, ExternalLink, Link2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useCloudLinkCompleteMutation,
  useCloudLinkStartMutation,
} from "@/lib/api/hooks";
import type { CloudLinkSession } from "@/lib/api/types";
import type { ConnectorView } from "@/lib/api/types";
import { BRAND } from "@/lib/brand";
import {
  awsRoleArnFromIdentifier,
  awsRoleIdentifierError,
  azureSubscriptionIdError,
  cloudLinkFieldError,
  gcpProjectIdError,
  sanitizeAzureSubscriptionId,
  sanitizeGcpProjectId,
} from "@/lib/cloud-link-validation";

const CLOUD_LINK_IDS = new Set(["aws-posture", "azure-posture", "gcp-posture"]);
const AWS_TEMPLATE_PATH = "deploy/aws/trustops-posture-readonly-role.yaml";
const AWS_STACK_NAME = "TrustOpsPostureReadOnly";
const AWS_ROLE_NAME = "TrustOpsPostureReadOnlyRole";
const AWS_ROLE_NAME_ALLOWED = /[^A-Za-z0-9+=,.@_-]/g;
type AwsDeployMode = "console" | "cloudformation" | "terraform";
type AwsDeployOption = {
  value: AwsDeployMode;
  label: string;
  detail: string;
};

interface Props {
  connector: ConnectorView;
  linkSessionId?: string | null;
  onLinked: (credentials: Record<string, string>) => void;
  onToast: (msg: string) => void;
}

export function supportsCloudLink(connectorId: string) {
  return CLOUD_LINK_IDS.has(connectorId);
}

function linkDescription(connectorId: string): string {
  if (connectorId === "aws-posture") {
    return "Deploy in AWS, then confirm the account. TrustOps verifies STS assume-role after deployment.";
  }
  if (connectorId === "azure-posture") {
    return `Grant admin consent for the ${BRAND.name} Azure app, then enter the subscription ID to stage the connector.`;
  }
  return "Apply the read-only Terraform reader identity in your GCP project, then enter the project ID to stage the connector.";
}

function shellQuote(value: string): string {
  return `'${value.replaceAll("'", "'\"'\"'")}'`;
}

function sanitizeAwsRoleName(value: string): string {
  return value.replace(AWS_ROLE_NAME_ALLOWED, "").slice(0, 64);
}

function awsDeploymentRoleName(roleName: string | null | undefined): string {
  return sanitizeAwsRoleName(roleName?.trim() || "") || AWS_ROLE_NAME;
}

function awsQuickCreateUrl(
  session: CloudLinkSession,
  roleName: string,
): string | null {
  if (!session.quick_create_url) return null;
  try {
    const url = new URL(session.quick_create_url);
    const selectedRoleName = awsDeploymentRoleName(roleName);
    if (url.hash.includes("?")) {
      const [path, query = ""] = url.hash.slice(1).split("?", 2);
      const params = new URLSearchParams(query);
      params.set("param_RoleName", selectedRoleName);
      url.hash = `${path}?${params.toString()}`;
    } else {
      url.searchParams.set("param_RoleName", selectedRoleName);
    }
    return url.toString();
  } catch {
    return session.quick_create_url;
  }
}

function awsDeployCommand(
  session: CloudLinkSession,
  roleName: string,
): string | null {
  if (!session.external_id || !session.trusted_principal) return null;
  const selectedRoleName = awsDeploymentRoleName(roleName || session.role_name);
  const templateSetup = session.template_url
    ? `template_file="$(mktemp /tmp/trustops-posture-readonly-role.XXXXXX.yaml)"
trap 'rm -f "$template_file"' EXIT
curl -fsSL ${shellQuote(session.template_url)} -o "$template_file"
`
    : "";
  const templateArg = session.template_url
    ? '"$template_file"'
    : shellQuote(session.manual_template_path || AWS_TEMPLATE_PATH);

  return `stack_status="$(aws cloudformation describe-stacks \\
  --stack-name ${shellQuote(AWS_STACK_NAME)} \\
  --query "Stacks[0].StackStatus" \\
  --output text 2>/dev/null || true)"

if [ "$stack_status" = "ROLLBACK_FAILED" ] || [ "$stack_status" = "ROLLBACK_COMPLETE" ]; then
  aws cloudformation delete-stack --stack-name ${shellQuote(AWS_STACK_NAME)}
  aws cloudformation wait stack-delete-complete --stack-name ${shellQuote(AWS_STACK_NAME)}
fi

${templateSetup}aws cloudformation deploy \\
  --stack-name ${shellQuote(AWS_STACK_NAME)} \\
  --template-file ${templateArg} \\
  --capabilities CAPABILITY_NAMED_IAM \\
  --parameter-overrides \\
    TrustedPrincipalArn=${shellQuote(session.trusted_principal)} \\
    ExternalId=${shellQuote(session.external_id)} \\
    RoleName=${shellQuote(selectedRoleName)}

aws cloudformation describe-stacks \\
  --stack-name ${shellQuote(AWS_STACK_NAME)} \\
  --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue" \\
  --output text`;
}

function awsTerraformCommand(
  session: CloudLinkSession,
  roleName: string,
): string | null {
  if (!session.external_id || !session.trusted_principal) return null;
  const selectedRoleName = awsDeploymentRoleName(roleName || session.role_name);
  const templateSetup = session.terraform_url
    ? `terraform_dir="$(mktemp -d /tmp/trustops-posture-role.XXXXXX)"
trap 'rm -rf "$terraform_dir"' EXIT
curl -fsSL ${shellQuote(session.terraform_url)} -o "$terraform_dir/main.tf"
`
    : "";
  const manualTerraformDir = session.manual_terraform_path
    ? session.manual_terraform_path.replace(/\/[^/]+$/, "")
    : "deploy/aws";
  const terraformChdir = session.terraform_url
    ? '"$terraform_dir"'
    : shellQuote(manualTerraformDir);

  return `${templateSetup}terraform -chdir=${terraformChdir} init
terraform -chdir=${terraformChdir} apply -auto-approve \\
  -var trusted_principal_arn=${shellQuote(session.trusted_principal)} \\
  -var external_id=${shellQuote(session.external_id)} \\
  -var role_name=${shellQuote(selectedRoleName)}

terraform -chdir=${terraformChdir} output -raw role_arn`;
}

export function CloudLinkPanel({
  connector,
  linkSessionId,
  onLinked,
  onToast,
}: Props) {
  const start = useCloudLinkStartMutation();
  const complete = useCloudLinkCompleteMutation();
  const [session, setSession] = useState<CloudLinkSession | null>(null);
  const [roleArn, setRoleArn] = useState("");
  const [customRoleArn, setCustomRoleArn] = useState("");
  const [subscriptionId, setSubscriptionId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const [awsRoleName, setAwsRoleName] = useState(AWS_ROLE_NAME);
  const [awsDeployMode, setAwsDeployMode] =
    useState<AwsDeployMode>("cloudformation");
  const awsRoleIdentifier =
    connector.connector_id === "aws-posture"
      ? customRoleArn.trim() || roleArn
      : roleArn;

  useEffect(() => {
    if (!linkSessionId) return;
    setSession((prev) => {
      if (prev?.session_id === linkSessionId) return prev;
      return {
        session_id: linkSessionId,
        connector_id: connector.connector_id,
        status: "pending",
      };
    });
  }, [connector.connector_id, linkSessionId]);

  useEffect(() => {
    if (connector.connector_id !== "aws-posture" || !session?.session_id) {
      return;
    }
    setAwsRoleName(awsDeploymentRoleName(session.role_name));
  }, [connector.connector_id, session?.role_name, session?.session_id]);

  const validationError = useMemo(
    () =>
      cloudLinkFieldError(connector.connector_id, {
        roleArn: awsRoleIdentifier,
        subscriptionId,
        projectId,
      }),
    [awsRoleIdentifier, connector.connector_id, projectId, subscriptionId],
  );

  const canComplete =
    Boolean(session?.session_id) &&
    !complete.isPending &&
    validationError === null;
  const awsCloudFormationCommand = useMemo(() => {
    if (!session) return null;
    if (connector.connector_id === "aws-posture") {
      return awsDeployCommand(session, awsRoleName);
    }
    return null;
  }, [awsRoleName, connector.connector_id, session]);
  const awsTerraformDeployCommand = useMemo(() => {
    if (!session || connector.connector_id !== "aws-posture") return null;
    return awsTerraformCommand(session, awsRoleName);
  }, [awsRoleName, connector.connector_id, session]);
  const deployCommand = useMemo(() => {
    if (!session || connector.connector_id === "aws-posture") return null;
    return session.deploy_command ?? null;
  }, [connector.connector_id, session]);
  const quickCreateUrl = useMemo(() => {
    if (!session || connector.connector_id !== "aws-posture") {
      return session?.quick_create_url ?? null;
    }
    return awsQuickCreateUrl(session, awsRoleName);
  }, [awsRoleName, connector.connector_id, session]);
  const awsDeployMethod = (
    value: AwsDeployMode,
    fallbackLabel: string,
    fallbackDetail: string,
  ) => {
    const method = session?.deployment_methods?.find(
      (candidate) => candidate.id === value,
    );
    return {
      label: method?.label ?? fallbackLabel,
      detail: method?.detail ?? fallbackDetail,
    };
  };
  const awsDeployOptions: AwsDeployOption[] =
    connector.connector_id === "aws-posture"
      ? [
          quickCreateUrl
            ? {
                value: "console" as const,
                ...awsDeployMethod(
                  "console",
                  "AWS Console",
                  "Guided CloudFormation",
                ),
              }
            : null,
          awsCloudFormationCommand
            ? {
                value: "cloudformation" as const,
                ...awsDeployMethod(
                  "cloudformation",
                  "CloudFormation CLI",
                  "AWS CLI deploy",
                ),
              }
            : null,
          awsTerraformDeployCommand
            ? {
                value: "terraform" as const,
                ...awsDeployMethod(
                  "terraform",
                  "Terraform CLI",
                  "IaC workflow",
                ),
              }
            : null,
        ].filter((item): item is NonNullable<typeof item> => item !== null)
      : [];
  const effectiveAwsDeployMode = awsDeployOptions.some(
    (option) => option.value === awsDeployMode,
  )
    ? awsDeployMode
    : (awsDeployOptions[0]?.value ?? awsDeployMode);
  const activeAwsDeployCommand =
    effectiveAwsDeployMode === "terraform"
      ? awsTerraformDeployCommand
      : effectiveAwsDeployMode === "cloudformation"
        ? awsCloudFormationCommand
        : null;

  const begin = async () => {
    setFieldError(null);
    setTouched(false);
    setAwsRoleName(AWS_ROLE_NAME);
    setAwsDeployMode("cloudformation");
    setRoleArn("");
    setCustomRoleArn("");
    try {
      const row = await start.mutateAsync({
        id: connector.connector_id,
        publicUrl:
          typeof window !== "undefined" ? window.location.origin : undefined,
      });
      setSession(row);
      onToast("Cloud link session started — complete the steps below");
    } catch (err) {
      onToast(`Cloud link failed: ${(err as Error).message}`);
    }
  };

  const finish = async () => {
    if (!session?.session_id) return;
    setTouched(true);
    const error = cloudLinkFieldError(connector.connector_id, {
      roleArn: awsRoleIdentifier,
      subscriptionId,
      projectId,
    });
    if (error) {
      setFieldError(error);
      onToast(error);
      return;
    }
    setFieldError(null);
    try {
      const result = await complete.mutateAsync({
        id: connector.connector_id,
        sessionId: session.session_id,
        roleArn:
          connector.connector_id === "aws-posture"
            ? awsRoleArnFromIdentifier(awsRoleIdentifier, awsRoleName)
            : undefined,
        subscriptionId:
          connector.connector_id === "azure-posture"
            ? sanitizeAzureSubscriptionId(subscriptionId)
            : undefined,
        projectId:
          connector.connector_id === "gcp-posture"
            ? sanitizeGcpProjectId(projectId)
            : undefined,
      });
      const creds = (result.configure?.credentials ?? {}) as Record<
        string,
        string
      >;
      onLinked(creds);
      onToast("Credentials staged — run Test connection to verify access");
    } catch (err) {
      onToast(`Complete link failed: ${(err as Error).message}`);
    }
  };

  const copyDeployCommand = async (command: string | null | undefined) => {
    if (!command) return;
    try {
      await navigator.clipboard.writeText(command);
      onToast("Deploy command copied");
    } catch {
      onToast("Could not copy deploy command");
    }
  };

  const showFieldError =
    fieldError ?? (touched && validationError ? validationError : null);

  if (!supportsCloudLink(connector.connector_id)) return null;

  const isAwsPosture = connector.connector_id === "aws-posture";
  const headerLabel = isAwsPosture
    ? "Read-only AWS role"
    : "Cloud account linking";

  return (
    <section className="rounded-lg border border-brand/30 bg-brand/5 p-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <Link2 className="h-4 w-4 text-brand" />
        <div className="text-xs font-black uppercase tracking-wide text-ink">
          {headerLabel}
        </div>
        <Badge tone="ready">Read-only access</Badge>
        <Badge>No long-lived keys</Badge>
      </div>
      <p className="mt-1.5 text-xs leading-5 text-muted">
        {linkDescription(connector.connector_id)}
      </p>
      {!session ? (
        <Button
          type="button"
          variant="primary"
          size="sm"
          className="mt-2"
          onClick={begin}
          disabled={start.isPending}
        >
          {start.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="h-4 w-4" />
          )}{" "}
          Connect cloud account
        </Button>
      ) : (
        <div className="mt-2 grid gap-2 text-sm">
          {linkSessionId && session.status === "pending" && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2 text-xs text-amber-950">
              Returned from identity provider — confirm consent completed, then
              enter your account identifier below.
            </p>
          )}
          {connector.connector_id === "aws-posture" &&
            awsDeployOptions.length > 0 && (
              <div className="grid gap-2">
                <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                  <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                    Deployment method
                    <select
                      value={effectiveAwsDeployMode}
                      onChange={(event) =>
                        setAwsDeployMode(event.target.value as AwsDeployMode)
                      }
                      className="rounded-lg border border-line bg-white px-3 py-2 text-sm normal-case tracking-normal text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                    >
                      {awsDeployOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label} - {option.detail}
                        </option>
                      ))}
                    </select>
                  </label>
                  {effectiveAwsDeployMode === "console" && quickCreateUrl && (
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      className="sm:mb-0"
                      onClick={() =>
                        window.open(
                          quickCreateUrl,
                          "_blank",
                          "noopener,noreferrer",
                        )
                      }
                    >
                      <ExternalLink className="h-4 w-4" />
                      Open AWS guided deploy
                    </Button>
                  )}
                </div>
                {activeAwsDeployCommand && (
                  <div className="rounded-lg border border-line bg-white p-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-xs font-black uppercase tracking-wide text-muted">
                          {effectiveAwsDeployMode === "terraform"
                            ? "Terraform deploy command"
                            : "CloudShell deploy script"}
                        </div>
                        <p className="mt-0.5 text-xs text-muted">
                          Run in the target AWS account; the final line prints
                          the role ARN.
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="default"
                        size="sm"
                        className="shrink-0"
                        onClick={() =>
                          copyDeployCommand(activeAwsDeployCommand)
                        }
                      >
                        <Copy className="h-4 w-4" />
                        {effectiveAwsDeployMode === "cloudformation"
                          ? "Copy CloudShell script"
                          : "Copy deploy command"}
                      </Button>
                    </div>
                    <details className="mt-2 text-xs text-muted">
                      <summary className="cursor-pointer list-none font-bold text-brand">
                        Preview script
                      </summary>
                      <code className="mt-2 block max-h-32 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-surface px-2 py-1.5 text-[11px] font-medium text-ink">
                        {activeAwsDeployCommand}
                      </code>
                    </details>
                  </div>
                )}
              </div>
            )}
          {session.consent_url && (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={() =>
                window.open(
                  session.consent_url!,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              <ExternalLink className="h-4 w-4" />
              Grant Azure admin consent
            </Button>
          )}
          {connector.connector_id === "gcp-posture" && session.template_url && (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={() =>
                window.open(
                  session.template_url!,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              <ExternalLink className="h-4 w-4" />
              Download Terraform template
            </Button>
          )}
          {deployCommand && connector.connector_id === "gcp-posture" && (
            <div className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              <div>Terraform deploy command</div>
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                <code className="min-w-0 whitespace-pre-wrap break-all rounded-lg border border-line bg-white px-2 py-1.5 text-xs font-medium normal-case tracking-normal text-ink">
                  {deployCommand}
                </code>
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  className="shrink-0 self-start"
                  onClick={() => copyDeployCommand(deployCommand)}
                >
                  <Copy className="h-4 w-4" />
                  Copy deploy command
                </Button>
              </div>
            </div>
          )}
          {!session.quick_create_url &&
            connector.connector_id === "aws-posture" && (
              <p className="text-xs text-muted">
                For local self-hosting, set an HTTPS{" "}
                <code>TRUSTOPS_AWS_TEMPLATE_URL</code> and{" "}
                <code>TRUSTOPS_AWS_LINK_PRINCIPAL</code> to enable one-click
                deployment. Hosted deployments can use{" "}
                <code>TRUSTOPS_PUBLIC_URL</code>. Manual template:{" "}
                <code>{session.manual_template_path}</code>
              </p>
            )}
          {connector.connector_id === "gcp-posture" &&
            !session.workload_identity_member && (
              <p className="text-xs text-muted">
                Set <code>TRUSTOPS_GCP_WIF_MEMBER</code> to include Workload
                Identity in the deploy command. Manual template:{" "}
                <code>{session.manual_template_path}</code>
              </p>
            )}
          {connector.connector_id === "aws-posture" && (
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              AWS account ID
              <input
                value={roleArn}
                onChange={(e) => {
                  setRoleArn(e.target.value);
                  setFieldError(null);
                }}
                onBlur={() => {
                  setTouched(true);
                  setFieldError(awsRoleIdentifierError(awsRoleIdentifier));
                }}
                autoComplete="off"
                aria-invalid={Boolean(showFieldError)}
                placeholder="030225640638"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="font-medium normal-case tracking-normal text-muted">
                Use the account ID when you keep the default role name. For a
                custom name, paste the Role ARN in Advanced options.
              </span>
            </label>
          )}
          {connector.connector_id === "aws-posture" && (
            <details className="text-xs text-muted">
              <summary className="cursor-pointer list-none font-black uppercase tracking-wide text-ink">
                Advanced options
              </summary>
              <div className="mt-2 grid gap-2 border-t border-line pt-2">
                <div className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Scale with StackSets or Terraform
                  <span className="font-medium normal-case tracking-normal text-muted">
                    {session.scale_strategy?.summary ||
                      "Use CloudFormation StackSets or Terraform workspaces across AWS accounts."}{" "}
                    {session.scale_strategy?.follow_up ||
                      "Bulk account import is the follow-up surface after rollout."}
                  </span>
                </div>
                <div className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Read-only IAM posture
                  <span
                    aria-label="IAM posture read-only"
                    className="font-semibold normal-case tracking-normal text-ink"
                    title="IAM posture read-only"
                  >
                    iam:ListUsers, iam:ListMFADevices, iam:ListAccessKeys,
                    iam:GetLoginProfile, iam:GetAccountPasswordPolicy,
                    iam:GetAccountSummary
                  </span>
                </div>
                {(session.external_id || session.trusted_principal) && (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {session.external_id && (
                      <label className="grid gap-1 font-black uppercase tracking-wide text-muted">
                        External ID
                        <code className="break-all rounded-lg border border-line bg-surface px-2 py-1.5 font-medium normal-case tracking-normal text-ink">
                          {session.external_id}
                        </code>
                      </label>
                    )}
                    {session.trusted_principal && (
                      <label className="grid gap-1 font-black uppercase tracking-wide text-muted">
                        Trusted principal
                        <code className="break-all rounded-lg border border-line bg-surface px-2 py-1.5 font-medium normal-case tracking-normal text-ink">
                          {session.trusted_principal}
                        </code>
                      </label>
                    )}
                  </div>
                )}
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Role name
                  <input
                    value={awsRoleName}
                    onChange={(event) =>
                      setAwsRoleName(sanitizeAwsRoleName(event.target.value))
                    }
                    placeholder={AWS_ROLE_NAME}
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm normal-case tracking-normal text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Use a custom Role ARN
                  <input
                    value={customRoleArn}
                    onChange={(event) => {
                      setCustomRoleArn(event.target.value);
                      setFieldError(null);
                    }}
                    onBlur={() => {
                      setTouched(true);
                      setFieldError(awsRoleIdentifierError(awsRoleIdentifier));
                    }}
                    autoComplete="off"
                    aria-invalid={Boolean(showFieldError)}
                    placeholder="arn:aws:iam::123456789012:role/CustomTrustOpsRole"
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm normal-case tracking-normal text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
              </div>
            </details>
          )}
          {connector.connector_id === "azure-posture" && (
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              Azure subscription ID
              <input
                value={subscriptionId}
                onChange={(e) => {
                  setSubscriptionId(
                    sanitizeAzureSubscriptionId(e.target.value),
                  );
                  setFieldError(null);
                }}
                onBlur={() => {
                  setTouched(true);
                  setFieldError(azureSubscriptionIdError(subscriptionId));
                }}
                autoComplete="off"
                aria-invalid={Boolean(showFieldError)}
                placeholder="00000000-0000-0000-0000-000000000000"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
          )}
          {connector.connector_id === "gcp-posture" && (
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              GCP project ID
              <input
                value={projectId}
                onChange={(e) => {
                  setProjectId(sanitizeGcpProjectId(e.target.value));
                  setFieldError(null);
                }}
                onBlur={() => {
                  setTouched(true);
                  setFieldError(gcpProjectIdError(projectId));
                }}
                autoComplete="off"
                aria-invalid={Boolean(showFieldError)}
                placeholder="my-gcp-project"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
          )}
          {showFieldError && (
            <p className="text-xs font-semibold text-rose-700">
              {showFieldError}
            </p>
          )}
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={finish}
            disabled={!canComplete}
          >
            {complete.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Link2 className="h-4 w-4" />
            )}{" "}
            {connector.connector_id === "aws-posture"
              ? "Save AWS account"
              : "Save cloud connection"}
          </Button>
        </div>
      )}
    </section>
  );
}
