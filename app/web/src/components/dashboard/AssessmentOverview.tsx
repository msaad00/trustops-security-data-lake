"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  ChevronDown,
  FileCheck2,
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
      label: "Control pass rate",
      value: evaluated && rate != null ? `${Math.round(rate * 100)}%` : "—",
      detail: evaluated
        ? `${ingestion?.eval_accuracy?.failing ?? 0} failing tests`
        : "Not evaluated",
      href: "/controls",
      Icon: ListChecks,
      attention: false,
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
      <div className="grid lg:grid-cols-[minmax(240px,0.85fr)_minmax(0,2fr)]">
        <div className="flex items-center gap-3 bg-[linear-gradient(115deg,#101c30,#123b48)] px-4 py-4 text-white">
          <div className="shrink-0">
            {posture ? (
              <PostureRing
                score={posture.score}
                state={posture.state}
                size="compact"
                dark
              />
            ) : (
              <span className="text-2xl text-slate-300">—</span>
            )}
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-medium uppercase tracking-wider text-cyan-200">
              Current assessment
            </p>
            <h2 className="mt-1 text-base font-semibold leading-snug">
              {state === "critical"
                ? "Critical findings open"
                : state === "ready"
                  ? "Ready for review"
                  : posture
                    ? "Review required"
                    : "Not assessed"}
            </h2>
            <Link
              href="/frameworks"
              className="mt-1 inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
            >
              {assessment?.frameworks.length ?? 0}/{frameworkCount} frameworks
              assessed
              <ArrowUpRight aria-hidden="true" className="h-3 w-3" />
            </Link>
          </div>
        </div>
        <div className="grid grid-cols-3 divide-x divide-line">
          {metrics.map(({ label, value, detail, href, Icon, attention }) => (
            <Link
              key={label}
              href={href}
              className="group flex min-w-0 flex-col justify-center px-3 py-4 transition-colors hover:bg-surfaceMuted focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand sm:px-5"
            >
              <div className="mb-2 flex items-center justify-between gap-1">
                <Icon
                  aria-hidden="true"
                  className={`h-4 w-4 ${attention ? "text-rose-600" : "text-muted"}`}
                />
                <ArrowUpRight
                  aria-hidden="true"
                  className="h-3.5 w-3.5 text-muted transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                />
              </div>
              <span className="text-xs font-medium leading-4 text-muted">
                {label}
              </span>
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
