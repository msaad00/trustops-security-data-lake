"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, LayoutGrid, ListFilter } from "lucide-react";
import type { FrameworkPosture } from "@/lib/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

function statusFor(framework: FrameworkPosture) {
  if (framework.state === "ready") {
    return { label: "Ready", tone: "ready" as const };
  }
  if (framework.critical_violation_count > 0 || framework.score < 50) {
    return { label: "Needs work", tone: "critical" as const };
  }
  return { label: "Review", tone: "attention" as const };
}

function worstFirst(a: FrameworkPosture, b: FrameworkPosture) {
  return (
    a.score - b.score ||
    b.critical_violation_count - a.critical_violation_count ||
    b.failing_control_count - a.failing_control_count ||
    b.stale_control_count - a.stale_control_count ||
    a.framework.localeCompare(b.framework)
  );
}

export function ReadinessGrid({
  frameworks,
}: {
  frameworks: FrameworkPosture[];
}) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const sorted = useMemo(() => [...frameworks].sort(worstFirst), [frameworks]);
  const readyCount = sorted.filter((f) => f.state === "ready").length;
  const workCount = sorted.length - readyCount;
  const visibleFrameworks = showAll || expanded ? sorted : sorted.slice(0, 4);
  const hiddenCount = Math.max(sorted.length - visibleFrameworks.length, 0);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-3 border-b border-line bg-white">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Framework portfolio</CardTitle>
            <CardDescription>
              Priority programs first. Expand for the full audit scope.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="default">{sorted.length} programs</Badge>
            <Badge tone={readyCount > 0 ? "ready" : "default"}>
              {readyCount} ready
            </Badge>
            <Badge tone={workCount > 0 ? "critical" : "ready"}>
              {workCount} need work
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant={!showAll ? "dark" : "default"}
            onClick={() => {
              setShowAll(false);
              setExpanded(false);
            }}
          >
            <ListFilter className="h-4 w-4" />
            Priority
          </Button>
          <Button
            type="button"
            size="sm"
            variant={showAll ? "dark" : "default"}
            onClick={() => {
              setShowAll(true);
              setExpanded(true);
            }}
          >
            <LayoutGrid className="h-4 w-4" />
            All
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-3">
        {visibleFrameworks.length > 0 && (
          <div className="grid gap-2.5 xl:grid-cols-2">
            {visibleFrameworks.map((f) => {
              const score = Math.round(f.score);
              const color = barColor(f.score);
              const status = statusFor(f);
              return (
                <div
                  key={f.framework}
                  className={cn(
                    "grid gap-3 rounded-lg border border-line bg-white p-3 transition-shadow hover:shadow-card",
                    f.state !== "ready" && "border-l-4",
                  )}
                  style={
                    f.state !== "ready" ? { borderLeftColor: color } : undefined
                  }
                >
                  <div className="flex min-w-0 items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <FrameworkBadge
                        frameworkId={frameworkIdFor(f.framework)}
                        fallbackLabel={f.framework}
                        size={38}
                        className="bg-white shadow-sm"
                      />
                      <div className="min-w-0">
                        <div className="truncate text-sm font-black text-ink">
                          {f.framework}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <Badge tone={status.tone}>{status.label}</Badge>
                          <span className="text-xs font-bold text-muted">
                            {f.control_count} controls
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
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
                  <div className="grid gap-2 text-xs sm:grid-cols-3">
                    <div className="rounded-md bg-panel px-2.5 py-2">
                      <div className="font-black text-ink tabular-nums">
                        {f.control_count}
                      </div>
                      <div className="font-bold text-muted">mapped</div>
                    </div>
                    <div className="rounded-md bg-rose-50 px-2.5 py-2">
                      <div className="font-black text-rose-700 tabular-nums">
                        {f.failing_control_count}
                      </div>
                      <div className="font-bold text-rose-700">failing</div>
                    </div>
                    <div className="rounded-md bg-amber-50 px-2.5 py-2">
                      <div className="font-black text-amber-800 tabular-nums">
                        {f.stale_control_count}
                      </div>
                      <div className="font-bold text-amber-800">stale</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {hiddenCount > 0 && (
          <Button
            type="button"
            variant="default"
            className="w-full"
            aria-expanded={expanded}
            onClick={() => setExpanded(true)}
          >
            <ChevronDown className="h-4 w-4" />
            Show {hiddenCount} more programs
          </Button>
        )}
        {(expanded || showAll) && sorted.length > 4 && (
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => {
              setExpanded(false);
              setShowAll(false);
            }}
          >
            <ChevronUp className="h-4 w-4" />
            Collapse to priority
          </Button>
        )}
        {sorted.length === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-panel p-4 text-sm font-bold text-muted">
            No framework posture yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
