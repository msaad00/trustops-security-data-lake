"use client";

import { AlertCircle, CheckCircle2, ClipboardList } from "lucide-react";
import type { ControlTest } from "@/lib/api/types";
import { KpiTile } from "@/components/ui/KpiTile";

function countByResult(rows: ControlTest[], result: string) {
  return rows.filter((row) => row.result === result).length;
}

export function ControlMonitoringSummary({ rows }: { rows: ControlTest[] }) {
  const passed = countByResult(rows, "pass");
  const failed = countByResult(rows, "fail");
  const error = countByResult(rows, "error");
  const total = rows.length;
  const passRate = total > 0 ? Math.round((passed / total) * 100) : 0;

  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Tests passing"
        value={`${passRate}%`}
        detail={`${passed} of ${total} control tests`}
        tone={failed > 0 || error > 0 ? "attention" : "ready"}
        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
      />
      <KpiTile
        label="Failed tests"
        value={failed}
        detail={failed > 0 ? "Assign owners and remediate" : "No failing tests"}
        tone={failed > 0 ? "critical" : "ready"}
        icon={<ClipboardList className="h-3.5 w-3.5" />}
      />
      <KpiTile
        label="Error state"
        value={error}
        detail={error > 0 ? "Connector or eval errors" : "No connector errors"}
        tone={error > 0 ? "critical" : "ready"}
        icon={<AlertCircle className="h-3.5 w-3.5" />}
      />
      <KpiTile
        label="Monitored tests"
        value={total}
        detail="Continuous control monitoring"
        tone="brand"
        icon={<ClipboardList className="h-3.5 w-3.5" />}
      />
    </div>
  );
}
