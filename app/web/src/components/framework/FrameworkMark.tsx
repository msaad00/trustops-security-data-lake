"use client";

import { frameworkVisual } from "@/lib/framework-visuals";
import { cn } from "@/lib/utils";

export function FrameworkMark({
  frameworkId,
  fallbackLabel,
  size = 40,
  className,
}: {
  frameworkId: string;
  fallbackLabel?: string;
  size?: number;
  className?: string;
}) {
  const visual = frameworkVisual(frameworkId, fallbackLabel);

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg border font-black",
        className,
      )}
      style={{
        width: size,
        height: size,
        background: visual.bg,
        borderColor: visual.ring,
        color: visual.accent,
      }}
      role="img"
      aria-hidden
    >
      <span
        className="tracking-tight"
        style={{ fontSize: Math.max(9, size * 0.22) }}
      >
        {visual.mark}
      </span>
    </span>
  );
}
