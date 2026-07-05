"use client";

import Link from "next/link";
import { Building2 } from "lucide-react";
import { useAuditReadiness } from "@/lib/api/hooks";
import { KpiTile } from "@/components/ui/KpiTile";

function vendorTone(
  overdue: number,
  open: number,
): "ready" | "attention" | "critical" | "default" {
  if (overdue > 0) return "critical";
  if (open > 0) return "attention";
  return "ready";
}

export function VendorRiskStrip() {
  const audit = useAuditReadiness();
  const vendor = audit.data?.vendor_risk;

  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold text-ink">Vendor diligence</h2>
          <p className="text-xs text-muted">
            Third-party questionnaires and scored assessments — managed GRC
            audit-prep parity.
          </p>
        </div>
        <Link
          href="/vendor-risk"
          className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
        >
          <Building2 className="h-3.5 w-3.5" />
          Open vendor risk
        </Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile
          label="Assessments"
          value={vendor ? String(vendor.total) : "—"}
          detail={`${vendor?.completed ?? 0} completed`}
          tone={vendor && vendor.total === 0 ? "attention" : "default"}
        />
        <KpiTile
          label="Open reviews"
          value={vendor ? String(vendor.open) : "—"}
          detail="Draft or in review"
          tone={vendor && vendor.open > 0 ? "attention" : "default"}
        />
        <KpiTile
          label="Overdue"
          value={vendor ? String(vendor.overdue) : "—"}
          detail="Past due date"
          tone={vendor && vendor.overdue > 0 ? "critical" : "default"}
        />
        <KpiTile
          label="High-risk open"
          value={vendor ? String(vendor.high_risk_open) : "—"}
          detail="Score below 70 or high/critical"
          tone={vendorTone(vendor?.overdue ?? 0, vendor?.open ?? 0)}
        />
      </div>
    </section>
  );
}
