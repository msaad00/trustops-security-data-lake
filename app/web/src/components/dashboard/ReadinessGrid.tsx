"use client";

import type { FrameworkPosture } from "@/lib/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function barColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

export function ReadinessGrid({
  frameworks,
}: {
  frameworks: FrameworkPosture[];
}) {
  const sorted = [...frameworks].sort((a, b) => a.score - b.score);
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Framework readiness</CardTitle>
        <CardDescription>
          Weighted score per framework — control pass rate minus stale penalty.
        </CardDescription>
      </CardHeader>
      <div className="grid gap-2.5 p-3 pt-0 sm:grid-cols-2 xl:grid-cols-3">
        {sorted.map((f) => {
          const score = Math.round(f.score);
          const color = barColor(f.score);
          return (
            <div
              key={f.framework}
              className="rounded-lg border border-line bg-white p-2.5 transition-shadow hover:shadow-card"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-black text-ink">
                  {f.framework}
                </span>
                <span
                  className="text-sm font-black tabular-nums"
                  style={{ color }}
                >
                  {score}
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${score}%`, background: color }}
                />
              </div>
              <div className="mt-2 text-[11px] text-muted">
                {f.failing_control_count} failing · {f.stale_control_count}{" "}
                stale · {f.control_count} controls
              </div>
            </div>
          );
        })}
        {sorted.length === 0 && (
          <div className="text-sm text-muted">No framework posture yet.</div>
        )}
      </div>
    </Card>
  );
}
