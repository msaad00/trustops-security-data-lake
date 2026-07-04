"use client";

import type { CSSProperties } from "react";
import { connectorBrandLogo } from "@/lib/connector-brand-logos";
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
  { box: number; icon: number; mark: string; vendor: string }
> = {
  sm: { box: 40, icon: 22, mark: "text-[9px]", vendor: "text-[10px]" },
  md: { box: 44, icon: 24, mark: "text-[10px]", vendor: "text-[11px]" },
  lg: { box: 52, icon: 28, mark: "text-[11px]", vendor: "text-xs" },
};

function BrandSvg({
  title,
  hex,
  path,
  iconSize,
}: {
  title: string;
  hex: string;
  path: string;
  iconSize: number;
}) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      width={iconSize}
      height={iconSize}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <title>{title}</title>
      <path d={path} fill={`#${hex}`} />
    </svg>
  );
}

export function ConnectorMark({
  connectorId,
  name,
  category,
  size = "md",
  showVendor = false,
  className,
}: ConnectorMarkProps) {
  const brand = connectorBrandLogo(connectorId);
  const visual = connectorVisual(connectorId, { name, category });
  const dim = SIZE[size];
  const boxStyle: CSSProperties = {
    width: dim.box,
    height: dim.box,
  };

  return (
    <span
      className={["inline-flex min-w-0 items-center gap-2.5", className]
        .filter(Boolean)
        .join(" ")}
      role="img"
      aria-label={`${visual.vendor} connector`}
      title={visual.vendor}
    >
      <span
        className="grid shrink-0 place-items-center rounded-xl border border-line bg-white shadow-sm"
        style={boxStyle}
      >
        {brand ? (
          <BrandSvg
            title={brand.title}
            hex={brand.hex}
            path={brand.path}
            iconSize={dim.icon}
          />
        ) : (
          <span
            className={[
              "grid h-full w-full place-items-center rounded-xl font-black tracking-wide",
              dim.mark,
            ].join(" ")}
            style={{ color: visual.accent, background: visual.bg }}
          >
            {visual.mark}
          </span>
        )}
      </span>
      {showVendor && (
        <span className="min-w-0 overflow-hidden">
          <span className={["block truncate font-black text-ink", dim.vendor].join(" ")}>
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
