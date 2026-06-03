"use client";

import { useControlTests, usePosture, usePostureStream } from "@/lib/api/hooks";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import { Card } from "@/components/ui/card";
import { shortDate } from "@/lib/utils";

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: string;
}) {
  return (
    <Card className="p-4">
      <div className="text-[11px] font-black uppercase tracking-wider text-muted">
        {label}
      </div>
      <div
        className="mt-1.5 text-3xl font-black leading-none tabular-nums"
        style={tone ? { color: tone } : undefined}
      >
        {value}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const posture = usePosture();
  const tests = useControlTests();
  const { connected } = usePostureStream();
  const data = posture.data;
  const p = data?.posture;

  return (
    <div className="grid gap-6 px-7 py-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[12px] font-black uppercase tracking-wider text-brand">
            Trust
          </div>
          <h1 className="mt-1 text-3xl font-black text-ink">Trust Home</h1>
          <p className="mt-2 max-w-[760px] text-sm text-muted">
            Continuous posture computed from normalized evidence,
            controls-as-code rules, source freshness, and hashed snapshots.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black ${connected ? "text-emerald-600" : "text-amber-600"}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "animate-pulse bg-emerald-500" : "bg-amber-500"}`}
            />
            {connected ? "Live" : "Polling"}
          </span>
          {data?.evaluated_at && (
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-500">
              as of {shortDate(data.evaluated_at)}
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Card className="flex items-center justify-center p-4">
          <PostureRing
            score={p?.score ?? 0}
            state={p?.state ?? "attention_required"}
          />
        </Card>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
          <Stat label="Frameworks" value={p?.framework_count ?? 0} />
          <Stat label="Controls" value={p?.control_count ?? 0} />
          <Stat
            label="Open violations"
            value={p?.open_violation_count ?? 0}
            tone={(p?.open_violation_count ?? 0) > 0 ? "#b54708" : undefined}
          />
          <Stat
            label="Critical"
            value={p?.critical_violation_count ?? 0}
            tone={
              (p?.critical_violation_count ?? 0) > 0 ? "#d92d20" : undefined
            }
          />
          <Stat
            label="Stale controls"
            value={p?.stale_control_count ?? 0}
            tone={(p?.stale_control_count ?? 0) > 0 ? "#b54708" : undefined}
          />
        </div>
      </div>

      <ReadinessGrid frameworks={data?.frameworks ?? []} />

      <div className="grid gap-5 lg:grid-cols-2">
        <FixNext violations={data?.violations ?? []} />
        <EvidenceTrend />
      </div>

      <ControlTestTable rows={tests.data ?? []} />
    </div>
  );
}
