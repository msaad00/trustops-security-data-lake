"use client";

import Link from "next/link";
import { ArrowRight, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useEvidenceFreshnessSummary } from "@/lib/api/hooks";

function stateTone(state?: string) {
  if (state === "healthy") return "ready" as const;
  if (state === "action_required") return "attention" as const;
  return "critical" as const;
}

export function EvidenceFreshnessStrip() {
  const summary = useEvidenceFreshnessSummary();
  const data = summary.data;
  if (!data) return null;

  const breachTotal =
    data.stale_count + data.expired_count + data.missing_count;

  return (
    <Card className="h-full border-line bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <Clock className="h-5 w-5 text-brand" />
          <div>
            <div className="text-xs font-black uppercase tracking-wider text-muted">
              Evidence freshness
            </div>
            <div className="text-sm font-bold text-ink">
              {data.fresh_rate_pct}% fresh · {data.sla_breach_count} SLA breach
              {data.sla_breach_count === 1 ? "" : "es"}
            </div>
          </div>
          <Badge tone={stateTone(data.state)}>
            {data.state.replace(/_/g, " ")}
          </Badge>
          {breachTotal > 0 && (
            <span className="text-xs text-muted">
              {data.stale_count} stale · {data.expired_count} expired ·{" "}
              {data.missing_count} missing
            </span>
          )}
        </div>
        <Link
          href="/evidence"
          className="inline-flex items-center gap-1 text-sm font-extrabold text-brand hover:underline"
        >
          Review evidence
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
