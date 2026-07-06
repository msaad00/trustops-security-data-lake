"use client";

import Link from "next/link";
import { Users } from "lucide-react";
import { useAuditReadiness } from "@/lib/api/hooks";
import { KpiTile } from "@/components/ui/KpiTile";

function personnelTone(
  identityConnectors: number,
  pending: number,
  activeCampaigns: number,
): "ready" | "attention" | "critical" | "default" {
  if (identityConnectors === 0 || activeCampaigns === 0) return "attention";
  if (pending > 0) return "attention";
  return "ready";
}

export function PersonnelComplianceStrip() {
  const audit = useAuditReadiness();
  const personnel = audit.data?.personnel;

  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold text-ink">Personnel &amp; access</h2>
          <p className="text-xs text-muted">
            Identity connector evidence plus access-review campaigns — the
            turnkey path until native HRIS ships.
          </p>
        </div>
        <Link
          href="/access-reviews"
          className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
        >
          <Users className="h-3.5 w-3.5" />
          Open access reviews
        </Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile
          label="Identity sources"
          value={personnel ? String(personnel.identity_connectors) : "—"}
          detail="Enabled IdP connectors"
          tone={
            personnel && personnel.identity_connectors === 0
              ? "attention"
              : "default"
          }
        />
        <KpiTile
          label="Active campaigns"
          value={personnel ? String(personnel.active_campaigns) : "—"}
          detail="In-flight certifications"
          tone={
            personnel && personnel.active_campaigns === 0 ? "attention" : "default"
          }
        />
        <KpiTile
          label="Pending reviews"
          value={personnel ? String(personnel.pending_certifications) : "—"}
          detail="Subjects awaiting decision"
          tone={
            personnel && personnel.pending_certifications > 0
              ? "attention"
              : "default"
          }
        />
        <KpiTile
          label="Certified"
          value={personnel ? String(personnel.certified) : "—"}
          detail={`${personnel?.completed_campaigns ?? 0} completed campaigns`}
          tone={personnelTone(
            personnel?.identity_connectors ?? 0,
            personnel?.pending_certifications ?? 0,
            personnel?.active_campaigns ?? 0,
          )}
        />
      </div>
    </section>
  );
}
