"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, LayoutGrid, ListFilter } from "lucide-react";
import type { FrameworkPosture, FrameworkView } from "@/lib/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { resolveFrameworkId } from "@/lib/framework-visuals";
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
  FedRAMP: "fedramp-moderate",
  "CIS AWS": "cis_aws",
};

function frameworkIdFor(label: string) {
  return resolveFrameworkId(FRAMEWORK_IDS[label] ?? label);
}

function frameworkLabel(framework: FrameworkView) {
  if (framework.framework_id === "soc2") return "SOC 2";
  if (framework.framework_id === "nist-ai-rmf") return "NIST AI RMF";
  if (framework.framework_id === "iso-27001-2022") return "ISO 27001";
  if (framework.framework_id === "iso-42001-2023") return "ISO 42001";
  if (framework.framework_id === "hipaa-security-rule") return "HIPAA";
  if (framework.framework_id === "pci-dss-v4") return "PCI DSS";
  if (framework.framework_id === "gdpr-2016-679") return "GDPR";
  if (framework.framework_id === "eu-ai-act-2024-1689") return "EU AI Act";
  return framework.name;
}

function statusFor(framework: FrameworkPosture) {
  if (framework.state === "ready") {
    return { label: "Ready", tone: "ready" as const };
  }
  if (framework.critical_violation_count > 0 || framework.score < 50) {
    return { label: "Action required", tone: "critical" as const };
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
  catalog = [],
}: {
  frameworks: FrameworkPosture[];
  catalog?: FrameworkView[];
}) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const sorted = useMemo(() => [...frameworks].sort(worstFirst), [frameworks]);
  const monitoredIds = useMemo(
    () =>
      new Set(sorted.map((framework) => frameworkIdFor(framework.framework))),
    [sorted],
  );
  const unmonitored = useMemo(
    () =>
      catalog
        .filter((framework) => !monitoredIds.has(framework.framework_id))
        .sort((a, b) =>
          frameworkLabel(a).localeCompare(frameworkLabel(b), undefined, {
            numeric: true,
          }),
        ),
    [catalog, monitoredIds],
  );
  const readyCount = sorted.filter((f) => f.state === "ready").length;
  const workCount = sorted.length - readyCount;
  const totalCount = sorted.length + unmonitored.length;
  const visibleLimit = showAll || expanded ? totalCount : 6;
  const visibleFrameworks = sorted.slice(0, visibleLimit);
  const visibleUnmonitored = unmonitored.slice(
    0,
    Math.max(visibleLimit - visibleFrameworks.length, 0),
  );
  const hiddenCount = Math.max(
    totalCount - visibleFrameworks.length - visibleUnmonitored.length,
    0,
  );
  const avgScore =
    sorted.length > 0
      ? Math.round(
          sorted.reduce((sum, framework) => sum + framework.score, 0) /
            sorted.length,
        )
      : 0;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-3 border-b border-line bg-white">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Framework readiness</CardTitle>
            <CardDescription>
              Worst gaps first across the registered audit and assurance scope.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="default">{totalCount} programs</Badge>
            <Badge tone={avgScore >= 85 ? "ready" : "attention"}>
              {avgScore}% avg
            </Badge>
            <Badge tone={readyCount > 0 ? "ready" : "default"}>
              {readyCount} ready
            </Badge>
            <Badge tone={workCount > 0 ? "critical" : "ready"}>
              {workCount} monitored gaps
            </Badge>
            {unmonitored.length > 0 && (
              <Badge tone="default">{unmonitored.length} not monitored</Badge>
            )}
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
        {totalCount > 0 && (
          <div className="grid gap-2.5 lg:grid-cols-2 2xl:grid-cols-3">
            {visibleFrameworks.map((f) => {
              const score = Math.round(f.score);
              const color = barColor(f.score);
              const status = statusFor(f);
              const gapCount = f.failing_control_count + f.stale_control_count;
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
                        size={36}
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
                        {score}%
                      </div>
                      <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-muted">
                        ready
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
                      <div className="font-bold text-muted">controls</div>
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
                  <div className="text-xs font-bold text-muted">
                    {gapCount === 0
                      ? "No current gaps detected for this program."
                      : `${gapCount} gap${gapCount === 1 ? "" : "s"} blocking external share.`}
                  </div>
                </div>
              );
            })}
            {visibleUnmonitored.map((framework) => (
              <div
                key={framework.framework_id}
                className="grid gap-3 rounded-lg border border-dashed border-line bg-panel p-3"
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <FrameworkBadge
                      frameworkId={framework.framework_id}
                      fallbackLabel={frameworkLabel(framework)}
                      size={36}
                      className="bg-white shadow-sm"
                    />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-ink">
                        {frameworkLabel(framework)}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <Badge tone="default">Not monitored yet</Badge>
                        <span className="text-xs font-bold text-muted">
                          {framework.implemented_control_count} mapped controls
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-lg font-black leading-none text-muted">
                      --
                    </div>
                    <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-muted">
                      ready
                    </div>
                  </div>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100" />
                <div className="text-xs font-bold text-muted">
                  Registered in the catalog, but no live evidence has evaluated
                  this program in the current lake.
                </div>
              </div>
            ))}
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
        {(expanded || showAll) && totalCount > 6 && (
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
        {totalCount === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-panel p-4 text-sm font-bold text-muted">
            No framework posture yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
