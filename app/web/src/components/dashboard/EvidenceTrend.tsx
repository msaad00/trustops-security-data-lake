"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useInsightsTimeseries } from "@/lib/api/hooks";

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function EvidenceTrend() {
  const timeseries = useInsightsTimeseries(14);
  const points = timeseries.data ?? [];
  const data = points.map((p) => ({
    date: fmtDate(p.captured_at),
    score: +p.posture_score.toFixed(1),
  }));

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Posture trend</CardTitle>
        <CardDescription>
          Daily posture score from captured snapshots.
        </CardDescription>
      </CardHeader>
      {data.length < 2 ? (
        <CardContent className="flex h-[180px] items-center justify-center text-center text-sm text-muted">
          {timeseries.isLoading
            ? "Loading trend..."
            : timeseries.isError
              ? "Trend is unavailable right now."
              : "Posture trend appears once daily snapshots accumulate. Capture one from Insights or schedule POST /api/v1/insights/capture."}
        </CardContent>
      ) : (
        <div className="h-[180px] w-full px-2 pb-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
            >
              <defs>
                <linearGradient id="postureGrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#4f7cff" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#4f7cff" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#64748b" tickLine={false} />
              <YAxis
                stroke="#64748b"
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                formatter={(v: number) => [`${v}%`, "posture"]}
                contentStyle={{
                  background: "#101623",
                  color: "#fff",
                  border: 0,
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#4f7cff"
                strokeWidth={2.5}
                fill="url(#postureGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
