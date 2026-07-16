"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Calendar, ExternalLink, FileCheck2, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Drawer } from "@/components/ui/drawer";
import { PageHeader } from "@/components/PageHeader";
import { TrustPipelineStrip } from "@/components/TrustPipelineStrip";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { FrameworkDrilldownPanel } from "@/components/framework/FrameworkDrilldownPanel";
import { frameworkDetailHref } from "@/lib/framework-links";
import { useFrameworks, useReadiness } from "@/lib/api/hooks";
import type {
  FrameworkFreshness,
  FrameworkReadiness,
  FrameworkView,
  ReadinessStage,
} from "@/lib/api/types";

const TONE: Record<
  FrameworkFreshness,
  "ready" | "attention" | "critical" | "default"
> = {
  fresh: "ready",
  stale: "attention",
  expired: "critical",
  never_pulled: "default",
};

const TONE_TEXT: Record<FrameworkFreshness, string> = {
  fresh: "Source pulled recently",
  stale: "Source overdue for re-pull",
  expired: "Source likely outdated",
  never_pulled: "Source never pulled — provenance unverified",
};

function Row({
  framework,
  onSelect,
}: {
  framework: FrameworkView;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-4 rounded-xl border border-line bg-white p-4 text-left transition-colors hover:border-brand hover:shadow-card"
    >
      <FrameworkBadge
        frameworkId={framework.framework_id}
        fallbackLabel={framework.name}
        size={44}
      />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate font-black text-ink">{framework.name}</span>
          <Badge tone={TONE[framework.freshness_state]}>
            {framework.freshness_state.replace("_", " ")}
          </Badge>
        </div>
        <div className="mt-1 truncate text-xs text-muted">
          {framework.version}
          {framework.effective_date &&
            ` · effective ${framework.effective_date}`}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge>{framework.control_count} controls</Badge>
          {framework.implementation_status === "planned" ? (
            <Badge tone="attention">planned pack</Badge>
          ) : (
            <Badge
              tone={
                framework.mapping_coverage_pct >= 95 ? "ready" : "attention"
              }
            >
              {framework.mapping_coverage_pct}% coverage
            </Badge>
          )}
          <Badge>sync every {framework.sync_cadence_days}d</Badge>
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs text-muted">
          pulled{" "}
          {framework.pulled_age_days === null
            ? "never"
            : framework.pulled_age_days === 0
              ? "today"
              : `${framework.pulled_age_days}d ago`}
        </div>
        {framework.source_sha256 && (
          <code className="mt-1 block text-[10px] text-muted">
            sha {framework.source_sha256.slice(0, 12)}…
          </code>
        )}
      </div>
    </button>
  );
}

