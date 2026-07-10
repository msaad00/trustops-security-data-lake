"use client";

import Link from "next/link";
import { Bot, BrainCircuit, CheckCircle2, CircleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { KpiTile } from "@/components/ui/KpiTile";
import { useAiGovernance, useAiInventory } from "@/lib/api/hooks";

const STATE_COPY: Record<
  string,
  { label: string; tone: "ready" | "attention" | "critical" }
> = {
  governed: { label: "Governed", tone: "ready" },
  on_track: { label: "On track", tone: "attention" },
  needs_work: { label: "Needs work", tone: "critical" },
};

function loopTone(active: boolean): "ready" | "attention" {
  return active ? "ready" : "attention";
}

export function AiGovernanceStrip() {
  const governance = useAiGovernance();
  const inventory = useAiInventory(6);

  return (
    <QueryState queries={[governance, inventory]} label="AI governance">
      {governance.data && (
        <Card>
          <CardContent className="grid gap-4 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <BrainCircuit className="h-4 w-4 text-brand" />
                  <span className="text-sm font-black text-ink">
                    AI governance evidence
                  </span>
                  <Badge
                    tone={
                      STATE_COPY[governance.data.state]?.tone ?? "attention"
                    }
                  >
                    {STATE_COPY[governance.data.state]?.label ??
                      governance.data.state}
                  </Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted">
                  Model inventory, lineage events, model cards, and agent
                  runtime signals mapped to NIST AI RMF, ISO 42001, and EU AI
                  Act — same evidence bucket as managed GRC AI programs (not
                  formal AIBOM files).
                </p>
              </div>
              <Link
                href="/ai-governance"
                className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
              >
                <Bot className="h-3.5 w-3.5" />
                Full inventory
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <KpiTile
                label="Governance score"
                value={`${governance.data.governance_score}%`}
                detail={`${governance.data.frameworks_ready}/${governance.data.frameworks_total} frameworks ready`}
                tone={
                  governance.data.governance_score >= 85
                    ? "ready"
                    : governance.data.governance_score >= 60
                      ? "attention"
                      : "critical"
                }
              />
              <KpiTile
                label="Models in inventory"
                value={String(governance.data.inventory.models)}
                detail={`${governance.data.inventory.with_model_card} with model card`}
                tone={
                  governance.data.inventory.models > 0 ? "default" : "attention"
                }
              />
              <KpiTile
                label="AI agents"
                value={String(governance.data.inventory.agents)}
                detail={`${governance.data.events.agent_runtime} runtime event(s)`}
                tone={
                  governance.data.inventory.agents > 0 ? "default" : "attention"
                }
              />
              <KpiTile
                label="Lineage signals"
                value={String(governance.data.events.model_lineage)}
                detail={`${governance.data.inventory.with_lineage} asset(s) lineage-complete`}
                tone={loopTone(governance.data.evidence_loops.lineage_events)}
              />
              <KpiTile
                label="Model cards / repo artifacts"
                value={String(governance.data.artifacts.model_cards)}
                detail={`${governance.data.events.repo_artifacts} repo ai_artifact signal(s)`}
                tone={loopTone(governance.data.evidence_loops.model_cards)}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              {governance.data.frameworks.map((framework) => (
                <div
                  key={framework.framework_id}
                  className="rounded-lg border border-line bg-surface px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-ink">
                      {framework.label}
                    </span>
                    <Badge tone={framework.score >= 85 ? "ready" : "attention"}>
                      {framework.score}%
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {framework.controls_covered}/{framework.controls_mapped}{" "}
                    controls covered · {framework.coverage_pct}% mapped
                  </p>
                </div>
              ))}
            </div>

            {inventory.data && inventory.data.length > 0 ? (
              <div className="grid gap-2">
                <span className="text-xs font-bold uppercase tracking-wide text-muted">
                  Inventory sample
                </span>
                {inventory.data.map((item) => (
                  <div
                    key={item.asset_id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-surfaceMuted px-3 py-2 text-xs"
                  >
                    <div className="min-w-0">
                      <span className="font-bold text-ink">
                        {item.asset_id}
                      </span>
                      <span className="ml-2 text-muted">
                        {item.asset_type} · {item.owner || "unowned"}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {item.model_card ? (
                        <Badge tone="ready">model card</Badge>
                      ) : null}
                      {item.lineage_complete ||
                      item.event_types.includes("model.lineage") ? (
                        <Badge tone="ready">lineage</Badge>
                      ) : null}
                      {item.event_types.includes("runtime.tool_call") ? (
                        <Badge tone="attention">runtime</Badge>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}

            {governance.data.gaps.length > 0 ? (
              <div className="grid gap-2">
                {governance.data.gaps.map((gap) => (
                  <Link
                    key={gap.id}
                    href={
                      gap.href.startsWith("/console")
                        ? gap.href.replace(/^\/console/, "")
                        : gap.href
                    }
                    className="flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-xs hover:bg-surfaceMuted"
                  >
                    <CircleAlert className="h-3.5 w-3.5 shrink-0 text-brand-orange" />
                    <span className="font-bold text-ink">{gap.label}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs text-muted">
                <CheckCircle2 className="h-4 w-4 text-brand" />
                Inventory, lineage, model-card, and agent governance evidence
                loops are active.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
