"use client";

import Link from "next/link";
import type { FrameworkPosture } from "@/lib/api/types";
import { FrameworkMark } from "@/components/framework/FrameworkMark";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { frameworkDetailHref } from "@/lib/framework-links";
import { cn } from "@/lib/utils";

function ringColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

function ComplianceTile({
  label,
  frameworkId,
  score,
  inverse,
}: {
  label: string;
  frameworkId: string;
  score: number;
  inverse: boolean;
}) {
  const color = ringColor(score);
  const pct = Math.min(100, Math.max(0, score));
  const r = 28;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;

  return (
    <Link
      href={frameworkDetailHref(frameworkId)}
      className={cn(
        "grid h-[84px] min-w-0 snap-start grid-cols-[36px_minmax(0,1fr)] items-center gap-2 rounded-lg border p-2 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand hover:shadow-card",
        inverse
          ? "border-white/10 bg-white/[0.06] hover:bg-white/[0.09]"
          : "border-line bg-surface",
      )}
    >
      <div className="relative h-9 w-9">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 72 72">
          <circle
            cx="36"
            cy="36"
            r={r}
            fill="none"
            stroke={inverse ? "rgba(148, 163, 184, 0.18)" : "var(--color-line)"}
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
            size={20}
          />
        </div>
      </div>
      <div className="min-w-0">
        <div className="text-sm font-black tabular-nums" style={{ color }}>
          {Math.round(score)}%
        </div>
        <div
          className={cn(
            "mt-0.5 truncate text-[10px] font-bold leading-tight",
            inverse ? "text-slate-400" : "text-muted",
          )}
        >
          {label}
        </div>
      </div>
    </Link>
  );
}

export function ComplianceOverview({
  frameworks,
  className,
  inverse = false,
}: {
  frameworks: FrameworkPosture[];
  className?: string;
  inverse?: boolean;
}) {
  const ordered = [...frameworks].sort(
    (a, b) =>
      a.score - b.score || b.failing_control_count - a.failing_control_count,
  );

  if (ordered.length === 0) return null;

  return (
    <div
      className={cn(
        "grid max-h-[178px] grid-flow-col grid-rows-2 auto-cols-[96px] snap-x snap-mandatory gap-2 overflow-x-auto pb-2 pr-1 [-ms-overflow-style:none] [scrollbar-width:thin]",
        className,
      )}
      role="region"
      aria-label="Framework posture comparison"
    >
      {ordered.map((f) => (
        <ComplianceTile
          key={f.framework}
          label={f.framework}
          frameworkId={resolveFrameworkId(f.framework)}
          score={f.score}
          inverse={inverse}
        />
      ))}
    </div>
  );
}
