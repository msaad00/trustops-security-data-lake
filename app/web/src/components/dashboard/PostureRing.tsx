"use client";

import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";

const TONE: Record<string, string> = {
  ready: "#16b364",
  attention_required: "#f79009",
  critical: "#d92d20",
};

const LABEL: Record<string, string> = {
  ready: "score",
  attention_required: "score",
  critical: "score",
};

export function PostureRing({
  score,
  state,
  size = "default",
  dark = false,
}: {
  score: number;
  state: string;
  size?: "compact" | "summary" | "default";
  dark?: boolean;
}) {
  const value = Math.round(score);
  const color = TONE[state] ?? "#f79009";
  const isSummary = size === "summary";
  const isCompact = size === "compact";
  return (
    <div
      role="img"
      aria-label={`Assessment score ${value} out of 100`}
      className={
        isSummary
          ? "relative h-[104px] w-[104px]"
          : isCompact
            ? "relative h-[78px] w-[78px]"
            : "relative h-[208px] w-[208px]"
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          innerRadius="76%"
          outerRadius="100%"
          data={[{ value }]}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            dataKey="value"
            cornerRadius={14}
            fill={color}
            background={{ fill: dark ? "#ffffff18" : "#eef2f7" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span
          style={{ color: dark ? "#ffffff" : undefined }}
          className={
            isSummary
              ? "text-[42px] font-semibold leading-none text-ink tabular-nums"
              : isCompact
                ? "text-[22px] font-black leading-none text-ink"
                : "text-[52px] font-black leading-none text-ink"
          }
        >
          {value}
        </span>
        <span
          className={
            isCompact
              ? "mt-1 rounded-full px-2 py-0.5 text-[9px] font-black uppercase tracking-wide"
              : "mt-1 rounded-full px-2.5 py-0.5 text-[11px] font-black uppercase tracking-wide"
          }
          style={{
            color: dark ? "#cbd5e1" : "#475467",
            background: dark ? "#ffffff10" : "#f1f5f9",
          }}
        >
          {isSummary ? "/ 100" : (LABEL[state] ?? state)}
        </span>
      </div>
    </div>
  );
}
