"use client";

import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
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
import { Button } from "@/components/ui/button";
import { EvidenceFreshnessTrendChart } from "@/components/insights/EvidenceFreshnessTrendChart";
import { FrameworkReadinessTrendChart } from "@/components/insights/FrameworkReadinessTrendChart";
import { useInsightsTimeseries, useSnapshots } from "@/lib/api/hooks";

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function buildTrendPoints(
  snapshots: ReturnType<typeof useSnapshots>["data"],
  metrics: ReturnType<typeof useInsightsTimeseries>["data"],
) {
  const fromSnapshots = (snapshots ?? [])
    .filter((s) => s.evaluated_at && s.posture_score != null)
    .map((s) => ({
      date: fmtDate(s.evaluated_at),
      audit_score: +(s.posture_score as number).toFixed(1),
      open_violations: s.open_violation_count ?? 0,
      source: "snapshot" as const,
    }));
  if (fromSnapshots.length >= 2) {
    return fromSnapshots;
  }
  return (metrics ?? []).map((p) => ({
    date: fmtDate(p.captured_at),
    audit_score: +p.posture_score.toFixed(1),
    open_violations: p.open_violations,
    source: "metrics" as const,
  }));
}

export function AuditRoomTrendsPanel() {
  const snapshots = useSnapshots();
  const timeseries = useInsightsTimeseries(30);
  const chartData = buildTrendPoints(snapshots.data, timeseries.data);
  const loading = snapshots.isLoading || timeseries.isLoading;

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 lg:grid-cols-2">
      <Card className="overflow-hidden">
        <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
          <div>
            <CardTitle className="text-base">Audit score trend</CardTitle>
            <CardDescription>
              Posture score from frozen snapshots or captured metrics.
            </CardDescription>
          </div>
          <Button asChild size="sm" variant="default">
            <Link href="/insights">Insights</Link>
          </Button>
        </CardHeader>
        {chartData.length < 2 ? (
          <CardContent className="flex h-[200px] items-center justify-center px-4 text-center text-sm text-muted">
            {loading
              ? "Loading trend…"
              : "Capture metrics from Insights or freeze another snapshot to plot audit readiness over time."}
          </CardContent>
        ) : (
          <div className="h-[200px] w-full px-2 pb-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e9f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="audit_score"
                  name="Posture score"
                  stroke="#4f7cff"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-base">Open violations trend</CardTitle>
          <CardDescription>
            Finding count at each snapshot or metrics capture.
          </CardDescription>
        </CardHeader>
        {chartData.length < 2 ? (
          <CardContent className="flex h-[200px] items-center justify-center text-sm text-muted">
            {loading ? "Loading…" : "No trend data yet."}
          </CardContent>
        ) : (
          <div className="h-[200px] w-full px-2 pb-3">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
              >
                <defs>
                  <linearGradient
                    id="auditViolGrad"
                    x1="0"
                    x2="0"
                    y1="0"
                    y2="1"
                  >
                    <stop offset="0%" stopColor="#f87171" stopOpacity={0.35} />
                    <stop
                      offset="100%"
                      stopColor="#f87171"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e9f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                />
                <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="open_violations"
                  name="Open violations"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fill="url(#auditViolGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      </div>

      <FrameworkReadinessTrendChart />
      <EvidenceFreshnessTrendChart limit={30} />
    </div>
  );
}
