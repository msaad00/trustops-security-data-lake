"use client";

import Link from "next/link";
import { ArrowRight, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useInsightsRemediation } from "@/lib/api/hooks";

function slaTone(pct: number | null | undefined) {
  if (pct == null) return "default" as const;
  if (pct >= 95) return "ready" as const;
  if (pct >= 80) return "attention" as const;
  return "critical" as const;
}

export function InsightsRemediationStrip() {
  const remediation = useInsightsRemediation();
  const data = remediation.data;
  if (!data) return null;

  const slaLabel =
    data.sla_attainment_pct != null
      ? `${Math.round(data.sla_attainment_pct)}% SLA`
      : "SLA n/a";
  const mttrLabel =
    data.mttr_hours != null
      ? `${data.mttr_hours.toFixed(1)}h MTTR`
      : "MTTR n/a";

  return (
    <Card className="h-full border-line bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <TrendingUp className="h-5 w-5 text-brand" />
          <div>
            <div className="text-xs font-black uppercase tracking-wider text-muted">
              Remediation insights
            </div>
            <div className="text-sm font-bold text-ink">
              {data.open} open · {data.overdue} overdue · {mttrLabel}
            </div>
          </div>
          <Badge tone={slaTone(data.sla_attainment_pct)}>{slaLabel}</Badge>
          {data.overdue > 0 && (
            <span className="text-xs text-muted">
              {data.overdue} task{data.overdue === 1 ? "" : "s"} past SLA due
              date
            </span>
          )}
        </div>
        <Link
          href="/insights"
          className="inline-flex items-center gap-1 text-sm font-extrabold text-brand hover:underline"
        >
          View insights
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
