"use client";

import { QueryState } from "@/components/QueryState";
import { KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/button";
import {
  useOpenPoamItems,
  useSprsScore,
  useSyncPoamMutation,
} from "@/lib/api/hooks";

function sprsTone(
  score: number | undefined,
): "ready" | "attention" | "critical" | "default" {
  if (score == null) return "default";
  if (score >= 100) return "ready";
  if (score >= 70) return "attention";
  return "critical";
}

export function GovComplianceStrip() {
  const sprs = useSprsScore();
  const poam = useOpenPoamItems();
  const sync = useSyncPoamMutation();

  const openPoam = poam.data?.length ?? 0;
  const score = sprs.data?.score;

  return (
    <QueryState queries={[sprs, poam]} label="gov compliance (CMMC)">
      <section className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Gov programs (CMMC)
            </h2>
            <p className="text-sm text-muted">
              SPRS score and POA&M auto-sync from failing NIST SP 800-171 Rev 2
              practices.
            </p>
          </div>
          <Button
            variant="default"
            size="sm"
            disabled={sync.isPending}
            onClick={() => sync.mutate()}
          >
            {sync.isPending ? "Syncing…" : "Sync POA&M"}
          </Button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiTile
            label="SPRS score"
            value={score != null ? String(score) : "—"}
            detail="110 max · weighted NIST 800-171 deductions"
            tone={sprsTone(score)}
          />
          <KpiTile
            label="Open POA&M"
            value={String(openPoam)}
            detail="Milestone-tracked gaps for assessors"
            tone={openPoam > 0 ? "attention" : "ready"}
          />
          <KpiTile
            label="Unmet practices"
            value={sprs.data ? String(sprs.data.requirements_unmet) : "—"}
            detail={`${sprs.data?.requirements_total ?? 110} CMMC L2 requirements`}
            tone={
              sprs.data && sprs.data.requirements_unmet > 0
                ? "attention"
                : "default"
            }
          />
          <KpiTile
            label="Deduction points"
            value={sprs.data ? String(sprs.data.deduction_total) : "—"}
            detail="Subtracted from SPRS base of 110"
            tone="default"
          />
        </div>
      </section>
    </QueryState>
  );
}
