"use client";

import { useState } from "react";
import { Database, Layers, Sparkles, Table2 } from "lucide-react";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { cn } from "@/lib/utils";

const STAGES = [
  {
    id: "bronze",
    label: "Bronze",
    detail: "Raw evidence ingest",
    icon: Database,
    accent: "#64748b",
    bg: "var(--color-surface-muted)",
  },
  {
    id: "silver",
    label: "Silver",
    detail: "Normalized events",
    icon: Layers,
    accent: "#2563eb",
    bg: "var(--color-surface-muted)",
  },
  {
    id: "gold",
    label: "Gold",
    detail: "Control posture + tests",
    icon: Sparkles,
    accent: "#7c3aed",
    bg: "var(--color-surface-muted)",
  },
  {
    id: "mart",
    label: "Mart",
    detail: "SQLite / DuckDB / lake",
    icon: Table2,
    accent: "#0f766e",
    bg: "var(--color-surface-muted)",
  },
] as const;

export function DataPipelineStrip({ className }: { className?: string }) {
  const [scrollHint, setScrollHint] = useState(true);

  return (
    <CollapsibleCard
      storageKey="dashboard-data-pipeline"
      defaultOpen={false}
      title="Evidence data plane"
      description="Bronze → silver → gold lakehouse with deterministic assessment marts"
      className={className}
      contentClassName="p-0"
    >
      <div
        className="relative flex snap-x snap-mandatory gap-0 overflow-x-auto pb-1 sm:grid sm:snap-none sm:grid-cols-4 sm:overflow-visible"
        onScroll={() => setScrollHint(false)}
      >
        {scrollHint && (
          <div
            className="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-surface to-transparent sm:hidden"
            aria-hidden
          />
        )}
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div
              key={stage.id}
              className={cn(
                "relative min-w-[72%] shrink-0 snap-start border-line p-4 sm:min-w-0 sm:shrink sm:border-r last:sm:border-r-0",
                index > 0 && "border-l sm:border-l-0 sm:border-t-0",
              )}
            >
              <div
                className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-line shadow-sm"
                style={{ background: stage.bg, color: stage.accent }}
              >
                <Icon className="h-5 w-5" strokeWidth={2.25} />
              </div>
              <div className="text-sm font-black text-ink">{stage.label}</div>
              <div className="mt-0.5 text-xs leading-5 text-muted">
                {stage.detail}
              </div>
            </div>
          );
        })}
      </div>
    </CollapsibleCard>
  );
}
