"use client";

import Link from "next/link";
import { AlertTriangle, Clock, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import {
  useEscalateStaleEvidenceMutation,
  useEvidenceFreshnessSummary,
} from "@/lib/api/hooks";
import { notify } from "@/lib/toast";

export function EvidenceFreshnessSlaPanel() {
  const summary = useEvidenceFreshnessSummary();
  const escalate = useEscalateStaleEvidenceMutation();

  const escalateTasks = async () => {
    try {
      const result = await escalate.mutateAsync(10);
      notify.success(
        `Created ${result.created_count} remediation task(s) for SLA breaches`,
      );
    } catch (err) {
      notify.error(String((err as Error).message));
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-brand" />
            Evidence freshness SLA
          </CardTitle>
          <CardDescription>
            Per-connector SLO windows flag stale, expired, and missing proof —
            escalate breaches into owner tasks for audit prep.
          </CardDescription>
        </div>
        <Button
          variant="primary"
          size="sm"
          disabled={escalate.isPending || (summary.data?.sla_breach_count ?? 0) === 0}
          onClick={escalateTasks}
        >
          {escalate.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Escalate breaches
        </Button>
      </CardHeader>
      <CardContent className="grid gap-3">
        <QueryState queries={[summary]} label="freshness SLA">
          {summary.data && (
            <>
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-line bg-panel p-3">
                  <div className="text-[10px] font-black uppercase text-muted">
                    Fresh rate
                  </div>
                  <div className="mt-1 text-2xl font-black text-ink">
                    {summary.data.fresh_rate_pct}%
                  </div>
                </div>
                <div className="rounded-lg border border-line bg-panel p-3">
                  <div className="text-[10px] font-black uppercase text-muted">
                    SLA breaches
                  </div>
                  <div className="mt-1 text-2xl font-black text-ink">
                    {summary.data.sla_breach_count}
                  </div>
                </div>
                <div className="rounded-lg border border-line bg-panel p-3">
                  <div className="text-[10px] font-black uppercase text-muted">
                    Sources at risk
                  </div>
                  <div className="mt-1 text-2xl font-black text-ink">
                    {summary.data.sources_needing_action}
                  </div>
                </div>
                <div className="rounded-lg border border-line bg-panel p-3">
                  <div className="text-[10px] font-black uppercase text-muted">
                    Tracked rows
                  </div>
                  <div className="mt-1 text-2xl font-black text-ink">
                    {summary.data.total}
                  </div>
                </div>
              </div>

              {summary.data.sla_breach_count > 0 && (
                <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
                  <p>
                    {summary.data.stale_count} stale · {summary.data.expired_count}{" "}
                    expired · {summary.data.missing_count} missing. Review in{" "}
                    <Link href="/evidence" className="font-bold underline">
                      Evidence
                    </Link>{" "}
                    or escalate to remediation owners.
                  </p>
                </div>
              )}

              <div className="grid gap-2">
                {(summary.data.sources ?? []).slice(0, 6).map((row) => (
                  <div
                    key={row.source}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-white px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-black text-ink">
                          {row.source}
                        </span>
                        <Badge
                          tone={
                            row.state === "action_required" ? "attention" : "ready"
                          }
                        >
                          {row.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted">
                        {row.evidence_count} rows · SLO {row.freshness_slo_minutes}m
                      </p>
                    </div>
                    <span className="text-xs font-bold text-muted">
                      {row.stale_count + row.expired_count + row.missing_count}{" "}
                      breach(es)
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </QueryState>
      </CardContent>
    </Card>
  );
}
