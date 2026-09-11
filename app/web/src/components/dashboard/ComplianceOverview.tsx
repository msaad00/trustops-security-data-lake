"use client";

import Link from "next/link";
import type { FrameworkPosture, FrameworkView } from "@/lib/api/types";
import { FrameworkMark } from "@/components/framework/FrameworkMark";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { frameworkDetailHref } from "@/lib/framework-links";
import { cn } from "@/lib/utils";

const FAMILY_LABELS: Record<string, string> = {
  assurance: "Assurance",
  security: "Security",
  privacy: "Privacy",
  "ai-governance": "AI governance",
  cloud: "Cloud",
  sector: "Sector",
};

function familyLabel(family?: string) {
  return FAMILY_LABELS[family ?? ""] ?? family ?? "Framework";
}

function ringColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

function ComplianceTile({
  label,
  frameworkId,
  posture,
  catalog,
  inverse,
}: {
  label: string;
  frameworkId: string;
  posture?: FrameworkPosture;
  catalog: FrameworkView;
  inverse: boolean;
}) {
  const score = posture?.score ?? 0;
  const color = ringColor(score);
  const pct = Math.min(100, Math.max(0, score));
  const r = 28;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const catalogOnly = !posture;
  const stateLabel = posture
    ? `${Math.round(score)}% · evaluated`
    : catalog.implementation_status === "planned"
      ? "planned"
      : "catalog only";

  return (
    <Link
      href={frameworkDetailHref(frameworkId)}
      className={cn(
        "grid h-[72px] min-w-0 snap-start grid-cols-[30px_minmax(0,1fr)] items-center gap-1.5 rounded-lg border p-1.5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand hover:shadow-card",
        inverse
          ? "border-white/15 bg-white/[0.09] hover:bg-white/[0.13]"
          : "border-line bg-surface",
      )}
    >
      {posture ? (
        <div className="relative h-[30px] w-[30px]">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 72 72">
            <circle
              cx="36"
              cy="36"
              r={r}
              fill="none"
              stroke={
                inverse ? "rgba(148, 163, 184, 0.18)" : "var(--color-line)"
              }
              strokeWidth="6"
            />
            <circle
              cx="36"
              cy="36"
              r={r}
              fill="none"
              stroke={color}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={c}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <FrameworkMark
              frameworkId={frameworkId}
              fallbackLabel={label}
              size={19}
            />
          </div>
        </div>
      ) : (
        <FrameworkMark
          frameworkId={frameworkId}
          fallbackLabel={label}
          size={28}
        />
      )}
      <div className="min-w-0">
        <div
          className={cn(
            "truncate text-[10px] font-black leading-tight",
            inverse ? "text-white" : "text-ink",
          )}
        >
          {label}
        </div>
        <div
          className={cn(
            "mt-1 truncate text-[9px] font-bold uppercase tracking-wide",
            catalogOnly
              ? inverse
                ? "text-slate-400"
                : "text-muted"
              : "text-emerald-300",
          )}
        >
          {stateLabel}
        </div>
      </div>
    </Link>
  );
}

export function ComplianceOverview({
  frameworks,
  catalog = [],
  className,
  inverse = false,
}: {
  frameworks: FrameworkPosture[];
  catalog?: FrameworkView[];
  className?: string;
  inverse?: boolean;
}) {
  const evaluated = new Map(
    frameworks.map((framework) => [
      resolveFrameworkId(framework.framework),
      framework,
    ]),
  );
  const items = catalog.length
    ? catalog.map((framework) => ({
        catalog: framework,
        posture: evaluated.get(framework.framework_id),
      }))
    : frameworks.map((framework) => ({
        catalog: {
          framework_id: resolveFrameworkId(framework.framework),
          name: framework.framework,
          implementation_status: "implemented",
        } as FrameworkView,
        posture: framework,
      }));
  const ordered = items.sort(
    (a, b) =>
      Number(Boolean(b.posture)) - Number(Boolean(a.posture)) ||
      (a.posture?.score ?? 101) - (b.posture?.score ?? 101) ||
      a.catalog.name.localeCompare(b.catalog.name),
  );

  if (ordered.length === 0) return null;

  const familyCounts = new Map<
    string,
    { count: number; frameworkId: string; label: string }
  >();
  for (const item of ordered) {
    const family = item.catalog.family ?? "security";
    const current = familyCounts.get(family);
    familyCounts.set(family, {
      count: (current?.count ?? 0) + 1,
      frameworkId: current?.frameworkId ?? item.catalog.framework_id,
      label: familyLabel(family),
    });
  }

  return (
    <div className={cn("min-w-0", className)}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span
          className={cn(
            "text-[9px] font-black uppercase tracking-[0.16em]",
            inverse ? "text-slate-300" : "text-muted",
          )}
        >
          Framework families
        </span>
        <Link
          href="/frameworks"
          className={cn(
            "text-[10px] font-black hover:underline",
            inverse ? "text-cyan-300" : "text-brand",
          )}
        >
          {frameworks.length}/{catalog.length || frameworks.length} evaluated
        </Link>
      </div>
      <div className="mb-2 flex min-w-0 gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none]">
        {[...familyCounts.values()].map((family) => (
          <Link
            key={family.label}
            href="/frameworks"
            className={cn(
              "inline-flex shrink-0 items-center gap-1 rounded-full border px-1.5 py-1 text-[9px] font-bold hover:border-brand",
              inverse
                ? "border-white/15 bg-white/[0.08] text-slate-300"
                : "border-line bg-surface text-muted",
            )}
            title={`${family.label}: ${family.count} catalogued frameworks`}
          >
            <FrameworkMark frameworkId={family.frameworkId} size={16} />
            <span>{family.label}</span>
            <span
              className={cn(
                "tabular-nums",
                inverse ? "text-white" : "text-ink",
              )}
            >
              {family.count}
            </span>
          </Link>
        ))}
      </div>
      <div
        className="grid max-h-[148px] grid-flow-col grid-rows-2 auto-cols-[104px] snap-x snap-mandatory gap-1.5 overflow-x-auto pb-1 pr-1 [-ms-overflow-style:none] [scrollbar-width:thin]"
        role="region"
        aria-label="Framework posture comparison"
      >
        {ordered.map(({ catalog: framework, posture }) => (
          <ComplianceTile
            key={framework.framework_id}
            label={framework.name}
            frameworkId={framework.framework_id}
            posture={posture}
            catalog={framework}
            inverse={inverse}
          />
        ))}
      </div>
    </div>
  );
}
