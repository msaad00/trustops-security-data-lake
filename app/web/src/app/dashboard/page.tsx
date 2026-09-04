"use client";

import { useState } from "react";
import Link from "next/link";
import { ClipboardCheck, FileCheck2, ShieldCheck } from "lucide-react";
import {
  useControlTests,
  useFrameworks,
  useIngestionStatus,
  usePosture,
  usePostureStream,
} from "@/lib/api/hooks";
import { DashboardStripsRow } from "@/components/dashboard/DashboardStripsRow";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ComplianceOverview } from "@/components/dashboard/ComplianceOverview";
import { TrustSignalFlow } from "@/components/dashboard/TrustSignalFlow";
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

const DASHBOARD_TABS = ["Posture", "Sources", "Proof"] as const;
type DashboardTab = (typeof DASHBOARD_TABS)[number];

function stateHeadline(state?: string) {
  if (state === "ready") return "Proof ready to share";
  if (state === "critical") return "Critical gaps need owners";
  return "Evidence review needed";
}

function stateCopy(state?: string) {
  if (state === "ready") {
    return "Current evidence is ready for auditor or customer review.";
  }
  if (state === "critical") {
    return "Assign the highest-risk gaps and refresh stale proof.";
  }
  return "Review evidence gaps before the next trust share.";
}

function stateBadge(state?: string) {
  if (state === "ready") return "Ready";
  if (state === "critical") return "Critical";
  return "Needs review";
}

