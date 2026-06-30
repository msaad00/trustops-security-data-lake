"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FrameworkPosture } from "@/lib/api/types";
import { frameworkVisual, resolveFrameworkId } from "@/lib/framework-visuals";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function color(score: number) {
  if (score >= 85) return "#16b364";
  if (score >= 65) return "#f79009";
  return "#d92d20";
}

export function FrameworkBars({
  frameworks,
}: {
  frameworks: FrameworkPosture[];
}) {
  const data = frameworks.map((f) => {
    const visual = frameworkVisual(resolveFrameworkId(f.framework), f.framework);
    return {
      name: visual.label,
      score: Math.round(f.score),
      fail: f.failing_control_count,
      color: color(f.score),
      accent: visual.accent,
    };
  });

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Framework scoreboard</CardTitle>
        <CardDescription>
          Per-program readiness — Vanta/Drata-style compliance bars with failing
          control overlay.
        </CardDescription>
      </CardHeader>
      <div className="h-[230px] w-full px-4 pb-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 12, left: 0, bottom: 4 }}
          >
            <CartesianGrid stroke="#eef2f7" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              stroke="#a0aec0"
            />
            <YAxis
              type="category"
              dataKey="name"
              width={140}
              stroke="#475569"
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(79,124,255,0.06)" }}
              formatter={(v: number) => [`${v}%`, "score"]}
              contentStyle={{
                background: "#101623",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar dataKey="score" radius={[6, 6, 6, 6]} barSize={18}>
              {data.map((d) => (
                <Cell key={d.name} fill={d.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
