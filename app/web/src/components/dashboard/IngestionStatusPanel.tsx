import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  FileCheck2,
  RefreshCw,
} from "lucide-react";
import type { IngestionStatus } from "@/lib/api/types";
import { shortDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function toneForState(state?: string): "ready" | "attention" | "critical" {
  if (state === "active") return "ready";
  if (state === "error") return "critical";
  return "attention";
}

function labelForState(state?: string) {
  if (state === "active") return "Live ingestion healthy";
  if (state === "error") return "Ingestion needs repair";
  if (state === "needs_configuration") return "Connect a source";
  if (state === "needs_data") return "Run initial sync";
  return "Ingestion needs review";
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2">
      <div className="text-[10px] font-black uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className="mt-1 text-xl font-black leading-none text-ink">
        {value}
      </div>
      <div className="mt-1 truncate text-xs text-muted">{detail}</div>
    </div>
  );
}

export function IngestionStatusPanel({
  status,
}: {
  status: IngestionStatus | undefined;
}) {
  const summary = status?.summary;
  const action = status?.recommended_actions?.[0];
  const visibleConnectors =
    status?.connectors
      ?.filter(
        (connector) =>
          connector.state === "enabled" ||
          connector.latest_sync.result === "error" ||
          connector.freshness_state === "stale",
      )
      .slice(0, 4) ?? [];
  const proofReady = Boolean(status?.proof?.proof_pack_exists);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-brand" />
            Live ingestion
          </CardTitle>
          <CardDescription>
            Source sync health, evidence coverage, and proof-pack readiness.
          </CardDescription>
        </div>
        <Badge tone={toneForState(status?.state)}>
          {labelForState(status?.state)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-2 md:grid-cols-4">
          <Metric
            label="Evidence"
            value={summary?.evidence_count ?? 0}
            detail={`${summary?.source_count ?? 0} sources`}
          />
          <Metric
            label="Connectors"
            value={`${summary?.enabled_connectors ?? 0}/${summary?.connector_count ?? 0}`}
            detail={`${summary?.failed_connectors ?? 0} failed`}
          />
          <Metric
            label="Freshness"
            value={summary?.stale_evidence ?? 0}
            detail="stale or expired"
          />
          <Metric
            label="Proof pack"
            value={proofReady ? "ready" : "missing"}
            detail={status?.proof?.scenario ?? "not run"}
          />
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0 rounded-lg border border-line">
            <div className="flex items-center justify-between border-b border-line px-3 py-2">
              <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-muted">
                <Database className="h-3.5 w-3.5" />
                Active sources
              </div>
              <span className="text-xs font-semibold text-muted">
                {status?.integrity?.ok === true ? "integrity ok" : "verify"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 p-3">
              {(status?.sources ?? []).length > 0 ? (
                status?.sources.map((source) => (
                  <span
                    key={source.source}
                    className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-2.5 py-1 text-xs font-bold text-slate-600"
                  >
                    {source.source}
                    <strong className="text-ink">{source.evidence_count}</strong>
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted">
                  No normalized evidence has landed yet.
                </span>
              )}
            </div>
            <div className="divide-y divide-line border-t border-line">
              {visibleConnectors.length > 0 ? (
                visibleConnectors.map((connector) => (
                  <div
                    key={connector.connector_id}
                    className="grid gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_160px_110px]"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-ink">
                        {connector.name}
                      </div>
                      <div className="truncate text-xs text-muted">
                        {connector.connector_id}
                      </div>
                    </div>
                    <div className="text-xs text-muted">
                      last sync {shortDate(connector.last_sync_at ?? undefined)}
                    </div>
                    <Badge
                      tone={
                        connector.latest_sync.result === "error"
                          ? "critical"
                          : connector.freshness_state === "fresh"
                            ? "ready"
                            : "attention"
                      }
                    >
                      {connector.latest_sync.result ?? connector.freshness_state}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="px-3 py-3 text-sm text-muted">
                  Enable a read-only connector or land existing-lake evidence.
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-lg border border-line bg-panel p-3">
              <div className="flex items-center gap-2 text-sm font-black text-ink">
                {proofReady ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <FileCheck2 className="h-4 w-4 text-amber-600" />
                )}
                Reviewer proof
              </div>
              <p className="mt-2 text-sm leading-5 text-muted">
                {proofReady
                  ? `${status?.proof?.evidence_count ?? 0} rows in latest proof pack across ${(status?.proof?.sources ?? []).length} sources.`
                  : "Run the live-cloud posture scenario after the first sync to create a proof pack."}
              </p>
            </div>
            <div className="rounded-lg border border-line bg-white p-3">
              <div className="flex items-center gap-2 text-sm font-black text-ink">
                {action?.priority === "p0" ? (
                  <AlertTriangle className="h-4 w-4 text-rose-600" />
                ) : (
                  <RefreshCw className="h-4 w-4 text-brand" />
                )}
                Next action
              </div>
              <p className="mt-2 text-sm leading-5 text-muted">
                {action?.reason ?? "No ingestion action is required right now."}
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
