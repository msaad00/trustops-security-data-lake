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
  awsRoleArnError,
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
    return "Deploy a read-only role that trusts this TrustOps runtime, then verify assume-role access. Account ID identifies the target; it does not grant access.";
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
  const [subscriptionId, setSubscriptionId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const [awsRoleName, setAwsRoleName] = useState(AWS_ROLE_NAME);
  const [awsDeployMode, setAwsDeployMode] = useState<"console" | "cli">(
    "console",
  );

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
        roleArn,
        subscriptionId,
        projectId,
      }),
    [connector.connector_id, projectId, roleArn, subscriptionId],
  );

  const canComplete =
    Boolean(session?.session_id) &&
    !complete.isPending &&
    validationError === null;
  const deployCommand = useMemo(() => {
    if (!session) return null;
    if (connector.connector_id === "aws-posture") {
      return awsDeployCommand(session, awsRoleName);
    }
    return session.deploy_command ?? null;
  }, [awsRoleName, connector.connector_id, session]);
  const quickCreateUrl = useMemo(() => {
    if (!session || connector.connector_id !== "aws-posture") {
      return session?.quick_create_url ?? null;
    }
    return awsQuickCreateUrl(session, awsRoleName);
  }, [awsRoleName, connector.connector_id, session]);
  const effectiveAwsDeployMode =
    awsDeployMode === "console" && !quickCreateUrl && deployCommand
      ? "cli"
      : awsDeployMode;

  const begin = async () => {
    setFieldError(null);
    setTouched(false);
    setAwsRoleName(AWS_ROLE_NAME);
    setAwsDeployMode("console");
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
      roleArn,
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
          connector.connector_id === "aws-posture" ? roleArn.trim() : undefined,
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

  const copyDeployCommand = async () => {
    if (!deployCommand) return;
    try {
      await navigator.clipboard.writeText(deployCommand);
      onToast("Deploy command copied");
    } catch {
      onToast("Could not copy deploy command");
    }
  };

  const showFieldError =
    fieldError ?? (touched && validationError ? validationError : null);

  if (!supportsCloudLink(connector.connector_id)) return null;

  return (
    <section className="rounded-lg border border-brand/30 bg-brand/5 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 text-brand" />
        <div className="text-xs font-black uppercase tracking-wide text-ink">
          Cloud account linking
        </div>
        <Badge tone="info">Guided setup</Badge>
        <Badge tone="ready">Read-only access</Badge>
        <Badge>No long-lived keys</Badge>
        <Badge
          tone={connector.connector_id === "aws-posture" ? "ready" : "default"}
        >
          {connector.connector_id === "aws-posture"
            ? "Console or CLI"
            : "Provider template path"}
        </Badge>
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
          {session.external_id && (
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              External ID
              <code className="break-all rounded-lg border border-line bg-white px-2 py-1.5 text-xs text-ink">
                {session.external_id}
              </code>
            </label>
          )}
          {connector.connector_id === "aws-posture" &&
            (quickCreateUrl || deployCommand) && (
              <div className="grid gap-2">
                <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
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
                  <div className="self-end rounded-lg border border-line bg-white px-3 py-2 text-xs font-black uppercase tracking-wide text-muted">
                    <span className="block text-[10px]">Grant set</span>
                    <span className="text-ink">IAM posture read-only</span>
                  </div>
                </div>
                <div
                  aria-label="AWS deployment method"
                  className="grid grid-cols-2 rounded-lg border border-line bg-white p-1"
                  role="tablist"
                >
                  {quickCreateUrl && (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={effectiveAwsDeployMode === "console"}
                      className={`rounded-md px-2 py-1.5 text-xs font-black uppercase tracking-wide ${
                        effectiveAwsDeployMode === "console"
                          ? "bg-brand text-white"
                          : "text-muted hover:bg-slate-50"
                      }`}
                      onClick={() => setAwsDeployMode("console")}
                    >
                      AWS Console
                    </button>
                  )}
                  {deployCommand && (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={effectiveAwsDeployMode === "cli"}
                      className={`rounded-md px-2 py-1.5 text-xs font-black uppercase tracking-wide ${
                        effectiveAwsDeployMode === "cli"
                          ? "bg-brand text-white"
                          : "text-muted hover:bg-slate-50"
                      }`}
                      onClick={() => setAwsDeployMode("cli")}
                    >
                      CLI script
                    </button>
                  )}
                </div>
                {effectiveAwsDeployMode === "console" && quickCreateUrl && (
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
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
                {effectiveAwsDeployMode === "cli" && deployCommand && (
                  <div className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                    <div>AWS CLI deploy command</div>
                    <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                      <code className="min-w-0 max-h-44 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-white px-2 py-1.5 text-xs font-medium normal-case tracking-normal text-ink">
                        {deployCommand}
                      </code>
                      <Button
                        type="button"
                        variant="default"
                        size="sm"
                        className="shrink-0 self-start"
                        onClick={copyDeployCommand}
                      >
                        <Copy className="h-4 w-4" />
                        Copy deploy command
                      </Button>
                    </div>
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
                  onClick={copyDeployCommand}
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
              AWS role ARN
              <input
                value={roleArn}
                onChange={(e) => {
                  setRoleArn(e.target.value);
                  setFieldError(null);
                }}
                onBlur={() => {
                  setTouched(true);
                  setFieldError(awsRoleArnError(roleArn));
                }}
                autoComplete="off"
                aria-invalid={Boolean(showFieldError)}
                placeholder="arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
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
            Save role connection
          </Button>
        </div>
      )}
    </section>
  );
}
