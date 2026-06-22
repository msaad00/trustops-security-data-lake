"use client";

/**
 * Neutral framework labels for the workbench.
 *
 * Do not recreate framework logos, certification seals, regulator marks, or
 * lookalike badges here. If an official public logo is ever used, it must come
 * from the official brand/certification program, carry documented permission,
 * and be tracked as a third-party asset.
 */

import type { CSSProperties } from "react";

interface FrameworkBadgeProps {
  frameworkId: string;
  fallbackLabel?: string;
  size?: number;
  className?: string;
}

const FRAMEWORKS: Record<
  string,
  { label: string; mark: string; accent: string; bg: string }
> = {
  soc2: { label: "SOC 2", mark: "SOC", accent: "#2563eb", bg: "#eff6ff" },
  "nist-ai-rmf": {
    label: "NIST AI",
    mark: "AI",
    accent: "#7c3aed",
    bg: "#f5f3ff",
  },
  "iso-27001-2022": {
    label: "ISO 27001",
    mark: "ISO",
    accent: "#0891b2",
    bg: "#ecfeff",
  },
  "iso-42001-2023": {
    label: "ISO 42001",
    mark: "AIMS",
    accent: "#0f766e",
    bg: "#f0fdfa",
  },
  "hipaa-security-rule": {
    label: "HIPAA",
    mark: "HHS",
    accent: "#059669",
    bg: "#ecfdf5",
  },
  "pci-dss-v4": {
    label: "PCI DSS",
    mark: "PCI",
    accent: "#d97706",
    bg: "#fffbeb",
  },
  "gdpr-2016-679": {
    label: "GDPR",
    mark: "EU",
    accent: "#4338ca",
    bg: "#eef2ff",
  },
  "eu-ai-act-2024-1689": {
    label: "EU AI Act",
    mark: "EU AI",
    accent: "#be123c",
    bg: "#fff1f2",
  },
};

const styleFor = (size: number): CSSProperties => ({
  minWidth: Math.max(size * 3.1, 98),
  minHeight: size,
  display: "inline-flex",
  alignItems: "center",
  flexShrink: 0,
});

export function FrameworkBadge({
  frameworkId,
  fallbackLabel,
  size = 32,
  className,
}: FrameworkBadgeProps) {
  const framework = FRAMEWORKS[frameworkId];
  const label = framework?.label ?? fallbackLabel ?? frameworkId;
  const mark = framework?.mark ?? label.slice(0, 4).toUpperCase();
  const accent = framework?.accent ?? "#2563eb";
  const bg = framework?.bg ?? "#eff6ff";

  return (
    <span
      style={styleFor(size)}
      className={[
        "gap-2 rounded-md border border-line bg-white px-2 py-1 text-left text-[11px] font-semibold leading-tight text-ink",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      role="img"
      aria-label={`${label} framework label; not an official logo or certification seal`}
      title={`${label} framework label; not an official logo or certification seal`}
    >
      <span
        className="inline-flex h-7 min-w-7 items-center justify-center rounded text-[9px] font-black tracking-wide"
        style={{ color: accent, background: bg }}
      >
        {mark}
      </span>
      <span className="min-w-0 truncate">{label}</span>
    </span>
  );
}
