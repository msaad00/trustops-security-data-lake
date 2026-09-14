"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  ChevronDown,
  FileCheck2,
  ArrowRight,
  Clock3,
  CircleCheck,
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

  return (
    <section
      aria-label="Current assessment"
      className="min-w-0 overflow-hidden rounded-xl border border-line bg-surface shadow-card"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
            Overall posture
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <StatusIcon
              aria-hidden="true"
              className={`h-5 w-5 ${statusTone}`}
            />
            <h2 className="text-xl font-semibold tracking-tight text-ink">
              {status}
            </h2>
          </div>
        </div>
        <Link
          href="/frameworks"
          className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs text-muted transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        >
          <span>
            <strong className="font-semibold text-ink">
              {assessment?.frameworks.length ?? 0}/{frameworkCount}
            </strong>{" "}
            frameworks assessed
          </span>
          <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3">
        <div className="col-span-2 flex min-w-0 flex-col border-b border-line px-5 py-4 sm:px-6 md:col-span-1 md:border-b-0">
          <p className="text-sm font-medium text-ink">Assessment score</p>
          <div className="mt-3 flex items-center gap-4">
            {posture ? (
              <PostureRing
                score={posture.score}
                state={posture.state}
                size="summary"
              />
            ) : (
              <span className="text-5xl text-muted">—</span>
            )}
            <div className="min-w-0 text-xs leading-5 text-muted">
              <p>Weighted framework score</p>
              <p className="mt-1">Based on assessed controls</p>
            </div>
          </div>
        </div>
        <Link
          href="/controls"
          className="group flex min-w-0 flex-col border-r border-line md:border-l px-5 py-4 transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand sm:px-6"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink">
              Control pass rate
            </span>
            <ArrowUpRight aria-hidden="true" className="h-4 w-4 text-muted" />
          </div>
          <span className="mt-4 text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl">
            {passPercent != null ? (
              <>
                {passPercent}
                <span className="ml-1 text-2xl font-medium text-muted">%</span>
              </>
            ) : (
              "—"
            )}
          </span>
          {passPercent != null && (
            <div
              role="progressbar"
              aria-label="Control pass rate"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={passPercent}
              className="mt-4 h-1.5 overflow-hidden rounded-full bg-surfaceMuted"
            >
              <div
                className="h-full rounded-full bg-brand"
                style={{ width: `${passPercent}%` }}
              />
            </div>
          )}
          <span className="mt-3 text-xs text-muted">
            {passPercent != null
              ? `${ingestion?.eval_accuracy?.passing ?? 0} of ${ingestion?.eval_accuracy?.total_tests ?? 0} tests passing`
              : "Not evaluated"}
          </span>
        </Link>
        <Link
          href="/violations"
          className="group flex min-w-0 flex-col border-line px-5 py-4 transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand sm:px-6"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink">Open findings</span>
            <ArrowUpRight aria-hidden="true" className="h-4 w-4 text-muted" />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl">
              {posture?.open_violation_count ?? "—"}
            </span>
            {critical > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">
                <ShieldAlert aria-hidden="true" className="h-3.5 w-3.5" />
                {critical} critical
              </span>
            )}
          </div>
          <span className="mt-3 text-xs text-muted">
            {critical > 0
              ? "Prioritize critical findings"
              : posture
                ? "Review findings and ownership"
                : "Awaiting assessment"}
          </span>
          <span className="mt-auto inline-flex items-center gap-1.5 pt-3 text-xs font-semibold text-brand">
            Review findings{" "}
            <ArrowRight
              aria-hidden="true"
              className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
            />
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
