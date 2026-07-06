"use client";

import { Activity, AlertTriangle, Database, Plug } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { useIngestionStatus } from "@/lib/api/hooks";

const toneForState = (state: string) => {
  if (state === "active") return "ready" as const;
  if (state === "error") return "critical" as const;
  if (state === "attention_required" || state === "needs_configuration")
    return "attention" as const;
  return "default" as const;
};

export function ConnectorIngestionStrip() {
  const ingestion = useIngestionStatus();

  return (
    <QueryState queries={[ingestion]} label="ingestion status">
      {ingestion.data && (
        <Card>
          <CardContent className="grid gap-3 p-4 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-panel text-brand ring-1 ring-line">
              <Activity className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-black text-ink">
                  Live ingestion
                </span>
                <Badge tone={toneForState(ingestion.data.state)}>
                  {ingestion.data.state.replace(/_/g, " ")}
                </Badge>
              </div>
              <p className="mt-1 text-xs leading-5 text-muted">
                {ingestion.data.summary.enabled_connectors} of{" "}
                {ingestion.data.summary.connector_count} connectors enabled ·{" "}
                {ingestion.data.summary.evidence_count.toLocaleString()}{" "}
                evidence rows
                {ingestion.data.scale?.mode
                  ? ` · ${ingestion.data.scale.mode.replace(/_/g, " ")}`
                  : ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px] font-bold text-muted">
                <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5">
                  <Plug className="h-3 w-3" />
                  {ingestion.data.summary.failed_connectors} failed
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5">
                  <AlertTriangle className="h-3 w-3" />
                  {ingestion.data.summary.never_synced_connectors} never synced
                </span>
                {(ingestion.data.summary.silent_connectors ?? 0) > 0 && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-rose-700">
                    <AlertTriangle className="h-3 w-3" />
                    {ingestion.data.summary.silent_connectors} silent
                  </span>
                )}
                <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5">
                  <Database className="h-3 w-3" />
                  {ingestion.data.summary.evidence_count} ingested
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
