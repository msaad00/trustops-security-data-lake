"use client";

import Link from "next/link";
import { ClipboardCheck, FileCheck2, ShieldCheck } from "lucide-react";
import {
  useControlTests,
  useFrameworks,
  useIngestionStatus,
  usePosture,
  usePostureStream,
} from "@/lib/api/hooks";
import { DashboardPanel } from "@/components/dashboard/DashboardPanel";
import { DashboardStripsRow } from "@/components/dashboard/DashboardStripsRow";
import { PostureRing } from "@/components/dashboard/PostureRing";
import { ComplianceOverview } from "@/components/dashboard/ComplianceOverview";
import { ControlFamilies } from "@/components/dashboard/ControlFamilies";
import { ReadinessGrid } from "@/components/dashboard/ReadinessGrid";
import { FixNext } from "@/components/dashboard/FixNext";
import { EvidenceTrend } from "@/components/dashboard/EvidenceTrend";
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
  if (state === "ready") return "Ready for review";
  if (state === "critical") return "Critical findings open";
  return "Review required";
}

function stateCopy(state?: string) {
  if (state === "ready") {
    return "Review the evidence and scope before sharing.";
  }
  if (state === "critical") {
    return "Assign owners to critical findings and refresh stale evidence.";
  }
  return "Review open findings and stale evidence.";
}

function formatPassRate(rate: number | null | undefined) {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
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

  return (
    <div className="mx-auto grid w-full max-w-[1600px] gap-4 px-3 py-4 sm:px-5 lg:px-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <h1 className="ui-page-title">Dashboard</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-1 text-xs font-medium ${connected ? "text-emerald-700" : "text-amber-700"}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500" : "bg-amber-500"}`}
            />
            {connected ? "Updates connected" : "Polling updates"}
          </span>
          {data?.evaluated_at ? (
            <span className="rounded-md border border-line bg-surface px-2 py-1 text-xs text-muted">
              {shortDate(data.evaluated_at)}
            </span>
          ) : null}
        </div>
      </div>

      <QueryState queries={[posture, ingestion]} label="overview">
        <Card
          role="region"
          aria-label="Current assessment"
          className="overflow-hidden border-slate-700 shadow-card"
          style={{
            background:
              "radial-gradient(ellipse at top right, #124753 0%, transparent 65%), linear-gradient(120deg, #0b1728, #101f34)",
            color: "#fff",
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-3">
            <span className="text-xs font-semibold uppercase tracking-[0.15em] text-cyan-200">
              Current assessment
            </span>
            <span className="text-xs text-slate-300">
              {frameworks.length}/{registeredCount} frameworks assessed
            </span>
          </div>
          <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-center">
            <div className="flex min-w-0 items-center gap-4">
              <div className="shrink-0">
                <PostureRing
                  score={p?.score ?? 0}
                  state={p?.state ?? "attention_required"}
                  size="compact"
                  dark
                />
              </div>
              <div className="min-w-0">
                <h2 className="mt-1 text-xl font-semibold text-white">
                  {stateHeadline(p?.state)}
                </h2>
                <p className="mt-2 text-sm text-slate-300">
                  {stateCopy(p?.state)}
                </p>
              </div>
            </div>
            <dl className="grid grid-cols-3 divide-x divide-white/15 border-t border-white/15 pt-4 lg:border-t-0 lg:pt-0">
              <div className="px-3">
                <dt className="text-xs text-slate-300">Control pass rate</dt>
                <dd className="mt-1 text-2xl font-semibold tabular-nums text-white">
                  {formatPassRate(passRate)}
                </dd>
                <p className="mt-1 text-xs text-slate-300">
                  {controlEvalReady
                    ? `${ingestion.data?.eval_accuracy?.failing ?? 0} failing tests`
                    : "Not evaluated"}
                </p>
              </div>
              <div className="px-3">
                <dt className="text-xs text-slate-300">Open findings</dt>
                <dd className="mt-1 text-2xl font-semibold tabular-nums text-white">
                  {p?.open_violation_count ?? 0}
                </dd>
                <p className="mt-1 text-xs text-slate-300">
                  {p?.critical_violation_count ?? 0} critical
                </p>
              </div>
              <div className="px-3">
                <dt className="text-xs text-slate-300">Assessment export</dt>
                <dd className="mt-1 text-2xl font-semibold text-white">
                  {proofReady ? "Available" : "Pending"}
                </dd>
                <p className="mt-1 text-xs text-slate-300">
                  {evidenceCount} evidence rows
                </p>
              </div>
            </dl>
          </div>
        </Card>

        <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
          <DashboardPanel
            title="Compliance"
            storageKey="dashboard-compliance-panel"
            tabs={[
              {
                label: "Frameworks",
                content: (
                  <ReadinessGrid
                    embedded
                    frameworks={frameworks}
                    catalog={registeredFrameworks.data ?? []}
                  />
                ),
              },
              {
                label: "Control families",
                content: <ControlFamilies embedded />,
              },
              {
                label: "Test results",
                content: (
                  <div
                    role="region"
                    aria-label="Control test results"
                    tabIndex={0}
                    className="max-h-[440px] overflow-auto"
                  >
                    <ControlTestTable rows={tests.data ?? []} />
                  </div>
                ),
              },
            ]}
          />
          <DashboardPanel
            title="Operations"
            storageKey="dashboard-operations-panel"
            tabs={[
              {
                label: "Findings",
                content: (
                  <FixNext embedded violations={data?.violations ?? []} />
                ),
              },
              {
                label: "Sources",
                content: (
                  <div className="p-3">
                    {" "}
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
                  </div>
                ),
              },
              {
                label: "Exports",
                content: (
                  <div className="p-3">
                    {" "}
                    <div className="grid gap-2">
                      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1 2xl:grid-cols-3">
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
                          detail="Assessed frameworks"
                          tone="brand"
                          icon={<ClipboardCheck className="h-3.5 w-3.5" />}
                        />
                        <KpiTile
                          label="Assessment hash"
                          value={data?.assessment_hash?.slice(0, 8) ?? "—"}
                          detail="Current assessment"
                          tone={data?.assessment_hash ? "ready" : "default"}
                          icon={<ShieldCheck className="h-3.5 w-3.5" />}
                        />
                      </div>
                      <Card className="overflow-hidden p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <h2 className="text-base font-semibold text-ink">
                              Assessment exports
                            </h2>
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
                  </div>
                ),
              },
            ]}
          />
        </div>

        <CollapsibleCard
          storageKey="dashboard-operational-detail"
          defaultOpen={false}
          title="Operational detail"
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
