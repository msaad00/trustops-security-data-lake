"use client";

import type { CSSProperties } from "react";
import { connectorVisual } from "@/lib/connector-visuals";

interface ConnectorMarkProps {
  connectorId: string;
  name?: string;
  category?: string;
  size?: "sm" | "md" | "lg";
  showVendor?: boolean;
  className?: string;
}

const SIZE: Record<
  NonNullable<ConnectorMarkProps["size"]>,
  { box: number; mark: string; vendor: string }
> = {
  sm: { box: 36, mark: "text-[9px]", vendor: "text-[10px]" },
  md: { box: 40, mark: "text-[10px]", vendor: "text-[11px]" },
  lg: { box: 48, mark: "text-[11px]", vendor: "text-xs" },
};

export function ConnectorMark({
  connectorId,
  name,
  category,
  size = "md",
  showVendor = false,
  className,
}: ConnectorMarkProps) {
  const visual = connectorVisual(connectorId, { name, category });
  const dim = SIZE[size];
  const boxStyle: CSSProperties = {
    width: dim.box,
    height: dim.box,
    color: visual.accent,
    background: visual.bg,
  };

  return (
    <span
      className={["inline-flex min-w-0 items-center gap-2", className]
        .filter(Boolean)
        .join(" ")}
      role="img"
      aria-label={`${visual.vendor} source mark; not an official vendor logo`}
      title={`${visual.vendor} — neutral source mark`}
    >
      <span
        className={[
          "grid shrink-0 place-items-center rounded-lg font-black tracking-wide ring-1 ring-line",
          dim.mark,
        ].join(" ")}
        style={boxStyle}
      >
        {visual.mark}
      </span>
      {showVendor && (
        <span className="min-w-0 truncate">
          <span
            className={["block font-black text-ink", dim.vendor].join(" ")}
          >
            {name ?? visual.vendor}
          </span>
          <span className="block truncate text-[10px] text-muted">
            {visual.categoryLabel}
          </span>
        </span>
      )}
    </span>
  );
}
