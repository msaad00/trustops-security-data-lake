"use client";

import type { FrameworkPosture } from "@/lib/api/types";
import { FrameworkMark } from "@/components/framework/FrameworkMark";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { cn } from "@/lib/utils";

function ringColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

function ComplianceRing({
  label,
  frameworkId,
  score,
}: {
  label: string;
  frameworkId: string;
  score: number;
}) {
  const color = ringColor(score);
  const pct = Math.min(100, Math.max(0, score));
  const r = 28;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;

  return (
    <div className="flex min-w-[108px] flex-col items-center gap-2 rounded-xl border border-line bg-white p-3 shadow-sm">
      <div className="relative h-[72px] w-[72px]">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 72 72">
          <circle
            cx="36"
            cy="36"
            r={r}
            fill="none"
            stroke="#e2e8f0"
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
            size={32}
          />
        </div>
      </div>
      <div className="text-center">
        <div className="text-lg font-black tabular-nums" style={{ color }}>
          {Math.round(score)}%
        </div>
        <div className="max-w-[96px] truncate text-[10px] font-bold text-muted">
          {label}
        </div>
      </div>
    </div>
  );
}

export function ComplianceOverview({
  frameworks,
  className,
}: {
  frameworks: FrameworkPosture[];
  className?: string;
}) {
  const top = [...frameworks]
    .sort(
      (a, b) =>
        a.score - b.score || b.failing_control_count - a.failing_control_count,
    )
    .slice(0, 6);

  if (top.length === 0) return null;

  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
        className,
      )}
    >
      {top.map((f) => (
        <ComplianceRing
          key={f.framework}
          label={f.framework}
          frameworkId={resolveFrameworkId(f.framework)}
          score={f.score}
        />
      ))}
    </div>
  );
}