function formatPassRate(rate: number | null | undefined) {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

export default function DashboardPage() {
  const [activeDashboardTab, setActiveDashboardTab] =
    useState<DashboardTab>("Posture");
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
  const sourceCount = ingestion.data?.summary.source_count ?? 0;
  const connectorCount = ingestion.data?.summary.connector_count ?? 0;
  const enabledConnectors = ingestion.data?.summary.enabled_connectors ?? 0;
  const evidenceCount = ingestion.data?.summary.evidence_count ?? 0;
  const proofReady = Boolean(ingestion.data?.proof?.proof_pack_exists);
  const controlEvalReady = Boolean(ingestion.data?.eval_accuracy?.has_tests);
  const passRate = ingestion.data?.eval_accuracy?.pass_rate;
  const ingestionNeedsAttention =
    ingestion.data?.state !== "active" ||
    Boolean(ingestion.data?.recommended_actions?.length) ||
    Boolean(ingestion.data?.scale?.eval_overdue);
  const ingestionDescription = ingestionNeedsAttention
    ? (ingestion.data?.recommended_actions?.[0]?.reason ??
      "Connector health or control eval needs attention")
    : "Source sync health and control eval runs";
  const dashboardTabCopy: Record<DashboardTab, string> = {
    Posture: `${frameworks.length}/${registeredCount} frameworks · ${p?.failed_control_test_count ?? 0} failing tests`,
    Sources: `${enabledConnectors}/${connectorCount} connectors enabled · ${sourceCount} sources`,
    Proof: proofReady
      ? "Security data lake proof export is ready"
      : "Run sync and eval to prepare proof export",
  };

  return (
    <div className="ui-page-canvas mx-auto grid min-h-full w-full max-w-[1680px] gap-3 px-3 py-3 sm:px-4 lg:px-6 lg:py-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[12px] font-black uppercase tracking-[0.14em] text-brand">
            Assessment status
          </div>
          <h1 className="ui-page-title mt-0.5">Dashboard</h1>
          <p className="text-sm text-muted">
            Current posture from ingested evidence, control evaluations, and
            saved proof exports.
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

      <QueryState queries={[posture, ingestion]} label="overview">
        <section
          aria-label="Assessment summary"
          className="ui-command-center overflow-hidden"
        >
          <div className="relative z-10 flex flex-wrap items-start justify-between gap-3 border-b border-white/10 px-4 py-3 sm:px-5">
            <div>
              <div className="text-[10px] font-black uppercase tracking-[0.2em] text-cyan-300">
                Assessment summary
              </div>
              <p className="mt-1 max-w-2xl text-sm text-slate-300">
                Current sources, control results, findings, and export status.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold">
              <span className="rounded-full border border-white/10 bg-white/[0.06] px-2.5 py-1 text-slate-300">
                {frameworks.length}/{registeredCount} frameworks assessed
              </span>
              <span className="rounded-full border border-cyan-300/20 bg-cyan-300/[0.08] px-2.5 py-1 text-cyan-200">
                {enabledConnectors}/{connectorCount} connectors enabled
              </span>
            </div>
          </div>
          <div className="relative z-10 grid lg:grid-cols-[minmax(210px,240px)_minmax(0,1fr)] xl:grid-cols-[minmax(210px,240px)_minmax(0,0.9fr)_minmax(320px,0.82fr)]">
            <div className="flex items-center gap-4 border-b border-white/10 bg-white/[0.025] p-4 lg:block lg:border-b-0 lg:border-r lg:border-white/10">
              <PostureRing
                score={p?.score ?? 0}
                state={p?.state ?? "attention_required"}
                size="default"
                inverse
              />
              <div className="min-w-0 lg:mt-2">
                <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">
                  Trust score
                </div>
                <p className="mt-1 text-xs leading-4 text-slate-400">
                  Calculated from the current gold assessment.
                </p>
              </div>
            </div>
            <div className="grid min-w-0 gap-4 border-b border-white/10 p-4 xl:border-b-0 xl:border-r xl:border-white/10">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">
                    Current assessment
                  </div>
                  <h2 className="mt-1 text-xl font-black leading-tight text-white sm:text-2xl">
                    {stateHeadline(p?.state)}
                  </h2>
                  <p className="mt-1 max-w-[720px] text-sm leading-5 text-slate-300">
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
                  {stateBadge(p?.state)}
                </Badge>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-white/[0.055] p-3 shadow-inner">
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">
                    Control pass rate
                  </div>
                  <div className="mt-1 text-2xl font-black text-white">
                    {formatPassRate(passRate)}
                  </div>
                  <p className="text-xs text-slate-400">
                    {controlEvalReady
                      ? `${ingestion.data?.eval_accuracy?.failing ?? 0} failing tests`
                      : "run control eval"}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.055] p-3 shadow-inner">
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">
                    Open findings
                  </div>
                  <div className="mt-1 text-2xl font-black text-white">
                    {p?.open_violation_count ?? 0}
                  </div>
                  <p className="text-xs text-slate-400">
                    {p?.critical_violation_count ?? 0} critical
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.055] p-3 shadow-inner">
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">
                    Proof export
                  </div>
                  <div className="mt-1 text-2xl font-black text-white">
                    {proofReady ? "ready" : "pending"}
                  </div>
                  <p className="text-xs text-slate-400">
                    {evidenceCount} raw evidence rows
                  </p>
                </div>
              </div>
            </div>
            <div className="min-w-0 p-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">
                    Framework posture
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Worst programs first, scroll to compare.
                  </p>
                </div>
                <Badge tone="info">
                  {frameworks.length}/{registeredCount}
                </Badge>
              </div>
              <div className="mt-3">
                <ComplianceOverview frameworks={frameworks} inverse />
              </div>
            </div>
          </div>
          <TrustSignalFlow
            sourceCount={sourceCount}
            enabledConnectors={enabledConnectors}
            connectorCount={connectorCount}
            passRate={passRate}
            failingTests={ingestion.data?.eval_accuracy?.failing ?? 0}
            openFindings={p?.open_violation_count ?? 0}
            criticalFindings={p?.critical_violation_count ?? 0}
            proofReady={proofReady}
            evidenceCount={evidenceCount}
          />
        </section>

        <div className="rounded-lg border border-line bg-surface p-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div
              aria-label="Dashboard view"
              className="grid min-w-[min(100%,28rem)] grid-cols-3 rounded-lg border border-line bg-panel p-1"
              role="tablist"
            >
              {DASHBOARD_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={activeDashboardTab === tab}
                  className={`rounded-md px-3 py-1.5 text-xs font-black ${
                    activeDashboardTab === tab
                      ? "bg-brand text-white"
                      : "text-muted hover:bg-surfaceMuted"
                  }`}
                  onClick={() => setActiveDashboardTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="min-w-0 text-xs font-semibold text-muted">
              {dashboardTabCopy[activeDashboardTab]}
            </div>
          </div>
        </div>

        {activeDashboardTab === "Sources" && (
          <div className="grid gap-2">
            <IngestionStatusPanel status={ingestion.data} embedded />
            <CollapsibleCard
              storageKey="dashboard-eval-runs"
              defaultOpen={ingestionNeedsAttention}
              title="Evaluation cadence"
              description={ingestionDescription}
              actions={
                ingestionNeedsAttention ? (
                  <Badge tone="attention">Action needed</Badge>
                ) : undefined
              }
              contentClassName="p-0"
            >
              <EvalRunsStrip embedded limit={4} />
            </CollapsibleCard>
          </div>
        )}

        {activeDashboardTab === "Posture" && (
          <div className="grid gap-2 xl:grid-cols-[minmax(0,1.05fr)_minmax(24rem,0.95fr)]">
            <ReadinessGrid
              frameworks={frameworks}
              catalog={registeredFrameworks.data ?? []}
            />
            <div className="grid min-w-0 gap-2 content-start">
              <FixNext violations={data?.violations ?? []} />
              <FrameworkBars frameworks={frameworks} />
              <CollapsibleCard
                storageKey="dashboard-control-tests"
                defaultOpen={false}
                title="Control test results"
                description="Deterministic checks from normalized evidence"
                contentClassName="p-0"
              >
                <ControlTestTable rows={tests.data ?? []} />
              </CollapsibleCard>
            </div>
          </div>
        )}

        {activeDashboardTab === "Proof" && (
          <div className="grid gap-2">
            <div className="grid gap-2 md:grid-cols-3">
              <KpiTile
                label="Proof export"
                value={proofReady ? "ready" : "pending"}
                detail={
                  proofReady
                    ? `${ingestion.data?.proof?.evidence_count ?? 0} evidence rows in latest pack`
                    : "sync and evaluate to prepare export"
                }
                tone={proofReady ? "ready" : "attention"}
                icon={<FileCheck2 className="h-3.5 w-3.5" />}
              />
              <KpiTile
                label="Framework posture"
                value={`${frameworks.length}/${registeredCount}`}
                detail="mapped frameworks in the current assessment"
                tone="brand"
                icon={<ClipboardCheck className="h-3.5 w-3.5" />}
              />
              <KpiTile
                label="Assessment hash"
                value={data?.assessment_hash?.slice(0, 8) ?? "—"}
                detail="gold snapshot chain anchor for reviewers"
                tone={data?.assessment_hash ? "ready" : "default"}
                icon={<ShieldCheck className="h-3.5 w-3.5" />}
              />
            </div>
            <Card className="overflow-hidden p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="ui-label">Security data lake</div>
                  <h2 className="mt-0.5 text-base font-black text-ink">
                    Raw collections and evaluated gold outputs
                  </h2>
                  <p className="mt-1 max-w-3xl text-sm leading-5 text-muted">
                    Trust Data Lake keeps raw connector evidence separate from
                    evaluated posture so reports, audit-room exports, and cloud
                    analytics can all read the same defensible state.
                  </p>
                </div>
                <Link href="/audit-room">
                  <Badge tone="info">Open audit room</Badge>
                </Link>
              </div>
              <div className="mt-3">
                <ComplianceOverview frameworks={frameworks} />
              </div>
            </Card>
            <TrustLifecycle
              posture={p}
              assessmentHash={data?.assessment_hash}
            />
          </div>
        )}

        <CollapsibleCard
          storageKey="dashboard-operational-detail"
          defaultOpen={false}
          title="Operational detail"
          description="Source health, trends, ingestion internals, and assessment provenance"
          contentClassName="grid gap-2 p-3"
        >
          <EvidenceTrend />
          <DashboardStripsRow />
          <DataPipelineStrip />
          <TrustLifecycle posture={p} assessmentHash={data?.assessment_hash} />
        </CollapsibleCard>
      </QueryState>
    </div>
  );
}
