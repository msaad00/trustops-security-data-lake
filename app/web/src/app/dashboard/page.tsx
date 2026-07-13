"use client";

import {
  AlertTriangle,
  ClipboardCheck,
  Layers,
  ShieldCheck,
} from "lucide-react";
import {
  useControlTests,
  useFrameworks,
  useIngestionStatus,
  usePosture,
  usePostureStream,
} from "@/lib/api/hooks";
import { DashboardStripsRow } from "@/components/dashboard/DashboardStripsRow";
import { TrustHomeQuickLinks } from "@/components/dashboard/TrustHomeQuickLinks";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ComplianceOverview } from "@/components/dashboard/ComplianceOverview";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
import { FrameworkBars } from "@/components/dashboard/FrameworkBars";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import { TrustLifecycle } from "@/components/dashboard/TrustLifecycle";
import { IngestionStatusPanel } from "@/components/dashboard/IngestionStatusPanel";
import { EvalRunsStrip } from "@/components/dashboard/EvalRunsStrip";
import { DataPipelineStrip } from "@/components/dashboard/DataPipelineStrip";
import { KpiTile } from "@/components/ui/KpiTile";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
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
      ? `${frameworkAvg}% avg · ${frameworks.length}/${registeredCount} frameworks`
      : "No framework posture yet";
  const ingestionNeedsAttention =
    ingestion.data?.state !== "active" ||
    Boolean(ingestion.data?.recommended_actions?.length) ||
    Boolean(ingestion.data?.scale?.eval_overdue);
  const ingestionDescription = ingestionNeedsAttention
    ? (ingestion.data?.recommended_actions?.[0]?.reason ??
      "Connector health or control eval needs attention")
    : "Source sync health and control eval runs";

  return (
    <div className="mx-auto grid w-full max-w-[1600px] gap-2 px-3 py-2 sm:px-4 lg:px-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[12px] font-black uppercase tracking-wider text-brand">
            Trust Command Center
          </div>
          <h1 className="ui-page-title mt-0.5">Executive trust overview</h1>
          <p className="text-sm text-muted">
            Live readiness, control monitoring, evidence freshness, and owner
            action — managed GRC-style continuous compliance at a glance.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-1 text-xs font-medium ${connected ? "text-emerald-700" : "text-amber-700"}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500" : "bg-amber-500"}`}
            />
            {connected ? "Live" : "Polling"}
          </span>
          {data?.evaluated_at ? (
            <span className="rounded-md border border-line bg-surface px-2 py-1 text-xs text-muted">
              {shortDate(data.evaluated_at)}
            </span>
          ) : null}
        </div>
      </div>

      <TrustHomeQuickLinks />

      <QueryState queries={[posture]} label="posture">
        <Card className="overflow-hidden border-line shadow-card">
          <div className="grid lg:grid-cols-[minmax(220px,260px)_minmax(0,1fr)]">
            <div className="flex items-center gap-4 border-b border-line bg-gradient-to-b from-slate-50 to-surface p-3 lg:block lg:border-b-0 lg:border-r">
              <PostureRing
                score={p?.score ?? 0}
                state={p?.state ?? "attention_required"}
                size="default"
              />
              <div className="min-w-0 lg:mt-2">
                <div className="ui-label">Trust score</div>
                <p className="mt-1 text-xs leading-4 text-muted">
                  Weighted across frameworks, tests, and evidence freshness.
                </p>
              </div>
            </div>
            <div className="grid min-w-0 gap-3 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="ui-label">Current assessment</div>
                  <h2 className="mt-0.5 text-xl font-black leading-tight text-ink">
                    {stateHeadline(p?.state)}
                  </h2>
                  <p className="mt-1 max-w-[720px] text-sm text-muted">
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
                  {stateHeadline(p?.state)}
                </Badge>
              </div>
              <ComplianceOverview frameworks={frameworks} />
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                <KpiTile
                  label="Framework readiness"
                  value={`${readyFrameworks} ready`}
                  detail={frameworkDetail}
                  tone={
                    frameworks.length > 0 &&
                    readyFrameworks === frameworks.length
                      ? "ready"
                      : "attention"
                  }
                  icon={<Layers className="h-3.5 w-3.5" />}
                />
                <KpiTile
                  label="Control tests"
                  value={p?.control_count ?? 0}
                  detail={`${p?.failed_control_test_count ?? 0} failing`}
                  tone={
                    (p?.failed_control_test_count ?? 0) > 0
                      ? "critical"
                      : "ready"
                  }
                  icon={<ClipboardCheck className="h-3.5 w-3.5" />}
                />
                <KpiTile
                  label="Open risk"
                  value={`${p?.critical_violation_count ?? 0} critical`}
                  detail={`${p?.open_violation_count ?? 0} open findings`}
                  tone={
                    (p?.critical_violation_count ?? 0) > 0
                      ? "critical"
                      : (p?.open_violation_count ?? 0) > 0
                        ? "attention"
                        : "ready"
                  }
                  icon={<AlertTriangle className="h-3.5 w-3.5" />}
                />
                <KpiTile
                  label="Evidence freshness"
                  value={`${p?.stale_evidence_count ?? 0} stale`}
                  detail={`${p?.stale_control_count ?? 0} controls need proof`}
                  tone={
                    (p?.stale_evidence_count ?? 0) > 0 ||
                    (p?.stale_control_count ?? 0) > 0
                      ? "attention"
                      : "ready"
                  }
                  icon={<ShieldCheck className="h-3.5 w-3.5" />}
                />
              </div>
            </div>
          </div>
        </Card>

        <ReadinessGrid
          frameworks={frameworks}
          catalog={registeredFrameworks.data ?? []}
        />

        <div className="grid gap-2 xl:grid-cols-2">
          <FixNext violations={data?.violations ?? []} />
          <EvidenceTrend />
        </div>

        <DashboardStripsRow />

        <QueryState queries={[ingestion]} label="ingestion status">
          <CollapsibleCard
            storageKey="dashboard-ingestion"
            defaultOpen={ingestionNeedsAttention}
            title="Source sync & control eval"
            description={ingestionDescription}
            actions={
              ingestionNeedsAttention ? (
                <Badge tone="attention">Action needed</Badge>
              ) : undefined
            }
            contentClassName="p-0"
          >
            <IngestionStatusPanel status={ingestion.data} embedded />
            <div className="border-t border-line px-3 py-2">
              <EvalRunsStrip embedded />
            </div>
          </CollapsibleCard>
        </QueryState>

        <DataPipelineStrip />

        <CollapsibleCard
          storageKey="dashboard-framework-bars"
          defaultOpen={false}
          title="Framework scoreboard"
          description="Per-program compliance bars"
          contentClassName="p-0"
        >
          <FrameworkBars frameworks={frameworks} embedded />
        </CollapsibleCard>

        <CollapsibleCard
          storageKey="dashboard-control-tests"
          defaultOpen={(p?.failed_control_test_count ?? 0) > 0}
          title="Control test results"
          description="Continuous control monitoring — failing and warning tests"
          contentClassName="p-0"
        >
          <ControlTestTable rows={tests.data ?? []} />
        </CollapsibleCard>

        <CollapsibleCard
          storageKey="dashboard-trust-lifecycle"
          defaultOpen={false}
          title="Trust lifecycle"
          description="Assessment hash and share readiness"
          contentClassName="p-3"
        >
          <TrustLifecycle posture={p} assessmentHash={data?.assessment_hash} />
        </CollapsibleCard>
      </QueryState>
    </div>
  );
}
