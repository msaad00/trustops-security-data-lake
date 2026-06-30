"use client";

import { Database, Layers, Sparkles, Table2 } from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const STAGES = [
  {
    id: "bronze",
    label: "Bronze",
    detail: "Raw evidence ingest",
    icon: Database,
    accent: "#64748b",
    bg: "#f8fafc",
  },
  {
    id: "silver",
    label: "Silver",
    detail: "Normalized events",
    icon: Layers,
    accent: "#2563eb",
    bg: "#eff6ff",
  },
  {
    id: "gold",
    label: "Gold",
    detail: "Control posture + tests",
    icon: Sparkles,
    accent: "#7c3aed",
    bg: "#f5f3ff",
  },
  {
    id: "mart",
    label: "Mart",
    detail: "SQLite / DuckDB / lake",
    icon: Table2,
    accent: "#0f766e",
    bg: "#f0fdfa",
  },
] as const;

export function DataPipelineStrip({ className }: { className?: string }) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="border-b border-line bg-gradient-to-r from-slate-50 to-white pb-3">
        <CardTitle className="text-base">Evidence data plane</CardTitle>
        <CardDescription>
          Bronze → silver → gold lakehouse with deterministic assessment marts
          (managed GRC-style continuous monitoring path).
        </CardDescription>
      </CardHeader>
      <div className="grid gap-0 sm:grid-cols-4">
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div
              key={stage.id}
              className={cn(
                "relative border-line p-4 sm:border-r last:sm:border-r-0",
                index > 0 && "border-t sm:border-t-0",
              )}
            >
              {index < STAGES.length - 1 && (
                <div className="absolute -right-2 top-1/2 z-10 hidden h-0.5 w-4 -translate-y-1/2 bg-line sm:block" />
              )}
              <div
                className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl shadow-sm"
                style={{ background: stage.bg, color: stage.accent }}
              >
                <Icon className="h-5 w-5" strokeWidth={2.25} />
              </div>
              <div className="text-sm font-black text-ink">{stage.label}</div>
              <div className="mt-0.5 text-xs text-muted">{stage.detail}</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
