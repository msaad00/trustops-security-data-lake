"use client";

import { useInsightsRemediation } from "@/lib/api/hooks";
import { KpiTile } from "@/components/ui/KpiTile";

function slaTone(pct: number | null | undefined): "ready" | "attention" | "critical" | "default" {
  if (pct == null) return "default";
  if (pct >= 95) return "ready";
  if (pct >= 80) return "attention";
  return "critical";
}

export function RemediationSlaStrip() {
  const remediation = useInsightsRemediation();
  const ins = remediation.data;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Open remediation"
        value={ins ? String(ins.open) : "—"}
        detail="Tasks tied to control gaps"
        tone={ins && ins.open > 10 ? "attention" : "default"}
      />
      <KpiTile
        label="Overdue"
        value={ins ? String(ins.overdue) : "—"}
        detail="Past SLA due date"
        tone={ins && ins.overdue > 0 ? "critical" : "default"}
      />
      <KpiTile
        label="MTTR"
        value={ins?.mttr_hours != null ? `${ins.mttr_hours.toFixed(1)} h` : "—"}
        detail="Mean time to resolve closed tasks"
        tone={
          ins?.mttr_hours != null && ins.mttr_hours > 72 ? "attention" : "default"
        }
      />
      <KpiTile
        label="SLA attainment"
        value={
          ins?.sla_attainment_pct != null
            ? `${Math.round(ins.sla_attainment_pct)}%`
            : "—"
        }
        detail={`${ins?.sla_eligible_count ?? 0} SLA-eligible tasks`}
        tone={slaTone(ins?.sla_attainment_pct)}
      />
    </div>
  );
}
