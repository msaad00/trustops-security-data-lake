"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, LayoutGrid, ListFilter } from "lucide-react";
import type { FrameworkPosture, FrameworkView } from "@/lib/api/types";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { frameworkDetailHref } from "@/lib/framework-links";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function barColor(score: number) {
  if (score >= 85) return "#059669";
  if (score >= 65) return "#d97706";
  return "#dc2626";
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

function FrameworkCard({
  framework,
  unmonitored,
}: {
  framework?: FrameworkPosture;
  unmonitored?: FrameworkView;
}) {
  if (unmonitored) {
    return (
      <Link
        href={frameworkDetailHref(unmonitored.framework_id)}
        className="flex min-h-[132px] min-w-[260px] shrink-0 snap-start flex-col gap-2 rounded-xl border border-dashed border-line bg-surfaceMuted p-4 transition-colors hover:border-brand sm:min-w-0"
      >
        <div className="flex items-start gap-3">
          <FrameworkBadge
            frameworkId={unmonitored.framework_id}
            fallbackLabel={frameworkLabel(unmonitored)}
            size={40}
            className="bg-surface shadow-sm"
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-black text-ink">
              {frameworkLabel(unmonitored)}
            </div>
            <Badge tone="default" className="mt-1.5">
              Not monitored
            </Badge>
          </div>
        </div>
        <p className="text-xs leading-5 text-muted">
          {unmonitored.implemented_control_count} mapped controls · no live eval
          yet
        </p>
      </Link>
    );
  }

  if (!framework) return null;

  const score = Math.round(framework.score);
  const color = barColor(framework.score);
  const status = statusFor(framework);
  const gapCount = framework.failing_control_count + framework.stale_control_count;

  return (
    <Link
      href={frameworkDetailHref(frameworkIdFor(framework.framework))}
      className={cn(
        "flex min-h-[132px] min-w-[260px] shrink-0 snap-start flex-col gap-3 rounded-xl border border-line bg-surface p-4 transition-shadow hover:border-brand hover:shadow-card sm:min-w-0",
        framework.state !== "ready" && "border-l-4",
      )}
      style={
        framework.state !== "ready" ? { borderLeftColor: color } : undefined
      }
    >
      <div className="flex items-start gap-3">
        <FrameworkBadge
          frameworkId={frameworkIdFor(framework.framework)}
          fallbackLabel={framework.framework}
          size={40}
          className="bg-surface shadow-sm"
        />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-black text-ink">
            {framework.framework}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <Badge tone={status.tone}>{status.label}</Badge>
            <span className="text-xs font-semibold text-muted">
              {framework.control_count} controls
            </span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div
            className="text-2xl font-black leading-none tabular-nums"
            style={{ color }}
          >
            {score}%
          </div>
        </div>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surfaceMuted">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <p className="text-xs font-semibold leading-5 text-muted">
        {gapCount === 0
          ? "No gaps blocking external share"
          : `${framework.failing_control_count} failing · ${framework.stale_control_count} stale · ${gapCount} gap${gapCount === 1 ? "" : "s"}`}
      </p>
    </Link>
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
  const visibleLimit = showAll || expanded ? totalCount : 4;
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

  const summary = `${totalCount} programs · ${avgScore}% avg · ${readyCount} ready · ${workCount} gaps${unmonitored.length > 0 ? ` · ${unmonitored.length} unmonitored` : ""}`;

  return (
    <CollapsibleCard
      storageKey="dashboard-framework-readiness"
      defaultOpen
      title="Framework readiness"
      description="Worst gaps first — swipe on mobile or use Priority / All"
      contentClassName="space-y-3 p-3 sm:p-4"
      actions={
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
      }
    >
      <p className="text-xs font-semibold text-muted">{summary}</p>

      {totalCount > 0 ? (
        <>
          <div className="relative">
            <div
              className={cn(
                showAll
                  ? "grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
                  : "flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:thin] sm:snap-none sm:grid sm:grid-cols-2 sm:overflow-visible xl:grid-cols-2",
              )}
              role="region"
              aria-label="Framework readiness cards"
            >
            {visibleFrameworks.map((f) => (
              <FrameworkCard key={f.framework} framework={f} />
            ))}
            {visibleUnmonitored.map((framework) => (
              <FrameworkCard
                key={framework.framework_id}
                unmonitored={framework}
              />
            ))}
            </div>
            {!showAll && (
              <div
                className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-surface to-transparent sm:hidden"
                aria-hidden
              />
            )}
          </div>
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
          {(expanded || showAll) && totalCount > 4 && (
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
        </>
      ) : (
        <div className="rounded-lg border border-dashed border-line bg-surfaceMuted p-4 text-sm font-semibold text-muted">
          No framework posture yet.
        </div>
      )}
    </CollapsibleCard>
  );
}
