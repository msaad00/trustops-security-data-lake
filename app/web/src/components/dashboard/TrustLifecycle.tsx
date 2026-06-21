"use client";

import Link from "next/link";
import {
  ArrowRight,
  Database,
  FileSearch,
  GitBranch,
  ListChecks,
  Share2,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { PostureBlock } from "@/lib/api/types";

interface Props {
  posture?: PostureBlock;
  assessmentHash?: string;
}

const stateLabel: Record<string, string> = {
  healthy: "healthy",
  attention_required: "needs review",
  critical: "critical",
};

export function TrustLifecycle({ posture, assessmentHash }: Props) {
  const failedTests = posture?.failed_control_test_count ?? 0;
  const staleEvidence = posture?.stale_evidence_count ?? 0;
  const openViolations = posture?.open_violation_count ?? 0;
  const criticalViolations = posture?.critical_violation_count ?? 0;
  const staleControls = posture?.stale_control_count ?? 0;
  const score = Math.round(posture?.score ?? 0);

  const lanes = [
    {
      label: "Live posture",
      href: "/dashboard",
      Icon: ShieldCheck,
      metric: `${score}`,
      detail: `${stateLabel[posture?.state ?? ""] ?? posture?.state ?? "not evaluated"} score`,
      tone:
        criticalViolations > 0
          ? "critical"
          : failedTests > 0 || staleControls > 0
            ? "attention"
            : "ready",
    },
    {
      label: "Control tests",
      href: "/controls",
      Icon: ListChecks,
      metric: `${failedTests}`,
      detail: failedTests === 1 ? "failing test" : "failing tests",
      tone: failedTests > 0 ? "critical" : "ready",
    },
    {
      label: "Evidence",
      href: "/evidence",
      Icon: FileSearch,
      metric: `${staleEvidence}`,
      detail:
        staleEvidence === 1 ? "stale evidence item" : "stale evidence items",
      tone: staleEvidence > 0 ? "attention" : "ready",
    },
    {
      label: "Risk queue",
      href: "/violations",
      Icon: Database,
      metric: `${openViolations}`,
      detail:
        criticalViolations > 0
          ? `${criticalViolations} critical`
          : "no critical violations",
      tone:
        criticalViolations > 0
          ? "critical"
          : openViolations > 0
            ? "attention"
            : "ready",
    },
    {
      label: "Automation",
      href: "/automation",
      Icon: GitBranch,
      metric: "DAG",
      detail: "route remediation and evidence requests",
      tone: "info",
    },
    {
      label: "Trust share",
      href: "/trust-center",
      Icon: Share2,
      metric: assessmentHash ? assessmentHash.slice(0, 8) : "not cut",
      detail: "scoped, expiring auditor/customer views",
      tone: assessmentHash ? "ready" : "default",
    },
  ] as const;

  return (
    <section className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-black text-ink">Trust operating loop</h2>
          <p className="mt-0.5 text-xs leading-5 text-muted">
            One path from source evidence to evaluated controls, remediation,
            and external assurance.
          </p>
        </div>
        <Badge tone="info">continuous</Badge>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-6">
        {lanes.map(({ label, href, Icon, metric, detail, tone }) => (
          <Link
            key={label}
            href={href}
            className="group grid min-h-[116px] grid-rows-[auto_1fr_auto] rounded-lg border border-line bg-panel p-3 transition-colors hover:border-brand hover:bg-white"
          >
            <span className="flex items-center justify-between gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-white text-brand ring-1 ring-line">
                <Icon className="h-4 w-4" />
              </span>
              <ArrowRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
            </span>
            <span className="mt-3 min-w-0">
              <span className="block text-[11px] font-black uppercase tracking-wide text-muted">
                {label}
              </span>
              <span className="mt-1 block truncate text-2xl font-black leading-none text-ink">
                {metric}
              </span>
            </span>
            <Badge tone={tone} className="mt-2 justify-self-start">
              {detail}
            </Badge>
          </Link>
        ))}
      </div>
    </section>
  );
}
