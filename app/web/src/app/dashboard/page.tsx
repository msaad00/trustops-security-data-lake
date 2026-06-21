"use client";

import { useControlTests, usePosture, usePostureStream } from "@/lib/api/hooks";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import { TrustLifecycle } from "@/components/dashboard/TrustLifecycle";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { shortDate } from "@/lib/utils";

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
        <Card className="grid gap-4 p-4 lg:grid-cols-[112px_minmax(0,1fr)_auto] lg:items-center">
          <div className="flex justify-start lg:justify-center">
            <PostureRing
              score={p?.score ?? 0}
              state={p?.state ?? "attention_required"}
              size="compact"
            />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-black uppercase tracking-wide text-muted">
              Current assessment
            </div>
            <h2 className="mt-1 text-xl font-black leading-tight text-ink">
              {p?.state === "critical"
                ? "Immediate control work required"
                : p?.state === "ready"
                  ? "Posture is ready"
                  : "Posture needs review"}
            </h2>
            <p className="mt-1 max-w-[720px] text-sm leading-5 text-muted">
              Score is a rollup of framework readiness, failed control tests,
              stale evidence, and open violations. The map below shows which
              system surface owns each step.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 lg:max-w-[340px] lg:justify-end">
            <Badge
              tone={(p?.failed_control_test_count ?? 0) ? "critical" : "ready"}
            >
              {p?.failed_control_test_count ?? 0} failing tests
            </Badge>
            <Badge
              tone={(p?.critical_violation_count ?? 0) ? "critical" : "ready"}
            >
              {p?.critical_violation_count ?? 0} critical violations
            </Badge>
            <Badge tone={(p?.stale_control_count ?? 0) ? "attention" : "ready"}>
              {p?.stale_control_count ?? 0} stale controls
            </Badge>
          </div>
        </Card>

        <TrustLifecycle posture={p} assessmentHash={data?.assessment_hash} />

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
