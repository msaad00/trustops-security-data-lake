"use client";

import { useEffect, useState } from "react";
import { Copy, ExternalLink, Link2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useCloudLinkCompleteMutation,
  useCloudLinkStartMutation,
} from "@/lib/api/hooks";
import type { CloudLinkSession } from "@/lib/api/client";
import type { ConnectorView } from "@/lib/api/types";

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
    return "Launch the read-only CloudFormation stack, then enter your AWS account ID to stage the assume-role connector.";
  }
  if (connectorId === "azure-posture") {
    return "Grant admin consent for the TrustOps Azure app, then enter the subscription ID to stage the connector.";
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
  const [accountId, setAccountId] = useState("");
  const [subscriptionId, setSubscriptionId] = useState("");
  const [projectId, setProjectId] = useState("");

  useEffect(() => {
    if (!linkSessionId || session?.session_id === linkSessionId) return;
    setSession((prev) =>
      prev
        ? { ...prev, session_id: linkSessionId, status: "consented" }
        : {
            session_id: linkSessionId,
            connector_id: connector.connector_id,
            status: "consented",
          },
    );
  }, [connector.connector_id, linkSessionId, session?.session_id]);

  const begin = async () => {
    try {
      const row = await start.mutateAsync({
        id: connector.connector_id,
        publicUrl:
          typeof window !== "undefined" ? window.location.origin : undefined,
      });
      setSession(row);
      onToast("Cloud link session started");
    } catch (err) {
      onToast(`Cloud link failed: ${(err as Error).message}`);
    }
  };

  const finish = async () => {
    if (!session?.session_id) return;
    try {
      const result = await complete.mutateAsync({
        id: connector.connector_id,
        sessionId: session.session_id,
        accountId:
          connector.connector_id === "aws-posture" ? accountId : undefined,
        subscriptionId:
          connector.connector_id === "azure-posture"
            ? subscriptionId
            : undefined,
        projectId:
          connector.connector_id === "gcp-posture" ? projectId : undefined,
      });
      const creds = (result.configure?.credentials ?? {}) as Record<
        string,
        string
      >;
      onLinked(creds);
      onToast("Account linked — credentials staged for test connection");
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

  if (!supportsCloudLink(connector.connector_id)) return null;

  return (
    <section className="rounded-xl border border-brand/30 bg-brand/5 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 text-brand" />
        <div className="text-xs font-black uppercase tracking-wide text-ink">
          One-click cloud linking
        </div>
        <Badge tone="info">OAuth link</Badge>
      </div>
      <p className="mt-2 text-xs font-semibold text-muted">
        {linkDescription(connector.connector_id)}
      </p>
      {!session ? (
        <Button
          type="button"
          variant="primary"
          className="mt-3"
          onClick={begin}
          disabled={start.isPending}
        >
          {start.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="h-4 w-4" />
          )}{" "}
          Start cloud linking
        </Button>
      ) : (
        <div className="mt-3 grid gap-3 text-sm">
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
              onClick={() =>
                window.open(
                  session.quick_create_url!,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              <ExternalLink className="h-4 w-4" />
              Launch AWS CloudFormation
            </Button>
          )}
          {session.consent_url && (
            <Button
              type="button"
              variant="default"
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
              AWS account ID
              <input
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                placeholder="123456789012"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
          )}
          {connector.connector_id === "azure-posture" && (
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              Azure subscription ID
              <input
                value={subscriptionId}
                onChange={(e) => setSubscriptionId(e.target.value)}
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
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="my-gcp-project"
                className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
          )}
          <Button
            type="button"
            variant="primary"
            onClick={finish}
            disabled={complete.isPending}
          >
            {complete.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Link2 className="h-4 w-4" />
            )}{" "}
            Complete account linking
          </Button>
        </div>
      )}
    </section>
  );
}
