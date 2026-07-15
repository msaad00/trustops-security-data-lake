"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ClipboardCheck,
  Database,
  FileCheck2,
  RefreshCw,
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

const DASHBOARD_TABS = ["Sources", "Controls", "Proof"] as const;
type DashboardTab = (typeof DASHBOARD_TABS)[number];

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

function formatPassRate(rate: number | null | undefined) {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

export default function DashboardPage() {
  const [activeDashboardTab, setActiveDashboardTab] =
    useState<DashboardTab>("Sources");
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
    Sources: `${enabledConnectors}/${connectorCount} connectors enabled · ${sourceCount} sources`,
    Controls: `${p?.failed_control_test_count ?? 0} failing tests · ${p?.open_violation_count ?? 0} findings`,
    Proof: proofReady
      ? "Security data lake proof export is ready"
      : "Run sync and eval to prepare proof export",
  };
  const loopStages = [
    {
      label: "Connected sources",
      value: `${enabledConnectors}/${connectorCount}`,
      detail:
        sourceCount > 0
          ? `${sourceCount} source${sourceCount === 1 ? "" : "s"} sending evidence`
          : "connect read-only sources",
      Icon: Database,
      done: enabledConnectors > 0,
    },
    {
      label: "Raw evidence",
      value: evidenceCount,
      detail:
        evidenceCount > 0
          ? "bronze collection landed"
          : "run first source sync",
      Icon: RefreshCw,
      done: evidenceCount > 0,
    },
    {
      label: "Control eval",
      value: formatPassRate(passRate),
      detail: controlEvalReady
        ? `${ingestion.data?.eval_accuracy?.failing ?? 0} failing tests`
        : "materialize gold controls",
      Icon: ShieldCheck,
      done: controlEvalReady,
    },
    {
      label: "Proof export",
      value: proofReady ? "ready" : "pending",
      detail: "Security data lake gold + report",
      Icon: FileCheck2,
      done: proofReady,
    },
  ] as const;

  return (
    <div className="mx-auto grid w-full max-w-[1600px] gap-2 px-3 py-2 sm:px-4 lg:px-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[12px] font-black uppercase tracking-wider text-brand">
            TrustOps overview
          </div>
          <h1 className="ui-page-title mt-0.5">Executive trust overview</h1>
          <p className="text-sm text-muted">
            Evidence-driven posture from connected sources, deterministic
            controls, and proof exports.
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
        <Card className="overflow-hidden border-line shadow-card">
          <div className="grid xl:grid-cols-[minmax(230px,280px)_minmax(0,1fr)]">
            <div className="flex items-center gap-4 border-b border-line bg-slate-50 p-3 xl:block xl:border-b-0 xl:border-r">
              <PostureRing
                score={p?.score ?? 0}
                state={p?.state ?? "attention_required"}
                size="default"
              />
              <div className="min-w-0 xl:mt-2">
                <div className="ui-label">Trust score</div>
                <p className="mt-1 text-xs leading-4 text-muted">
                  Calculated from the current gold assessment.
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
                    {stateCopy(p?.state)} Evidence starts at connected sources,
                    lands raw, evaluates into gold controls, then exports for
                    audit and analytics.
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
              <div>
                <div className="ui-label">Evidence loop</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                  {loopStages.map(({ label, value, detail, Icon, done }) => (
                    <div
                      key={label}
                      className={`min-w-0 rounded-lg border px-3 py-2 ${
                        done
                          ? "border-emerald-200 bg-emerald-50"
                          : "border-line bg-panel"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-[10px] font-black uppercase tracking-wide text-muted">
                          {label}
                        </span>
                        <Icon
                          className={`h-3.5 w-3.5 shrink-0 ${
                            done ? "text-emerald-700" : "text-muted"
                          }`}
                        />
                      </div>
                      <div className="mt-1 truncate text-lg font-black leading-tight text-ink">
                        {value}
                      </div>
                      <div className="mt-1 line-clamp-2 text-xs leading-4 text-muted">
                        {detail}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Card>

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
                      : "text-muted hover:bg-white"
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

        {activeDashboardTab === "Controls" && (
          <div className="grid gap-2 xl:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
            <FixNext violations={data?.violations ?? []} />
            <CollapsibleCard
              storageKey="dashboard-control-tests"
              defaultOpen={(p?.failed_control_test_count ?? 0) > 0}
              title="Control test results"
              description="Deterministic control checks from normalized evidence"
              contentClassName="p-0"
            >
              <ControlTestTable rows={tests.data ?? []} />
            </CollapsibleCard>
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
                    TrustOps keeps raw connector evidence separate from
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
          description={`${frameworks.length}/${registeredCount} frameworks · source health · trends · assessment provenance`}
          contentClassName="grid gap-2 p-3"
        >
          <ReadinessGrid
            frameworks={frameworks}
            catalog={registeredFrameworks.data ?? []}
          />
          <EvidenceTrend />
          <DashboardStripsRow />
          <DataPipelineStrip />
          <FrameworkBars frameworks={frameworks} embedded />
          <TrustLifecycle posture={p} assessmentHash={data?.assessment_hash} />
        </CollapsibleCard>
      </QueryState>
    </div>
  );
}
