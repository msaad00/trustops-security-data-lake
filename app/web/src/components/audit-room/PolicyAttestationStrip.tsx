"use client";

import Link from "next/link";
import { FileCheck2 } from "lucide-react";
import { useAuditReadiness } from "@/lib/api/hooks";
import { KpiTile } from "@/components/ui/KpiTile";

function attestationTone(
  unattested: number,
  published: number,
): "ready" | "attention" | "critical" | "default" {
  if (published === 0) return "default";
  if (unattested > 0) return "critical";
  return "ready";
}

export function PolicyAttestationStrip() {
  const audit = useAuditReadiness();
  const attestation = audit.data?.policy_attestation;

  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold text-ink">Policy attestation</h2>
          <p className="text-xs text-muted">
            Employee sign-off on published policies — audit evidence for SOC 2
            CC1/CC2 program controls.
          </p>
        </div>
        <Link
          href="/policies"
          className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
        >
          <FileCheck2 className="h-3.5 w-3.5" />
          Open policies
        </Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile
          label="Published policies"
          value={attestation ? String(attestation.published) : "—"}
          detail="Live policy documents"
          tone={
            attestation && attestation.published === 0 ? "attention" : "default"
          }
        />
        <KpiTile
          label="Acknowledged"
          value={attestation ? String(attestation.acknowledged) : "—"}
          detail="Policies with at least one sign-off"
          tone={attestationTone(
            attestation?.unattested ?? 0,
            attestation?.published ?? 0,
          )}
        />
        <KpiTile
          label="Unattested"
          value={attestation ? String(attestation.unattested) : "—"}
          detail="Published without employee ack"
          tone={
            attestation && attestation.unattested > 0 ? "critical" : "default"
          }
        />
        <KpiTile
          label="Total attestations"
          value={attestation ? String(attestation.total_acknowledgments) : "—"}
          detail="Recorded employee sign-offs"
          tone="default"
        />
      </div>
    </section>
  );
}
