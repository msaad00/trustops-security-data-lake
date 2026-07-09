"use client";

import Link from "next/link";
import { ArrowRight, Layers, Plug, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { KpiTile } from "@/components/ui/KpiTile";
import { useIngestionStatus } from "@/lib/api/hooks";

function formatRate(rate: number | undefined) {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

export function ConnectorIntegrationCoverage() {
  const ingestion = useIngestionStatus();
  const coverage = ingestion.data?.catalog_coverage;
  const accuracy = ingestion.data?.eval_accuracy;

  return (
    <QueryState queries={[ingestion]} label="integration coverage">
      {coverage && (
        <Card>
          <CardContent className="grid gap-4 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Layers className="h-4 w-4 text-brand" />
                  <span className="text-sm font-black text-ink">
                    Integration breadth
                  </span>
                  <Badge tone="info">
                    {coverage.implemented}/{coverage.total} implemented
                  </Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted">
                  Catalog coverage vs live adapters and enabled sources — depth
                  for managed GRC-style connector programs.
                </p>
              </div>
              <Link
                href="/connectors"
                className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
              >
                Manage connectors
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiTile
                label="Catalog"
                value={coverage.total}
                detail={`${coverage.implemented} with live adapters`}
                icon={<Plug className="h-4 w-4" />}
              />
              <KpiTile
                label="Implementation"
                value={formatRate(coverage.implementation_rate)}
                detail="share of catalog with collection code"
                tone={coverage.implementation_rate >= 0.5 ? "ready" : "attention"}
              />
              <KpiTile
                label="Enabled"
                value={`${coverage.enabled}/${coverage.implemented}`}
                detail={`${formatRate(coverage.enabled_rate)} of implemented`}
                tone={coverage.enabled > 0 ? "ready" : "attention"}
              />
              <KpiTile
                label="Eval accuracy"
                value={
                  accuracy?.pass_rate != null
                    ? formatRate(accuracy.pass_rate)
                    : "—"
                }
                detail={
                  accuracy?.has_tests
                    ? `${accuracy.failing} failing · ${accuracy.evidence_source_count} evidence sources`
                    : "run lake eval for control tests"
                }
                tone={
                  accuracy && accuracy.failing > 0
                    ? "attention"
                    : accuracy?.has_tests
                      ? "ready"
                      : "default"
                }
                icon={<ShieldCheck className="h-4 w-4" />}
              />
            </div>

            {coverage.by_category.length > 0 && (
              <div className="rounded-lg border border-line bg-panel p-3">
                <div className="text-xs font-black uppercase tracking-wide text-muted">
                  By category
                </div>
                <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {coverage.by_category.map((row) => (
                    <div
                      key={row.category}
                      className="rounded-md border border-line bg-white px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-bold capitalize text-ink">
                          {row.category.replace(/_/g, " ")}
                        </span>
                        <Badge tone={row.implemented > 0 ? "ready" : "attention"}>
                          {row.implemented}/{row.total}
                        </Badge>
                      </div>
                      <p className="mt-1 text-[11px] text-muted">
                        {row.enabled} enabled
                        {row.implemented < row.total
                          ? ` · ${row.total - row.implemented} contract-only`
                          : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
