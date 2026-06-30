"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export type KpiTone = "default" | "critical" | "attention" | "ready" | "brand";

const TONE_VALUE: Record<KpiTone, string> = {
  default: "text-ink",
  critical: "text-rose-700",
  attention: "text-amber-800",
  ready: "text-emerald-700",
  brand: "text-brand",
};

const TONE_BG: Record<KpiTone, string> = {
  default: "from-white to-slate-50",
  critical: "from-rose-50 to-white",
  attention: "from-amber-50 to-white",
  ready: "from-emerald-50 to-white",
  brand: "from-blue-50 to-white",
};

const TONE_ACCENT: Record<KpiTone, string> = {
  default: "#4f7cff",
  critical: "#d92d20",
  attention: "#f79009",
  ready: "#16b364",
  brand: "#4f7cff",
};

export function KpiTile({
  label,
  value,
  detail,
  tone = "default",
  icon,
  delay = 0,
  className,
}: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: KpiTone;
  icon?: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.28 }}
      className={cn(
        "relative min-w-0 overflow-hidden rounded-xl border border-line bg-gradient-to-br p-3.5 shadow-card",
        TONE_BG[tone],
        className,
      )}
    >
      <div
        className="absolute inset-y-0 left-0 w-1 rounded-l-xl"
        style={{ background: TONE_ACCENT[tone] }}
      />
      <div className="flex items-start justify-between gap-2 pl-2">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-black uppercase tracking-wider text-muted">
            {label}
          </div>
          <div
            className={cn(
              "mt-1 text-2xl font-black leading-none tabular-nums",
              TONE_VALUE[tone],
            )}
          >
            {value}
          </div>
          {detail && (
            <div className="mt-1.5 text-xs leading-4 text-muted">{detail}</div>
          )}
        </div>
        {icon && (
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white shadow-sm"
            style={{ background: TONE_ACCENT[tone] }}
          >
            {icon}
          </div>
        )}
      </div>
    </motion.div>
  );
}
