"use client";

import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { AuditReadinessStrip } from "./AuditReadinessStrip";
import { EvidenceFreshnessStrip } from "./EvidenceFreshnessStrip";
import { InsightsRemediationStrip } from "./InsightsRemediationStrip";

/** Collapsible row of status strips — side-by-side on wide screens, stacked on mobile. */
export function DashboardStripsRow() {
  return (
    <CollapsibleCard
      storageKey="dashboard-at-a-glance"
      defaultOpen={false}
      title="At a glance"
      description="Audit room, evidence freshness, and remediation SLA"
      contentClassName="p-2 sm:p-3"
    >
      <div className="grid gap-2 lg:grid-cols-3">
        <AuditReadinessStrip />
        <EvidenceFreshnessStrip />
        <InsightsRemediationStrip />
      </div>
    </CollapsibleCard>
  );
}
