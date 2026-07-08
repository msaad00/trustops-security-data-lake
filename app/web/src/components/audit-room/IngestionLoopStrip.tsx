"use client";

import Link from "next/link";
import { Activity, ArrowRight, Clock3, History } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { KpiTile } from "@/components/ui/KpiTile";
import { useEvalRuns, useIngestionStatus } from "@/lib/api/hooks";
import { shortDate } from "@/lib/utils";

function toneForState(state?: string): "ready" | "attention" | "critical" {
  if (state === "active") return "ready";
  if (state === "error") return "critical";
  return "attention";
}

export function IngestionLoopStrip() {
  const ingestion = useIngestionStatus();
  const evalRuns = useEvalRuns(3);
  const summary = ingestion.data?.summary;
  const scale = ingestion.data?.scale;
  const health = ingestion.data?.health;

  return (
    <QueryState queries={[ingestion, evalRuns]} label="ingestion loop">
      {ingestion.data && (
        <Card>
          <CardContent className="grid gap-4 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Activity className="h-4 w-4 text-brand" />
                  <span className="text-sm font-black text-ink">
                    Continuous ingestion loop
                  </span>
                  <Badge tone={toneForState(ingestion.data.state)}>
                    {ingestion.data.state.replace(/_/g, " ")}
                  </Badge>
                  {scale?.eval_overdue ? (
                    <Badge tone="critical">eval overdue</Badge>
                  ) : null}
                </div>
                <p className="mt-1 text-xs leading-5 text-muted">
                  Connector syncs land raw evidence; lake eval materializes
                  posture on a separate schedule — same split loop as managed
                  GRC platforms.
                </p>
              </div>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
              >
                Source health
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <KpiTile
                label="Enabled connectors"
                value={`${summary?.enabled_connectors ?? 0}/${summary?.connector_count ?? 0}`}
                detail={`${summary?.failed_connectors ?? 0} failed · ${summary?.never_synced_connectors ?? 0} never synced`}
                tone={
                  (summary?.failed_connectors ?? 0) > 0
                    ? "attention"
                    : "default"
                }
              />
              <KpiTile
                label="Evidence rows"
                value={(summary?.evidence_count ?? 0).toLocaleString()}
                detail={`${summary?.source_count ?? 0} sources · ${summary?.stale_evidence ?? 0} stale`}
              />
              <KpiTile
                label="Connector health"
                value={
                  health
                    ? `${health.summary.healthy}/${health.summary.enabled}`
                    : "—"
                }
                detail={
                  health
                    ? `${health.summary.silent} silent · ${health.summary.degraded} degraded`
                    : "freshness SLO rollups"
                }
                tone={
                  health && health.summary.unhealthy > 0
                    ? "attention"
                    : "default"
                }
              />
              <KpiTile
                label="Last eval"
                value={
                  scale?.latest_eval?.occurred_at
                    ? shortDate(scale.latest_eval.occurred_at)
                    : "never"
                }
                detail={`${scale?.latest_eval?.mode ?? "—"} · ${scale?.latest_eval?.result ?? "pending"}`}
              />
              <KpiTile
                label="Next eval"
                value={
                  scale?.next_eval_at
                    ? shortDate(scale.next_eval_at)
                    : (scale?.eval_schedule ?? "—")
                }
                detail={
                  scale?.eval_overdue
                    ? "overdue — scheduler will fire on next tick"
                    : scale?.eval_schedule
                      ? `cadence ${scale.eval_schedule}`
                      : "no eval schedule configured"
                }
                tone={scale?.eval_overdue ? "critical" : "default"}
              />
            </div>

            {(evalRuns.data ?? []).length > 0 && (
              <div className="rounded-lg border border-line bg-panel p-3">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-muted">
                  <History className="h-3.5 w-3.5" />
                  Recent eval runs
                </div>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {evalRuns.data?.map((run, index) => (
                    <div
                      key={`${run.occurred_at}-${index}`}
                      className="rounded-md border border-line bg-white px-2.5 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-bold text-ink">
                          {run.mode}
                        </span>
                        <Badge
                          tone={run.result === "ok" ? "ready" : "critical"}
                        >
                          {run.result}
                        </Badge>
                      </div>
                      <div className="mt-1 flex items-center gap-1 text-[11px] text-muted">
                        <Clock3 className="h-3 w-3" />
                        {shortDate(run.occurred_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
