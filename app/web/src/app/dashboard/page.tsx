"use client";

import {
  useControlTests,
  useFrameworks,
  useIngestionStatus,
  usePosture,
  usePostureStream,
} from "@/lib/api/hooks";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import { TrustLifecycle } from "@/components/dashboard/TrustLifecycle";
import { IngestionStatusPanel } from "@/components/dashboard/IngestionStatusPanel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { shortDate } from "@/lib/utils";

function stateHeadline(state?: string) {
  if (state === "ready") return "Audit-ready posture";
  if (state === "critical") return "Executive action required";
  return "Posture needs review";
}

function stateCopy(state?: string) {
  if (state === "ready") {
    return "Ready for auditor or customer sharing.";
  }
  if (state === "critical") {
    return "Assign critical owners and refresh stale proof.";
  }
  return "Review gaps before the next trust share.";
}

function ExecutiveMetric({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: string | number;
  detail: string;
  tone?: "default" | "critical" | "attention" | "ready";
}) {
  const toneClass =
    tone === "critical"
      ? "text-rose-700"
      : tone === "attention"
        ? "text-amber-800"
        : tone === "ready"
          ? "text-emerald-700"
          : "text-ink";
  return (
    <div className="min-w-0 rounded-lg border border-line bg-white p-3">
      <div className="text-[10px] font-black uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className={`mt-1 text-2xl font-black leading-none ${toneClass}`}>
        {value}
      </div>
      <div className="mt-1 text-xs leading-4 text-muted">{detail}</div>
    </div>
  );
}

export default function DashboardPage() {
  const posture = usePosture();
  const tests = useControlTests();
  const ingestion = useIngestionStatus();
  const registeredFrameworks = useFrameworks();
  const { connected } = usePostureStream();
  const data = posture.data;
  const p = data?.posture;
  const frameworks = data?.frameworks ?? [];
  const registeredCount =
    registeredFrameworks.data?.length ?? frameworks.length;
  const readyFrameworks = frameworks.filter((f) => f.score >= 85).length;
  const frameworkAvg =
    frameworks.length > 0
      ? Math.round(
          frameworks.reduce((sum, framework) => sum + framework.score, 0) /
            frameworks.length,
        )
      : 0;
  const frameworkDetail =
    frameworks.length > 0
      ? `${frameworkAvg}% avg · ${frameworks.length} monitored / ${registeredCount} registered`
      : "No framework posture yet";

  return (
    <div className="mx-auto grid w-full max-w-[1500px] gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[12px] font-black uppercase tracking-wider text-brand">
            Trust Command Center
          </div>
          <span className="sr-only">Trust Home</span>
          <h1 className="mt-1 text-[clamp(24px,2.5vw,32px)] font-black leading-tight text-ink">
            Executive trust overview
          </h1>
          <p className="mt-1 max-w-[720px] text-sm leading-5 text-muted">
            Live readiness, risk, evidence freshness, and owner action in one
            place.
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
        <Card className="overflow-hidden">
          <div className="grid lg:grid-cols-[260px_minmax(0,1fr)]">
            <div className="flex items-center gap-4 border-b border-line bg-panel p-4 lg:block lg:border-b-0 lg:border-r">
              <PostureRing
                score={p?.score ?? 0}
                state={p?.state ?? "attention_required"}
                size="default"
              />
              <div className="min-w-0 lg:mt-3">
                <div className="text-[10px] font-black uppercase tracking-wide text-muted">
                  Trust score
                </div>
                <p className="mt-1 text-xs leading-5 text-muted">
                  Audit, customer, and security readiness.
                </p>
              </div>
            </div>
            <div className="grid min-w-0 gap-4 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Current assessment
                  </div>
                  <h2 className="mt-1 text-2xl font-black leading-tight text-ink">
                    {stateHeadline(p?.state)}
                  </h2>
                  <p className="mt-1 max-w-[760px] text-sm leading-5 text-muted">
                    {stateCopy(p?.state)}
                  </p>
                </div>
                <Badge
                  tone={
                    p?.state === "ready"
                      ? "ready"
                      : p?.state === "critical"
                        ? "critical"
                        : "attention"
                  }
                >
                  {p?.state === "ready" ? "shareable" : "internal review"}
                </Badge>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <ExecutiveMetric
                  label="Framework readiness"
                  value={`${readyFrameworks} ready`}
                  detail={frameworkDetail}
                  tone={
                    frameworks.length > 0 &&
                    readyFrameworks === frameworks.length
                      ? "ready"
                      : "attention"
                  }
                />
                <ExecutiveMetric
                  label="Control tests"
                  value={p?.control_count ?? 0}
                  detail={`${p?.failed_control_test_count ?? 0} failing tests require work`}
                  tone={
                    (p?.failed_control_test_count ?? 0) > 0
                      ? "critical"
                      : "ready"
                  }
                />
                <ExecutiveMetric
                  label="Open risk"
                  value={`${p?.critical_violation_count ?? 0} critical`}
                  detail={`${p?.open_violation_count ?? 0} open findings need owners`}
                  tone={
                    (p?.critical_violation_count ?? 0) > 0
                      ? "critical"
                      : (p?.open_violation_count ?? 0) > 0
                        ? "attention"
                        : "ready"
                  }
                />
                <ExecutiveMetric
                  label="Evidence freshness"
                  value={`${p?.stale_evidence_count ?? 0} stale`}
                  detail={`${p?.stale_control_count ?? 0} controls need refreshed proof`}
                  tone={
                    (p?.stale_evidence_count ?? 0) > 0 ||
                    (p?.stale_control_count ?? 0) > 0
                      ? "attention"
                      : "ready"
                  }
                />
              </div>
            </div>
          </div>
        </Card>

        <QueryState queries={ingestion} label="ingestion status">
          <IngestionStatusPanel status={ingestion.data} />
        </QueryState>

        <ReadinessGrid
          frameworks={frameworks}
          catalog={registeredFrameworks.data ?? []}
        />

        <div className="grid gap-4 lg:grid-cols-2">
          <FixNext violations={data?.violations ?? []} />
          <EvidenceTrend />
        </div>

        <ControlTestTable rows={tests.data ?? []} />

        <TrustLifecycle posture={p} assessmentHash={data?.assessment_hash} />
      </QueryState>
    </div>
  );
}
