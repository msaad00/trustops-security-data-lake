"use client";

import { motion } from "framer-motion";
import type { Assessment } from "@/lib/api/types";
import { Card } from "@/components/ui/card";
import { shortDate } from "@/lib/utils";

interface Props {
  posture: Assessment | undefined;
  evidenceCount: number;
}

const Stat = ({
  label,
  value,
  sub,
  delay = 0,
}: {
  label: string;
  value: string | number;
  sub?: string;
  delay?: number;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.3 }}
  >
    <Card className="min-h-[94px] p-4">
      <span className="text-[11px] font-black uppercase tracking-wider text-muted">
        {label}
      </span>
      <strong className="mt-2 block text-[26px] leading-none">{value}</strong>
      {sub && <small className="text-muted">{sub}</small>}
    </Card>
  </motion.div>
);

export function PostureKpis({ posture, evidenceCount }: Props) {
  const p = posture?.posture;
  const score = Math.round(p?.score ?? 0);
  const open = p?.open_violation_count ?? 0;
  const critical = p?.critical_violation_count ?? 0;
  const failingTests = p?.failed_control_test_count ?? 0;
  const stale = p?.stale_control_count ?? 0;
  const evidenceCoverage = posture?.frameworks
    ? Math.round(
        posture.frameworks.reduce(
          (acc, f) => acc + Number(f.score) * Number(f.control_count),
          0,
        ) /
          Math.max(
            1,
            posture.frameworks.reduce(
              (acc, f) => acc + Number(f.control_count),
              0,
            ),
          ),
      )
    : 0;

  return (
    <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-5">
      <Stat
        label="Posture score"
        value={`${score}%`}
        sub="weighted across frameworks"
      />
      <Stat
        label="Confidence"
        value={`${evidenceCoverage}%`}
        sub="evidence × freshness × hash"
        delay={0.05}
      />
      <Stat
        label="Open violations"
        value={open}
        sub={
          critical
            ? `${critical} critical violations`
            : "no critical violations"
        }
        delay={0.1}
      />
      <Stat
        label="Failing tests"
        value={failingTests}
        sub="live control test failures"
        delay={0.15}
      />
      <Stat
        label="Stale controls"
        value={stale}
        sub={stale ? "evidence past freshness SLA" : "all within freshness SLA"}
        delay={0.2}
      />
      <div className="col-span-2 hidden text-xs text-muted lg:col-span-5 lg:block">
        Evidence facts: {evidenceCount} · Last evidence:{" "}
        {shortDate(posture?.evaluated_at)} · hash{" "}
        <code className="text-ink">
          {posture?.assessment_hash?.slice(0, 16) ?? "—"}…
        </code>
      </div>
    </div>
  );
}
