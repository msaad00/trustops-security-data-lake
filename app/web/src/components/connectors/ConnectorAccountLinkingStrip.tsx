"use client";

import Link from "next/link";
import { ArrowRight, Link2 } from "lucide-react";
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

const RECOMMENDED_IDS = [
  "aws-posture",
  "azure-posture",
  "gcp-posture",
  "snowflake-evidence-lake",
  "github-security",
  "gitlab-security",
  "okta-identity",
] as const;

function accountStatus(connector: ConnectorView | undefined) {
  if (!connector || connector.state !== "enabled") {
    return { label: "Not linked", tone: "attention" as const };
  }
  const success = connector.last_successful_sync ?? connector.last_sync;
  if (success?.result === "ok") {
    return { label: "Live ingestion", tone: "ready" as const };
  }
  if (connector.last_probe?.result === "ok") {
    return { label: "Connected", tone: "info" as const };
  }
  if (
    connector.last_sync?.result === "error" ||
    connector.last_probe?.result === "error"
  ) {
    return { label: "Error", tone: "critical" as const };
  }
  return { label: "Enabled", tone: "info" as const };
}

function AccountCard({ connector }: { connector: ConnectorView | undefined }) {
  const connectorId = connector?.connector_id ?? "unknown";
  const status = accountStatus(connector);
  const evidenceCount =
    connector?.last_successful_sync?.evidence_count ??
    connector?.last_sync?.evidence_count ??
    0;
  const label =
    connector?.vendor ?? connector?.name ?? connectorId.replace(/-/g, " ");

  return (
    <Link
      href={`/connectors/?connect=${connectorId}`}
      className="group flex min-h-[128px] flex-col overflow-hidden rounded-xl border border-line bg-white transition-all hover:border-brand hover:shadow-card"
    >
      <div className="flex flex-1 items-start gap-3 p-4">
        <ConnectorMark
          connectorId={connectorId}
          name={connector?.name}
          category={connector?.category}
          size="lg"
        />
        <div className="min-w-0 flex-1 overflow-hidden">
          <div className="flex items-start justify-between gap-2">
            <span className="truncate text-sm font-black text-ink">
              {label}
            </span>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone={status.tone}>{status.label}</Badge>
            {evidenceCount > 0 && (
              <Badge tone="ready">{evidenceCount} evidence</Badge>
            )}
          </div>
        </div>
      </div>
      {connector?.setup_hint && (
        <p className="line-clamp-2 border-t border-line bg-panel/40 px-4 py-2.5 text-[11px] leading-4 text-muted">
          {connector.setup_hint}
        </p>
      )}
    </Link>
  );
}

export function ConnectorAccountLinkingStrip() {
  const connectors = useConnectors();
  const byId = new Map(
    (connectors.data ?? []).map((row) => [row.connector_id, row]),
  );
  const linked = RECOMMENDED_IDS.filter(
    (id) => byId.get(id)?.state === "enabled",
  ).length;
  const ingesting = RECOMMENDED_IDS.filter((id) => {
    const row = byId.get(id);
    const success = row?.last_successful_sync ?? row?.last_sync;
    return success?.result === "ok";
  }).length;

  return (
    <QueryState queries={[connectors]} label="account linking">
      <Card className="overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Link2 className="h-4 w-4 text-brand" />
              <CardTitle className="text-base">Link accounts</CardTitle>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-bold text-muted">
              <span className="rounded-full border border-line bg-white px-2.5 py-1">
                {linked}/{RECOMMENDED_IDS.length} linked
              </span>
              <span className="rounded-full border border-line bg-white px-2.5 py-1">
                {ingesting} ingesting
              </span>
            </div>
          </div>
          <CardDescription>
            Read-only cloud, identity, and warehouse sources.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {RECOMMENDED_IDS.map((id) => (
            <AccountCard key={id} connector={byId.get(id)} />
          ))}
        </CardContent>
      </Card>
    </QueryState>
  );
}
