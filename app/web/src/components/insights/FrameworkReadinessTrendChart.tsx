"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
import { useInsightsFrameworkTrends } from "@/lib/api/hooks";
import {
  fmtChartDate,
  FRAMEWORK_LINE_COLORS,
  TOOLTIP_STYLE,
} from "./chart-utils";

export function FrameworkReadinessTrendChart() {
  const trends = useInsightsFrameworkTrends(90);
  const frameworks = trends.data?.frameworks ?? [];
  const points = trends.data?.points ?? [];

  const chartData = points.map((p) => {
    const row: Record<string, string | number> = {
      date: fmtChartDate(p.at),
    };
    for (const fw of frameworks) {
      row[fw] = p.frameworks[fw] ?? null;
    }
    return row;
  });

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Framework readiness over time</CardTitle>
        <CardDescription>
          Per-framework compliance scores from frozen snapshots and the live
          posture baseline.
        </CardDescription>
      </CardHeader>
      <div className="h-[260px] w-full px-2 pb-4">
        {trends.isLoading ? (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            Loading framework trends…
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            No snapshot history yet — freeze a snapshot from the audit room or
            capture metrics to start plotting framework readiness.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e9f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {frameworks.map((fw, index) => (
                <Line
                  key={fw}
                  type="monotone"
                  dataKey={fw}
                  name={fw}
                  stroke={
                    FRAMEWORK_LINE_COLORS[index % FRAMEWORK_LINE_COLORS.length]
                  }
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
