"use client";

import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EvidenceFreshnessSlaPanel } from "@/components/evidence/EvidenceFreshnessSlaPanel";
import { AuditRoomTrendsPanel } from "@/components/audit-room/AuditRoomTrendsPanel";
import { AuditSnapshotTimeline } from "@/components/audit-room/AuditSnapshotTimeline";
import { RemediationSlaStrip } from "@/components/audit-room/RemediationSlaStrip";
import { VendorRiskStrip } from "@/components/audit-room/VendorRiskStrip";
import { PolicyAttestationStrip } from "@/components/audit-room/PolicyAttestationStrip";
import { PersonnelComplianceStrip } from "@/components/audit-room/PersonnelComplianceStrip";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import { KpiTile } from "@/components/ui/KpiTile";
import { useAuditReadiness, usePlatformStream } from "@/lib/api/hooks";

function consoleHref(href: string) {
  return href.startsWith("/console") ? href.replace(/^\/console/, "") : href;
}

const STATE_COPY: Record<
  string,
  { label: string; tone: "ready" | "attention" | "critical" }
> = {
  audit_ready: { label: "Audit ready", tone: "ready" },
  on_track: { label: "On track", tone: "attention" },
  needs_work: { label: "Needs work", tone: "attention" },
};

export default function AuditRoomPage() {
  const audit = useAuditReadiness();
  const { connected } = usePlatformStream();

  return (
    <div className="mx-auto grid max-w-6xl gap-6 p-6 md:p-8">
      <PageHeader
        eyebrow="Audit center"
        title="Audit readiness room"
        description="Continuous controls, evidence, access reviews, auditor shares, and point-in-time snapshots — same data via API for headless automation."
      />

      <QueryState queries={audit} label="audit readiness">
        {audit.data && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <Badge tone={STATE_COPY[audit.data.state]?.tone ?? "attention"}>
                {STATE_COPY[audit.data.state]?.label ?? audit.data.state}
              </Badge>
              {connected ? <Badge tone="ready">Live</Badge> : null}
              <span className="text-sm text-muted">
                Evaluated {new Date(audit.data.evaluated_at).toLocaleString()}
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <KpiTile
                label="Audit score"
                value={`${audit.data.audit_score}%`}
                detail="Weighted posture, tests, frameworks, workflow coverage"
              />
              <KpiTile
                label="Control tests"
                value={`${audit.data.control_tests.passing}/${audit.data.control_tests.total}`}
                detail={`${audit.data.control_tests.failing} failing`}
              />
              <KpiTile
                label="Frameworks ready"
                value={`${audit.data.posture.frameworks_ready}/${audit.data.posture.frameworks_total}`}
                detail={`${audit.data.posture.score}% posture`}
              />
              <KpiTile
                label="Evidence fresh"
                value={
                  audit.data.evidence_freshness
                    ? `${audit.data.evidence_freshness.fresh_rate_pct}%`
                    : "—"
                }
                detail={
                  audit.data.evidence_freshness
                    ? `${audit.data.evidence_freshness.stale_count} SLA breach(es)`
                    : "Freshness rollups from lake pipeline"
                }
              />
              <KpiTile
                label="Workflow coverage"
                value={`${audit.data.workflow_coverage.score}%`}
                detail="Audit-center checklist"
              />
            </div>

            <EvidenceFreshnessSlaPanel />

            <AuditRoomTrendsPanel />

            <RemediationSlaStrip />

            <VendorRiskStrip />

            <PersonnelComplianceStrip />

            <PolicyAttestationStrip />

            <AuditSnapshotTimeline />

            {audit.data.gaps.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Blocking gaps</CardTitle>
                  <CardDescription>
                    Top items an auditor or GRC lead would ask for before
                    sign-off.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2">
                  {audit.data.gaps.map((gap) => (
                    <Link
                      key={gap.id}
                      href={consoleHref(gap.href)}
                      className="flex items-center justify-between rounded-lg border border-line bg-surface px-3 py-2 text-sm hover:bg-surfaceMuted"
                    >
                      <span className="flex items-center gap-2 font-bold text-ink">
                        <CircleAlert className="h-4 w-4 text-brand-orange" />
                        {gap.label}
                      </span>
                      <ArrowRight className="h-4 w-4 text-muted" />
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Evidence &amp; access
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-muted">
                  <div className="flex justify-between">
                    <span>Open evidence requests</span>
                    <b className="text-ink">
                      {audit.data.evidence_requests.open}
                    </b>
                  </div>
                  <div className="flex justify-between">
                    <span>Active access reviews</span>
                    <b className="text-ink">
                      {audit.data.access_reviews.active}
                    </b>
                  </div>
                  <div className="flex justify-between">
                    <span>Auditor trust shares</span>
                    <b className="text-ink">
                      {audit.data.trust_shares.auditor}
                    </b>
                  </div>
                  <div className="flex justify-between">
                    <span>Connectors / evidence rows</span>
                    <b className="text-ink">
                      {audit.data.connectors.enabled} /{" "}
                      {audit.data.connectors.evidence_count}
                    </b>
                  </div>
                  {audit.data.vendor_risk && (
                    <>
                      <div className="flex justify-between">
                        <span>Vendor assessments</span>
                        <b className="text-ink">
                          {audit.data.vendor_risk.completed}/
                          {audit.data.vendor_risk.total} complete
                        </b>
                      </div>
                      <div className="flex justify-between">
                        <span>Overdue vendor reviews</span>
                        <b className="text-ink">
                          {audit.data.vendor_risk.overdue}
                        </b>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Point-in-time</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-muted">
                  <div className="flex justify-between">
                    <span>Snapshots</span>
                    <b className="text-ink">{audit.data.snapshots.count}</b>
                  </div>
                  <div className="flex justify-between">
                    <span>Latest</span>
                    <code className="max-w-[200px] truncate text-ink">
                      {audit.data.snapshots.latest_hash ?? "—"}
                    </code>
                  </div>
                  <div className="flex justify-between">
                    <span>Open violations</span>
                    <b className="text-ink">
                      {audit.data.posture.open_violations}
                    </b>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Audit workflow checklist
                </CardTitle>
                <CardDescription>
                  Capabilities shipped today vs roadmap gaps — also available
                  via API.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                {audit.data.workflow_coverage.checklist.map((row) => (
                  <div
                    key={row.id}
                    className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 rounded-lg border border-line bg-surface px-3 py-2"
                  >
                    {row.shipped ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-brand-green" />
                    ) : (
                      <CircleAlert className="mt-0.5 h-4 w-4 text-muted" />
                    )}
                    <div>
                      <div className="text-sm font-bold text-ink">
                        {row.label}
                      </div>
                      <div className="text-xs text-muted">{row.note}</div>
                    </div>
                    <Badge tone={row.shipped ? "ready" : "default"}>
                      {row.shipped ? "shipped" : "gap"}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>

            <div className="flex flex-wrap gap-2">
              <Button asChild variant="primary">
                <Link href="/trust-center">
                  <ShieldCheck className="h-4 w-4" />
                  Trust center
                </Link>
              </Button>
              <Button asChild variant="default">
                <Link href="/access-reviews">
                  <ClipboardCheck className="h-4 w-4" />
                  Access reviews
                </Link>
              </Button>
              <Button asChild variant="default">
                <a
                  href="https://github.com/msaad00/trustops-security-data-lake/blob/main/docs/AUDIT_READINESS.md"
                  target="_blank"
                  rel="noreferrer"
                >
                  Audit readiness doc
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </div>
          </>
        )}
      </QueryState>
    </div>
  );
}
