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

  const begin = async () => {
    setFieldError(null);
    setTouched(false);
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
    if (!session?.deploy_command) return;
    try {
      await navigator.clipboard.writeText(session.deploy_command);
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
          {session.quick_create_url && (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={() =>
                window.open(
                  session.quick_create_url!,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              <ExternalLink className="h-4 w-4" />
              Deploy read-only role
            </Button>
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
          {connector.connector_id === "gcp-posture" &&
            session.deploy_command && (
              <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                Terraform deploy command
                <div className="flex gap-2">
                  <code className="min-w-0 flex-1 break-all rounded-lg border border-line bg-white px-2 py-1.5 text-xs text-ink">
                    {session.deploy_command}
                  </code>
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    className="shrink-0"
                    onClick={copyDeployCommand}
                  >
                    <Copy className="h-4 w-4" />
                    Copy
                  </Button>
                </div>
              </label>
            )}
          {session.template_url &&
            !session.quick_create_url &&
            connector.connector_id === "aws-posture" && (
              <p className="text-xs text-muted">
                Set <code>TRUSTOPS_PUBLIC_URL</code> and{" "}
                <code>TRUSTOPS_AWS_LINK_PRINCIPAL</code> for a one-click stack
                URL. Manual template:{" "}
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
