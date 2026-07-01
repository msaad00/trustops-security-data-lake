"use client";

import Link from "next/link";
import { Link2 } from "lucide-react";
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
  "okta-identity",
] as const;

function accountStatus(connector: ConnectorView | undefined) {
  if (!connector || connector.state !== "enabled") {
    return { label: "not linked", tone: "attention" as const };
  }
  const success = connector.last_successful_sync ?? connector.last_sync;
  if (success?.result === "ok") {
    return { label: "live ingestion", tone: "ready" as const };
  }
  if (connector.last_probe?.result === "ok") {
    return { label: "connected", tone: "info" as const };
  }
  if (
    connector.last_sync?.result === "error" ||
    connector.last_probe?.result === "error"
  ) {
    return { label: "error", tone: "critical" as const };
  }
  return { label: "enabled", tone: "info" as const };
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
      className="grid gap-2 rounded-xl border border-line bg-white p-3 transition-colors hover:border-brand hover:shadow-card"
    >
      <div className="flex flex-wrap items-center gap-2">
        <ConnectorMark
          connectorId={connectorId}
          name={connector?.name}
          category={connector?.category}
          size="sm"
        />
        <span className="truncate text-sm font-black text-ink">{label}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={status.tone}>{status.label}</Badge>
        {evidenceCount > 0 && (
          <Badge tone="ready">{evidenceCount} evidence</Badge>
        )}
      </div>
      {connector?.setup_hint && (
        <p className="line-clamp-2 text-[11px] leading-4 text-muted">
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
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <Link2 className="h-4 w-4 text-brand" />
            <CardTitle>Link accounts</CardTitle>
          </div>
          <CardDescription>
            Connect read-only cloud, identity, and evidence-lake sources first —
            the same onboarding path managed GRC tools use for account linking.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex flex-wrap gap-2 text-xs font-bold text-muted">
            <span className="rounded-full border border-line bg-white px-2.5 py-1">
              {linked}/{RECOMMENDED_IDS.length} linked
            </span>
            <span className="rounded-full border border-line bg-white px-2.5 py-1">
              {ingesting} ingesting
            </span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {RECOMMENDED_IDS.map((id) => (
              <AccountCard key={id} connector={byId.get(id)} />
            ))}
          </div>
        </CardContent>
      </Card>
    </QueryState>
  );
}
