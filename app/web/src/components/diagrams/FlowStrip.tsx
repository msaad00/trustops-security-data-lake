"use client";

import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface FlowStep {
  step: string;
  title: string;
  detail: string;
  tone?: "brand" | "lake" | "assess" | "share" | "neutral";
}

const TONE: Record<NonNullable<FlowStep["tone"]>, string> = {
  brand: "bg-brand/10 text-brand ring-brand/20",
  lake: "bg-cyan-50 text-cyan-800 ring-cyan-200",
  assess: "bg-amber-50 text-amber-900 ring-amber-200",
  share: "bg-violet-50 text-violet-800 ring-violet-200",
  neutral: "bg-panel text-ink ring-line",
};

export function FlowStrip({
  steps,
  className,
}: {
  steps: FlowStep[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-2 lg:flex-row lg:items-stretch",
        className,
      )}
    >
      {steps.map((item, index) => (
        <div
          key={item.step}
          className="flex min-w-0 flex-1 items-stretch gap-2"
        >
          <div className="grid min-h-0 min-w-0 flex-1 grid-cols-[auto_minmax(0,1fr)] gap-3 overflow-hidden rounded-xl border border-line bg-white p-3 shadow-card">
            <span
              className={cn(
                "grid h-9 w-9 shrink-0 place-items-center rounded-lg text-[10px] font-black ring-1",
                TONE[item.tone ?? "neutral"],
              )}
            >
              {item.step}
            </span>
            <span className="min-w-0 overflow-hidden">
              <span className="block truncate text-sm font-black text-ink">
                {item.title}
              </span>
              <span className="mt-0.5 line-clamp-2 text-xs leading-5 text-muted">
                {item.detail}
              </span>
            </span>
          </div>
          {index < steps.length - 1 && (
            <ArrowRight
              className="hidden shrink-0 self-center text-muted lg:block lg:h-4 lg:w-4"
              aria-hidden
            />
          )}
        </div>
      ))}
    </div>
  );
}
