"use client";

import type { FrameworkPosture } from "@/lib/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";

function barColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

const FRAMEWORK_IDS: Record<string, string> = {
  "SOC 2": "soc2",
  "NIST AI RMF": "nist-ai-rmf",
  "ISO 27001": "iso-27001-2022",
  "ISO 42001": "iso-42001-2023",
  HIPAA: "hipaa-security-rule",
  "PCI DSS": "pci-dss-v4",
  GDPR: "gdpr-2016-679",
  "EU AI Act": "eu-ai-act-2024-1689",
};

function frameworkIdFor(label: string) {
  return FRAMEWORK_IDS[label] ?? label.toLowerCase().replaceAll(" ", "-");
}

export function ReadinessGrid({
  frameworks,
}: {
  frameworks: FrameworkPosture[];
}) {
  const sorted = [...frameworks].sort((a, b) => a.score - b.score);
  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-line bg-white">
        <CardTitle>Framework portfolio</CardTitle>
        <CardDescription>
          Where each audit or assurance program stands right now.
        </CardDescription>
      </CardHeader>
      <div className="grid gap-2.5 p-3 sm:grid-cols-2 xl:grid-cols-3">
        {sorted.map((f) => {
          const score = Math.round(f.score);
          const color = barColor(f.score);
          return (
            <div
              key={f.framework}
              className="grid gap-3 rounded-lg border border-line bg-white p-3 transition-shadow hover:shadow-card"
            >
              <div className="flex items-center justify-between gap-2">
                <FrameworkBadge
                  frameworkId={frameworkIdFor(f.framework)}
                  fallbackLabel={f.framework}
                  size={34}
                  className="bg-white shadow-sm"
                />
                <div className="text-right">
                  <div
                    className="text-2xl font-black leading-none tabular-nums"
                    style={{ color }}
                  >
                    {score}
                  </div>
                  <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-muted">
                    score
                  </div>
                </div>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${score}%`, background: color }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <span className="rounded-md bg-panel px-2 py-1 text-muted">
                  <b className="text-ink">{f.control_count}</b> controls
                </span>
                <span className="rounded-md bg-rose-50 px-2 py-1 text-rose-700">
                  <b>{f.failing_control_count}</b> failing
                </span>
                <span className="rounded-md bg-amber-50 px-2 py-1 text-amber-800">
                  <b>{f.stale_control_count}</b> stale
                </span>
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
