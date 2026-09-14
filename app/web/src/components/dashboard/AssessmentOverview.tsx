"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  ChevronDown,
  FileCheck2,
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
  const metrics = [
    {
      label: "Open findings",
      value: posture?.open_violation_count ?? "—",
      detail: `${posture?.critical_violation_count ?? 0} critical`,
      href: "/violations",
      Icon: ShieldAlert,
      attention: Boolean(posture?.critical_violation_count),
    },
    {
      label: "Assessment export",
      value: exportReady ? "Available" : "Pending",
      detail: `${ingestion?.summary.evidence_count ?? 0} evidence rows`,
      href: "/audit-room",
      Icon: FileCheck2,
      attention: false,
    },
  ];

  return (
    <section
      aria-label="Current assessment"
      className="min-w-0 overflow-hidden rounded-xl border border-line bg-surface shadow-card"
    >
      <div className="grid xl:grid-cols-[minmax(0,2.2fr)_minmax(260px,0.8fr)]">
        <div className="grid bg-[linear-gradient(115deg,#101c30,#123b48)] text-white sm:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <div className="min-w-0 px-5 py-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-200">
              Overall posture
            </p>
            <div className="mt-4 flex items-center gap-4">
              <div className="shrink-0">
                {posture ? (
                  <PostureRing
                    score={posture.score}
                    state={posture.state}
                    size="summary"
                    dark
                  />
                ) : (
                  <span className="text-4xl text-slate-300">—</span>
                )}
              </div>
              <div className="min-w-0">
                <h2 className="text-xl font-semibold leading-snug tracking-tight">
                  {status}
                </h2>
                <p className="mt-1 text-xs text-slate-300">Assessment score</p>
                <Link
                  href="/frameworks"
                  className="mt-3 inline-flex items-center gap-1 text-xs text-cyan-200 hover:text-white hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
                >
                  {assessment?.frameworks.length ?? 0}/{frameworkCount}{" "}
                  frameworks assessed
                  <ArrowUpRight aria-hidden="true" className="h-3 w-3" />
                </Link>
              </div>
            </div>
          </div>
          <Link
            href="/controls"
            className="group flex min-w-0 flex-col justify-center border-t border-white/15 bg-white/[0.035] px-5 py-5 transition-colors hover:bg-white/[0.08] focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-cyan-300 sm:border-l sm:border-t-0"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-cyan-100">
                Control pass rate
              </span>
              <ArrowUpRight
                aria-hidden="true"
                className="h-4 w-4 text-cyan-200 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              />
            </div>
            <span className="mt-3 text-5xl font-semibold tracking-tight text-white tabular-nums">
              {passPercent != null ? (
                <>
                  {passPercent}
                  <span className="ml-1 text-2xl text-cyan-200">%</span>
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
                className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/15"
              >
                <div
                  className="h-full rounded-full bg-cyan-300"
                  style={{ width: `${passPercent}%` }}
                />
              </div>
            )}
            <span className="mt-3 text-xs text-slate-200">
              {passPercent != null
                ? `${ingestion?.eval_accuracy?.passing ?? 0} of ${ingestion?.eval_accuracy?.total_tests ?? 0} tests passing`
                : "Not evaluated"}
            </span>
          </Link>
        </div>
        <div className="grid grid-cols-2 divide-x divide-line xl:grid-cols-1 xl:divide-x-0 xl:divide-y">
          {metrics.map(({ label, value, detail, href, Icon, attention }) => (
            <Link
              key={label}
              href={href}
              className="group flex min-w-0 flex-col justify-center px-3 py-4 transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand sm:px-5"
            >
              <div className="flex items-center gap-2">
                <Icon
                  aria-hidden="true"
                  className={`h-4 w-4 ${attention ? "text-rose-600" : "text-muted"}`}
                />
                <span className="flex-1 text-xs font-medium leading-4 text-muted">
                  {label}
                </span>
                <ArrowUpRight
                  aria-hidden="true"
                  className="h-3.5 w-3.5 text-muted transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                />
              </div>
              <span
                className={`mt-1 text-xl font-semibold tracking-tight tabular-nums sm:text-2xl ${attention ? "text-rose-600" : "text-ink"}`}
              >
                {value}
              </span>
              <span className="mt-1 text-[11px] leading-4 text-muted">
                {detail}
              </span>
            </Link>
          ))}
        </div>
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
