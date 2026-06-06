"use client";

import { useControlTests, usePosture, usePostureStream } from "@/lib/api/hooks";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import { Card } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
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
    <Card className="flex h-[58px] min-w-0 flex-col justify-center p-2.5">
      <div className="text-[9px] font-black uppercase tracking-[0.11em] text-muted">
        {label}
      </div>
      <div
        className="mt-0.5 text-[20px] font-black leading-none tabular-nums"
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
    <div className="mx-auto grid w-full max-w-[1500px] gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[12px] font-black uppercase tracking-wider text-brand">
            Trust Command Center
          </div>
          <span className="sr-only">Trust Home</span>
          <h1 className="mt-1 text-[clamp(24px,2.5vw,32px)] font-black leading-tight text-ink">
            Continuous trust control plane
          </h1>
          <p className="mt-1 max-w-[720px] text-sm leading-5 text-muted">
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

      <QueryState queries={[posture]} label="posture">
        <div className="grid items-start gap-2.5 xl:grid-cols-[108px_minmax(0,1fr)]">
          <Card className="flex min-h-[92px] items-center justify-center p-1.5">
            <PostureRing
              score={p?.score ?? 0}
              state={p?.state ?? "attention_required"}
              size="compact"
            />
          </Card>
          <div className="grid min-w-0 auto-rows-[58px] content-start grid-cols-[repeat(auto-fit,minmax(124px,1fr))] gap-2">
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

        <div className="grid gap-4 lg:grid-cols-2">
          <FixNext violations={data?.violations ?? []} />
          <EvidenceTrend />
        </div>

        <ControlTestTable rows={tests.data ?? []} />
      </QueryState>
    </div>
  );
}
