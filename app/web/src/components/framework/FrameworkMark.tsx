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
  const fontSize = Math.max(
    7,
    Math.min(12, size * (visual.mark.length > 4 ? 0.2 : 0.27)),
  );

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
      aria-label={`${visual.label} framework`}
    >
      <span
        className="font-black leading-none tracking-[-0.04em]"
        style={{ fontSize }}
        aria-hidden="true"
      >
        {visual.mark}
      </span>
    </span>
  );
}
