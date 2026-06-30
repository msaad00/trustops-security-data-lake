"use client";

import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { Badge } from "@/components/ui/badge";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import { cn } from "@/lib/utils";

function barColor(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

export function FrameworkCard({
  frameworkId,
  label,
  score,
  state,
  failingControls = 0,
  staleControls = 0,
  criticalViolations = 0,
  controlCount,
  mappedCount,
  onClick,
  variant = "posture",
  className,
}: {
  frameworkId: string;
  label: string;
  score?: number;
  state?: string;
  failingControls?: number;
  staleControls?: number;
  criticalViolations?: number;
  controlCount?: number;
  mappedCount?: number;
  onClick?: () => void;
  variant?: "posture" | "catalog";
  className?: string;
}) {
  const id = resolveFrameworkId(frameworkId);
  const hasScore = typeof score === "number";
  const statusTone =
    state === "ready"
      ? "ready"
      : criticalViolations > 0 || (hasScore && score < 50)
        ? "critical"
        : "attention";
  const statusLabel =
    state === "ready"
      ? "Ready"
      : criticalViolations > 0 || (hasScore && score < 50)
        ? "Action required"
        : hasScore
          ? "Review"
          : "Catalog";

  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <FrameworkBadge frameworkId={id} fallbackLabel={label} size={36} />
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </div>
      {hasScore && (
        <div className="mt-3">
          <div className="flex items-end justify-between gap-2">
            <span className="text-2xl font-black tabular-nums text-ink">
              {score}%
            </span>
            <span className="text-xs text-muted">readiness</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-panel">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(100, Math.max(0, score))}%`,
                background: barColor(score),
              }}
            />
          </div>
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
        {variant === "posture" ? (
          <>
            {failingControls > 0 && (
              <Badge tone="critical">{failingControls} failing</Badge>
            )}
            {staleControls > 0 && (
              <Badge tone="attention">{staleControls} stale</Badge>
            )}
            {criticalViolations > 0 && (
              <Badge tone="critical">{criticalViolations} critical</Badge>
            )}
            {failingControls === 0 &&
              staleControls === 0 &&
              criticalViolations === 0 && (
                <Badge tone="ready">No open gaps</Badge>
              )}
          </>
        ) : (
          <>
            {controlCount !== undefined && (
              <Badge>{controlCount} controls</Badge>
            )}
            {mappedCount !== undefined && (
              <Badge tone="ready">{mappedCount} mapped</Badge>
            )}
          </>
        )}
      </div>
    </>
  );

  const shellClass = cn(
    "rounded-xl border border-line bg-white p-4 text-left shadow-sm transition-all",
    onClick && "hover:border-brand hover:shadow-card cursor-pointer",
    className,
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(shellClass, "w-full")}
      >
        {body}
      </button>
    );
  }

  return <div className={shellClass}>{body}</div>;
}
