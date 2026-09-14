"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  ChevronDown,
  FileCheck2,
  ArrowRight,
  Clock3,
  CircleCheck,
  ChartNoAxesCombined,
  ListChecks,
  ShieldAlert,
} from "lucide-react";
import type { Assessment, IngestionStatus } from "@/lib/api/types";
import { PostureRing } from "./PostureRing";

export function AssessmentOverview({
  assessment,
  ingestion,
  frameworkCount,
}: {
  assessment?: Assessment;
  ingestion?: IngestionStatus;
  frameworkCount: number;
}) {
  const posture = assessment?.posture;
  const state = posture?.state;
  const evaluated = Boolean(ingestion?.eval_accuracy?.has_tests);
  const rate = ingestion?.eval_accuracy?.pass_rate;
  const passPercent =
    evaluated && rate != null && Number.isFinite(rate)
      ? Math.round(rate * 100)
      : null;
  const status = !posture
    ? "Not assessed"
    : state === "ready"
      ? "Ready for review"
      : state === "critical"
        ? "Needs attention"
        : "Review required";
  const exportReady = Boolean(ingestion?.proof.proof_pack_exists);
  const critical = posture?.critical_violation_count ?? 0;
  const StatusIcon = state === "ready" ? CircleCheck : ShieldAlert;
  const statusTone = !posture
    ? "text-muted"
    : state === "ready"
      ? "text-emerald-600 dark:text-emerald-400"
      : state === "critical"
        ? "text-rose-600 dark:text-rose-400"
        : "text-amber-600 dark:text-amber-400";

  const accuracy = ingestion?.eval_accuracy;
  const outcomes = [
    { label: "Pass", count: accuracy?.passing ?? 0, color: "bg-indigo-500" },
    { label: "Fail", count: accuracy?.failing ?? 0, color: "bg-rose-500" },
    { label: "Warning", count: accuracy?.warning ?? 0, color: "bg-amber-400" },
    {
      label: "Other",
      count: Math.max(
        0,
        (accuracy?.total_tests ?? 0) -
          (accuracy?.passing ?? 0) -
          (accuracy?.failing ?? 0) -
          (accuracy?.warning ?? 0),
      ),
      color: "bg-slate-300",
    },
  ];
  const findings = posture?.open_violation_count ?? 0;
  const severity = [
    { label: "Critical", count: critical, color: "bg-rose-600" },
    {
      label: "High",
      count: posture?.high_violation_count ?? 0,
      color: "bg-orange-400",
    },
    {
      label: "Other",
      count: Math.max(
        0,
        findings - critical - (posture?.high_violation_count ?? 0),
      ),
      color: "bg-slate-300",
    },
  ];

  return (
    <section
      aria-label="Current assessment"
      className="min-w-0 overflow-hidden rounded-xl border border-line bg-surface shadow-card"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 pb-1 pt-4 sm:px-5">
        <p className="text-sm font-semibold text-ink">Overall posture</p>
        <div className="flex items-center gap-1.5 rounded-full border border-line bg-surfaceMuted/60 px-2.5 py-1">
          <StatusIcon
            aria-hidden="true"
            className={`h-3.5 w-3.5 ${statusTone}`}
          />
          <h2 className="text-xs font-medium text-ink">{status}</h2>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 p-3 min-[640px]:grid-cols-3 sm:p-4">
        <div className="relative col-span-2 flex min-w-0 flex-col overflow-hidden rounded-xl border border-slate-700 bg-[radial-gradient(ellipse_at_top_right,#164e63_0%,#142239_55%,#101b2e_100%)] p-4 text-white min-[640px]:col-span-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-slate-200">
              Assessment score
            </span>
            <ChartNoAxesCombined
              aria-hidden="true"
              className="h-4 w-4 text-cyan-300"
            />
          </div>
          <div className="my-3 flex items-center gap-3 min-[640px]:justify-center">
            <div className="shrink-0">
              {posture ? (
                <PostureRing
                  score={posture.score}
                  state={posture.state}
                  size="summary"
                  dark
                />
              ) : (
                <span className="text-5xl text-slate-300">—</span>
              )}
            </div>
            <p className="text-xs leading-5 text-slate-300 min-[640px]:hidden">
              Weighted framework
              <br />
              score out of 100
            </p>
          </div>
          <Link
            href="/frameworks"
            className="mt-auto flex items-center justify-between gap-2 border-t border-white/15 pt-3 text-xs text-slate-200 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
          >
            <span>
              <strong className="font-semibold text-white">
                {assessment?.frameworks.length ?? 0}/{frameworkCount}
              </strong>{" "}
              frameworks assessed
            </span>
            <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
          </Link>
        </div>
        <Link
          href="/controls"
          className="group flex min-w-0 flex-col rounded-xl border border-indigo-100 bg-[linear-gradient(145deg,#eef2ff_0%,#ffffff_70%)] p-4 transition-shadow hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand dark:border-indigo-900 dark:bg-[linear-gradient(145deg,#20283f_0%,#172131_70%)]"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-ink">
              Control pass rate
            </span>
            <ListChecks
              aria-hidden="true"
              className="h-4 w-4 shrink-0 text-indigo-500 dark:text-indigo-300"
            />
          </div>
          <span className="mt-5 text-[42px] font-semibold leading-none tracking-tight text-ink tabular-nums sm:text-5xl">
            {passPercent != null ? (
              <>
                {passPercent}
                <span className="ml-1 text-xl font-medium text-muted">%</span>
              </>
            ) : (
              "—"
            )}
          </span>
          <span className="mt-2 text-[11px] leading-4 text-muted">
            {passPercent != null
              ? `${accuracy?.passing ?? 0} of ${accuracy?.total_tests ?? 0} tests passing`
              : "Not evaluated"}
          </span>
          {passPercent != null && (
            <>
              <div
                role="progressbar"
                aria-label="Control pass rate"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={passPercent}
                className="mt-4 flex h-2 gap-0.5 overflow-hidden rounded-full bg-surfaceMuted"
              >
                {outcomes.map((item) => (
                  <span
                    key={item.label}
                    className={item.color}
                    style={{
                      width: `${accuracy?.total_tests ? (item.count / accuracy.total_tests) * 100 : 0}%`,
                    }}
                  />
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 text-[10px] text-muted">
                {outcomes.map((item) => (
                  <span
                    key={item.label}
                    className="inline-flex items-center gap-1"
                  >
                    <span
                      aria-hidden="true"
                      className={`h-1.5 w-1.5 rounded-full ${item.color}`}
                    />
                    <strong className="font-semibold text-ink">
                      {item.count}
                    </strong>{" "}
                    {item.label}
                  </span>
                ))}
              </div>
            </>
          )}
          <span className="mt-auto inline-flex items-center gap-1.5 border-t border-indigo-100 pt-3 text-xs font-semibold text-indigo-600 dark:border-indigo-900 dark:text-indigo-300 min-[640px]:mt-4">
            View controls <ArrowRight aria-hidden="true" className="h-3 w-3" />
          </span>
        </Link>
        <Link
          href="/violations"
          className="group flex min-w-0 flex-col rounded-xl border border-rose-100 bg-[linear-gradient(145deg,#fff1f2_0%,#ffffff_70%)] p-4 transition-shadow hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand dark:border-rose-900/50 dark:bg-[linear-gradient(145deg,#322331_0%,#172131_70%)]"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-ink">Open findings</span>
            <ShieldAlert
              aria-hidden="true"
              className="h-4 w-4 shrink-0 text-rose-500 dark:text-rose-300"
            />
          </div>
          <span className="mt-5 text-[42px] font-semibold leading-none tracking-tight text-ink tabular-nums sm:text-5xl">
            {posture?.open_violation_count ?? "—"}
          </span>
          <span className="mt-2 text-[11px] leading-4 font-medium text-rose-700 dark:text-rose-300">
            {posture ? `${critical} critical` : "Awaiting assessment"}
          </span>
          {posture && (
            <>
              <div
                role="img"
                aria-label={`Finding severity: ${severity.map((item) => `${item.count} ${item.label.toLowerCase()}`).join(", ")}`}
                className="mt-4 flex h-2 gap-0.5 overflow-hidden rounded-full bg-surfaceMuted"
              >
                {severity.map((item) => (
                  <span
                    key={item.label}
                    className={item.color}
                    style={{
                      width: `${findings ? (item.count / findings) * 100 : 0}%`,
                    }}
                  />
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 text-[10px] text-muted">
                {severity.map((item) => (
                  <span
                    key={item.label}
                    className="inline-flex items-center gap-1"
                  >
                    <span
                      aria-hidden="true"
                      className={`h-1.5 w-1.5 rounded-full ${item.color}`}
                    />
                    <strong className="font-semibold text-ink">
                      {item.count}
                    </strong>{" "}
                    {item.label}
                  </span>
                ))}
              </div>
            </>
          )}
          <span className="mt-auto inline-flex items-center gap-1.5 border-t border-rose-100 pt-3 text-xs font-semibold text-rose-700 dark:border-rose-900/50 dark:text-rose-300 min-[640px]:mt-4">
            Review findings{" "}
            <ArrowRight aria-hidden="true" className="h-3 w-3" />
          </span>
        </Link>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-t border-line bg-surfaceMuted/50 px-5 py-3 text-xs sm:px-6">
        <span className="inline-flex items-center gap-2 text-muted">
          <Clock3 aria-hidden="true" className="h-4 w-4" />
          {posture
            ? `${posture.stale_evidence_count} stale evidence rows`
            : "Evidence freshness unavailable"}
        </span>
        <Link
          href="/audit-room"
          className="inline-flex items-center gap-2 text-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        >
          <FileCheck2 aria-hidden="true" className="h-4 w-4" />
          <span>Assessment export</span>
          <span className="rounded-md border border-line bg-surface px-2 py-0.5 font-medium text-ink">
            {exportReady ? "Available" : "Pending"}
          </span>
          <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      </div>
      <details className="group border-t border-line">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-2 text-xs text-muted hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand">
          <span>Assessment details</span>
          <ChevronDown
            aria-hidden="true"
            className="h-3.5 w-3.5 transition-transform group-open:rotate-180"
          />
        </summary>
        <dl className="grid gap-x-6 gap-y-3 border-t border-line bg-surfaceMuted px-4 py-3 text-xs sm:grid-cols-3">
          <div>
            <dt className="text-muted">Last evaluated</dt>
            <dd className="mt-1 text-ink">
              {assessment?.evaluated_at
                ? new Date(assessment.evaluated_at).toLocaleString()
                : "Not evaluated"}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Stale evidence</dt>
            <dd className="mt-1 text-ink">
              {posture?.stale_evidence_count ?? "—"} rows
            </dd>
          </div>
          <div>
            <dt className="text-muted">Assessment ID</dt>
            <dd className="mt-1 break-all font-mono text-ink">
              {assessment?.assessment_hash || "Not available"}
            </dd>
          </div>
        </dl>
      </details>
    </section>
  );
}
