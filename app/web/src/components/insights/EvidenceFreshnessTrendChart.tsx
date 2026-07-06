"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useInsightsTimeseries } from "@/lib/api/hooks";
import { fmtChartDate, TOOLTIP_STYLE } from "./chart-utils";

export function EvidenceFreshnessTrendChart({
  limit = 90,
}: {
  limit?: number;
}) {
  const timeseries = useInsightsTimeseries(limit);
  const points = timeseries.data ?? [];

  const chartData = points.map((p) => ({
    date: fmtChartDate(p.captured_at),
    fresh_pct: +(p.evidence_fresh_pct * 100).toFixed(1),
    stale_controls: p.stale_controls,
  }));

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Evidence freshness trend</CardTitle>
        <CardDescription>
          Fresh evidence percentage and stale control count at each captured
          metrics snapshot.
        </CardDescription>
      </CardHeader>
      <div className="h-[240px] w-full px-2 pb-4">
        {timeseries.isLoading ? (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            Loading freshness trend…
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            No metrics snapshots yet — capture a point to plot evidence
            freshness over time.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
            >
              <defs>
                <linearGradient id="freshGrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e9f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis
                yAxisId="left"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="fresh_pct"
                name="Fresh evidence %"
                stroke="#22c55e"
                strokeWidth={2}
                fill="url(#freshGrad)"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="stale_controls"
                name="Stale controls"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
