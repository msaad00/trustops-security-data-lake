"use client";

import Link from "next/link";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useInsightsSlaHeatmap } from "@/lib/api/hooks";
import type { SlaHeatmapColumn } from "@/lib/api/types";

const COLUMN_LABELS: Record<SlaHeatmapColumn, string> = {
  open_on_track: "Open · on track",
  open_overdue: "Open · overdue",
  open_no_sla: "Open · no SLA",
  resolved_on_time: "Resolved · on time",
  resolved_late: "Resolved · late",
};

const COLUMN_TONE: Record<SlaHeatmapColumn, "ok" | "warn" | "bad" | "neutral"> =
  {
    open_on_track: "ok",
    open_overdue: "bad",
    open_no_sla: "neutral",
    resolved_on_time: "ok",
    resolved_late: "warn",
  };

function cellClass(tone: "ok" | "warn" | "bad" | "neutral", active: boolean) {
  if (!active) return "bg-slate-50 text-slate-400";
  if (tone === "bad") return "bg-red-100 text-red-800";
  if (tone === "warn") return "bg-amber-100 text-amber-900";
  if (tone === "ok") return "bg-emerald-100 text-emerald-900";
  return "bg-slate-100 text-slate-700";
}

export function SlaHeatmapPanel() {
  const heatmap = useInsightsSlaHeatmap();
  const columns = heatmap.data?.columns ?? [];
  const rows = heatmap.data?.owner_rows ?? [];

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Remediation SLA heatmap</CardTitle>
        <CardDescription>
          Task counts by owner and SLA state. Select a cell to open that
          owner&apos;s remediation workbench.
        </CardDescription>
      </CardHeader>
      <div className="overflow-x-auto px-4 pb-4">
        {heatmap.isLoading ? (
          <div className="flex h-[160px] items-center justify-center text-sm text-muted">
            Loading SLA heatmap…
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-[160px] items-center justify-center text-sm text-muted">
            No remediation tasks yet.
          </div>
        ) : (
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="px-2 py-2 text-left text-[11px] font-black uppercase tracking-wider text-muted">
                  Owner
                </th>
                {columns.map((column) => (
                  <th
                    key={column}
                    className="px-2 py-2 text-center text-[11px] font-black uppercase tracking-wider text-muted"
                  >
                    {COLUMN_LABELS[column]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.owner}>
                  <td className="max-w-48 truncate px-2 py-2 font-semibold text-ink">
                    {row.owner}
                  </td>
                  {columns.map((column) => {
                    const value = row[column];
                    const tone = COLUMN_TONE[column];
                    return (
                      <td key={column} className="px-2 py-2 text-center">
                        {value > 0 ? (
                          <Link
                            href={`/remediation?owner=${encodeURIComponent(row.owner === "Unassigned" ? "" : row.owner)}`}
                            aria-label={`${row.owner}: ${value} ${COLUMN_LABELS[column].toLowerCase()} remediation task${value === 1 ? "" : "s"}`}
                            className={`inline-flex min-w-[2.25rem] justify-center rounded-lg px-2 py-1 text-xs font-bold ring-offset-2 hover:underline focus:outline-none focus:ring-2 focus:ring-brand ${cellClass(tone, true)}`}
                          >
                            {value}
                          </Link>
                        ) : (
                          <span
                            className={`inline-flex min-w-[2.25rem] justify-center rounded-lg px-2 py-1 text-xs font-bold ${cellClass(tone, false)}`}
                          >
                            0
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