function Detail({
  framework,
  expandedControlId,
  onExpandedControlChange,
  onClose,
}: {
  framework: FrameworkView | null;
  expandedControlId: string | null;
  onExpandedControlChange: (controlId: string | null) => void;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={Boolean(framework)}
      onOpenChange={(o) => !o && onClose()}
      title={framework?.name ?? "Framework"}
      description={framework?.version}
      width="lg"
    >
      {framework && (
        <div className="grid gap-5 text-sm">
          <div className="flex items-center gap-3">
            <FrameworkBadge
              frameworkId={framework.framework_id}
              fallbackLabel={framework.name}
              size={56}
            />
            <div>
              <div className="font-black text-ink">{framework.name}</div>
              <div className="text-xs text-muted">{framework.version}</div>
            </div>
          </div>
          <section
            className={[
              "rounded-xl border p-3",
              framework.freshness_state === "fresh"
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : framework.freshness_state === "stale"
                  ? "border-amber-200 bg-amber-50 text-amber-900"
                  : framework.freshness_state === "expired"
                    ? "border-rose-200 bg-rose-50 text-rose-900"
                    : "border-line bg-slate-50 text-slate-700",
            ].join(" ")}
          >
            <div className="flex items-center gap-2 font-black">
              {framework.freshness_state === "fresh" ? (
                <FileCheck2 className="h-4 w-4" />
              ) : (
                <ShieldAlert className="h-4 w-4" />
              )}{" "}
              {TONE_TEXT[framework.freshness_state]}
            </div>
            <p className="mt-1 text-xs">{framework.copyright_guardrail}</p>
          </section>

          <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-1.5">
            <dt className="text-muted">Source</dt>
            <dd>
              <a
                href={framework.official_source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 break-all text-brand hover:underline"
              >
                {framework.official_source_name}{" "}
                <ExternalLink className="h-3 w-3" />
              </a>
            </dd>
            <dt className="text-muted">Effective date</dt>
            <dd className="font-extrabold">
              <Calendar className="mr-1 inline h-3 w-3" />
              {framework.effective_date ?? "—"}
            </dd>
            <dt className="text-muted">Last pulled</dt>
            <dd className="font-extrabold">
              {framework.pulled_at ?? "never (run scripts/sync_framework.py)"}
            </dd>
            <dt className="text-muted">Source sha256</dt>
            <dd>
              <code className="break-all text-xs text-ink">
                {framework.source_sha256 ?? "—"}
              </code>
            </dd>
            <dt className="text-muted">Next pull due</dt>
            <dd className="font-extrabold">{framework.next_pull_due ?? "—"}</dd>
            <dt className="text-muted">Superseded by</dt>
            <dd className="font-extrabold">{framework.superseded_by ?? "—"}</dd>
          </dl>

          <section className="rounded-xl border border-line p-3">
            <div className="text-xs font-black uppercase tracking-wide text-muted">
              Control mapping coverage
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-ink">
                {framework.implemented_control_count}
              </span>
              <span className="text-muted">
                of {framework.control_count} controls implemented
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand to-brand-green"
                style={{ width: `${framework.mapping_coverage_pct}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-muted">
              Coverage ≥ 95% is the threshold for claiming framework readiness.
              {framework.mapping_coverage_pct < 95 &&
                ` This framework is currently at ${framework.mapping_coverage_pct}% — additional mapped controls required before posture rolls up to this framework.`}
            </p>
          </section>

          <section className="grid gap-2 rounded-xl border border-line p-3">
            <FrameworkDrilldownPanel
              frameworkId={framework.framework_id}
              expandedControlId={expandedControlId}
              onExpandedControlChange={onExpandedControlChange}
            />
          </section>
        </div>
      )}
    </Drawer>
  );
}

const STAGE_ORDER: ReadinessStage[] = [
  "source_pulled",
  "mapped",
  "evidence_defined",
  "rule_versioned",
  "coverage_verified",
];

const STAGE_LABEL: Record<ReadinessStage, string> = {
  source_pulled: "Source pulled",
  mapped: "Mapped to articles",
  evidence_defined: "Evidence defined",
  rule_versioned: "Rule versioned",
  coverage_verified: "Coverage gate passed",
};

function ReadinessRow({ row }: { row: FrameworkReadiness }) {
  return (
    <div className="rounded-xl border border-line bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <FrameworkBadge
            frameworkId={row.framework_id}
            fallbackLabel={row.name}
            size={28}
          />
          <code className="text-sm font-black text-ink">
            {row.framework_id}
          </code>
        </span>
        <Badge tone={row.is_ready ? "ready" : "attention"}>
          {row.is_ready ? "ready" : `blocked at ${row.stage}`}
        </Badge>
      </div>
      <div className="mt-1 text-xs text-muted">
        {row.mapped_control_count}/{row.control_count} controls mapped ·{" "}
        {row.coverage_pct}% coverage
      </div>
      <div className="mt-3 grid grid-cols-5 gap-1">
        {STAGE_ORDER.map((stage) => {
          const passed = row.gates[stage];
          return (
            <div
              key={stage}
              className={[
                "rounded-md px-2 py-1.5 text-[10px] font-black uppercase tracking-wide",
                passed
                  ? "bg-emerald-100 text-emerald-700"
                  : stage === row.stage
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-500",
              ].join(" ")}
              title={STAGE_LABEL[stage]}
            >
              {STAGE_LABEL[stage]}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FrameworksPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const frameworks = useFrameworks();
  const readiness = useReadiness();
  const [selected, setSelected] = useState<FrameworkView | null>(null);
  const data = frameworks.data ?? [];
  const readinessRows = readiness.data ?? [];
  const frameworkParam = searchParams.get("framework");
  const controlParam = searchParams.get("control");

  useEffect(() => {
    if (!frameworkParam || data.length === 0) return;
    const match = data.find((row) => row.framework_id === frameworkParam);
    if (match) setSelected(match);
  }, [frameworkParam, data]);

  function openFramework(framework: FrameworkView) {
    setSelected(framework);
    router.replace(frameworkDetailHref(framework.framework_id), {
      scroll: false,
    });
  }

  function closeFramework() {
    setSelected(null);
    router.replace("/frameworks", { scroll: false });
  }

  function setExpandedControl(controlId: string | null) {
    if (!selected) return;
    router.replace(frameworkDetailHref(selected.framework_id, controlId), {
      scroll: false,
    });
  }

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Frameworks"
        title="Framework provenance"
        description="Framework contracts define what deterministic eval can prove. Each framework declares its official source, version, sha256, effective date, and mapping coverage."
        actions={
          <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
            <FileCheck2 className="mr-1 inline h-3 w-3 text-emerald-600" />{" "}
            {data.length} loaded
          </span>
        }
      />
      <TrustPipelineStrip activeStage="frameworks" />

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Staged readiness</CardTitle>
          <CardDescription>
            Coverage is verified after every gate is green: source pulled,
            controls mapped to source articles, evidence requirements declared,
            evaluation rules versioned, and mapping coverage ≥ 95%. The earliest
            unmet gate is highlighted amber.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {readinessRows.length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
              Loading readiness…
            </div>
          )}
          {readinessRows.map((row) => (
            <ReadinessRow key={row.framework_id} row={row} />
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>{data.length} frameworks</CardTitle>
          <CardDescription>
            Provenance is the contract: source URL + sha256 + last-pulled
            timestamp + mapping coverage. Frameworks past their sync cadence are
            flagged stale or expired.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {data.length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
              No frameworks registered. Check{" "}
              <code>frameworks/registry.json</code>.
            </div>
          )}
          {data.map((f) => (
            <Row
              key={f.framework_id}
              framework={f}
              onSelect={() => openFramework(f)}
            />
          ))}
        </div>
      </Card>

      <Detail
        framework={selected}
        expandedControlId={controlParam}
        onExpandedControlChange={setExpandedControl}
        onClose={closeFramework}
      />
    </div>
  );
}

export default function FrameworksPage() {
  return (
    <Suspense
      fallback={
        <div className="px-4 py-5 text-sm text-muted">Loading frameworks…</div>
      }
    >
      <FrameworksPageContent />
    </Suspense>
  );
}
