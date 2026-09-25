"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, LayoutGrid, ListFilter } from "lucide-react";
import type { FrameworkPosture, FrameworkView } from "@/lib/api/types";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { frameworkDetailHref } from "@/lib/framework-links";
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
    return { label: "Needs attention", tone: "critical" as const };
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
  if (!framework && !unmonitored) return null;
  const id = unmonitored?.framework_id ?? frameworkIdFor(framework!.framework);
  const label = unmonitored
    ? frameworkLabel(unmonitored)
    : framework!.framework;
  const status = framework
    ? statusFor(framework).label
    : unmonitored?.implementation_status === "planned"
      ? "Planned"
      : "Not assessed";
  return (
    <Link
      href={frameworkDetailHref(id)}
      className="group flex min-w-0 items-center gap-3 border-b border-line px-2 py-4 transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    >
      <FrameworkBadge
        frameworkId={id}
        fallbackLabel={label}
        size={40}
        variant="mark-only"
      />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold leading-5 text-ink [overflow-wrap:anywhere]">
          {label}
        </div>
        <div className="mt-1 text-xs leading-5 text-muted">
          {framework
            ? `${framework.control_count} ${framework.control_count === 1 ? "control" : "controls"} · ${framework.failing_control_count} failing · ${framework.stale_control_count} stale`
            : `${unmonitored!.implemented_control_count} implemented controls`}
        </div>
      </div>
      <div className="w-24 shrink-0 text-right">
        {framework && (
          <div
            className="text-xl font-semibold tabular-nums"
            title="Assessment score"
            style={{ color: barColor(framework.score) }}
          >
            {Math.round(framework.score)}
            <span className="text-sm">%</span>
          </div>
        )}
        <div className="text-[11px] font-medium text-muted">{status}</div>
      </div>
    </Link>
  );
}

export function ReadinessGrid({
  frameworks,
  catalog = [],
  embedded = false,
}: {
  frameworks: FrameworkPosture[];
  catalog?: FrameworkView[];
  embedded?: boolean;
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
  const visibleLimit = showAll || expanded ? totalCount : 3;
  const visibleFrameworks = sorted.slice(0, visibleLimit);
  const visibleUnmonitored = unmonitored.slice(
    0,
    Math.max(visibleLimit - visibleFrameworks.length, 0),
  );
  const hiddenCount = Math.max(
    totalCount - visibleFrameworks.length - visibleUnmonitored.length,
    0,
  );
  const summary = `${sorted.length} assessed · ${workCount} need attention · ${readyCount} ready · ${unmonitored.length} not assessed`;

  return (
    <CollapsibleCard
      embedded={embedded}
      storageKey="dashboard-framework-readiness"
      defaultOpen
      title="Framework posture"
      className="shadow-card [&>div:first-child>button]:min-w-[180px] [&>div:first-child]:items-center [&>div:first-child]:flex-wrap [&>div:first-child]:px-5 [&>div:first-child]:py-4"
      contentClassName="space-y-3 px-3 py-3 sm:px-5"
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
      <p className="text-sm text-muted">{summary}</p>

      {totalCount > 0 ? (
        <>
          <div className="relative">
            <div
              className={cn(
                "grid min-w-0 gap-x-7 2xl:grid-cols-2",
                (showAll || expanded) &&
                  "max-h-[360px] overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin]",
              )}
              tabIndex={0}
              role="region"
              aria-label="Framework posture list"
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
              Show {hiddenCount} more frameworks
            </Button>
          )}
          {(expanded || showAll) && totalCount > 3 && (
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
              Show priority frameworks
            </Button>
          )}
        </>
      ) : (
        <div className="rounded-lg border border-dashed border-line bg-surfaceMuted p-5 text-sm font-semibold text-muted">
          No framework assessments yet. Connect a source and evaluate controls
          to begin.
        </div>
      )}
    </CollapsibleCard>
  );
}
