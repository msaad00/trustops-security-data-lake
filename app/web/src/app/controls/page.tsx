"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import { resolveFrameworkId } from "@/lib/framework-visuals";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { SavedViewsBar } from "@/components/SavedViewsBar";
import { TagFilterBar } from "@/components/TagFilterBar";
import { TrustPipelineStrip } from "@/components/TrustPipelineStrip";
import { QueryState } from "@/components/QueryState";
import { notify } from "@/lib/toast";
import { Toolbar, matchesQuery } from "@/components/Toolbar";
import { ControlDrawer } from "@/components/drawers/ControlDrawer";
import { ViolationDrawer } from "@/components/drawers/ViolationDrawer";
import {
  useControls,
  useControlTests,
  usePosture,
  useTagEntityIds,
  useTags,
} from "@/lib/api/hooks";
import { useToolbar } from "@/lib/state/filters";
import { cn } from "@/lib/utils";
import { ControlMonitoringSummary } from "@/components/controls/ControlMonitoringSummary";
import { ControlTestTable } from "@/components/dashboard/ControlTestTable";
import type { ControlPosture, Violation } from "@/lib/api/types";

const SURFACE = "controls";

const toneForStatus = (status: string) =>
  status === "pass" ? "ready" : status === "fail" ? "critical" : "attention";

function ControlRow({
  control,
  onSelect,
  confidence,
}: {
  control: ControlPosture;
  onSelect: () => void;
  confidence?: number;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "block w-full rounded-xl border border-line bg-white p-3 text-left transition-colors hover:border-brand hover:shadow-card",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <code className="text-sm font-black text-ink">
          {control.control_id}
        </code>
        <Badge tone={toneForStatus(control.status)}>{control.status}</Badge>
      </div>
      <div className="mt-1 text-sm text-ink">{control.title}</div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <FrameworkBadge
          frameworkId={resolveFrameworkId(control.framework)}
          fallbackLabel={control.framework}
          variant="compact"
          size={28}
        />
        <Badge>{control.owner}</Badge>
        <Badge tone={Number(control.risk_score) >= 80 ? "critical" : "default"}>
          risk {control.risk_score}
        </Badge>
        <Badge>
          evidence {control.evidence_count}/{control.event_count}
        </Badge>
        {confidence !== undefined && (
          <Badge tone={confidence >= 75 ? "ready" : "attention"}>
            test {confidence}%
          </Badge>
        )}
      </div>
    </button>
  );
}

export default function ControlsPage() {
  const controls = useControls();
  const tests = useControlTests();
  const posture = usePosture();
  const tagsQuery = useTags();
  const { filters, setFilters } = useToolbar();
  const [selected, setSelected] = useState<ControlPosture | null>(null);
  const [violation, setViolation] = useState<Violation | null>(null);
  const [activeTagId, setActiveTagId] = useState<string | null>(null);
  const taggedControls = useTagEntityIds(activeTagId, "control");
  const taggedIds = useMemo(
    () => new Set(taggedControls.data ?? []),
    [taggedControls.data],
  );
  const tags = tagsQuery.data ?? [];

  const frameworks = useMemo(
    () => Array.from(new Set((controls.data ?? []).map((c) => c.framework))),
    [controls.data],
  );

  const filtered = useMemo(
    () =>
      (controls.data ?? []).filter((c) => {
        if (activeTagId && !taggedIds.has(c.control_id)) return false;
        return (
          (filters.framework === "all" || c.framework === filters.framework) &&
          matchesQuery(c, filters.query)
        );
      }),
    [controls.data, filters, activeTagId, taggedIds],
  );

  const openViolation = (violationId: string) => {
    const v = (posture.data?.violations ?? []).find(
      (row) => row.violation_id === violationId,
    );
    if (v) setViolation(v);
  };

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Continuous control monitoring"
        title="Control workbench"
        description="Deterministic gold control results from normalized evidence. Filter by result, framework, and owner, then drill into any control for evidence and remediation."
      />
      <TrustPipelineStrip activeStage="controls" />
      <QueryState queries={[tests]} label="control tests">
        <ControlMonitoringSummary rows={tests.data ?? []} />
        {(tests.data ?? []).some((t) => t.result !== "pass") ? (
          <ControlTestTable rows={tests.data ?? []} />
        ) : null}
      </QueryState>
      <TagFilterBar
        tags={tags}
        activeTagId={activeTagId}
        onSelect={setActiveTagId}
        onClear={() => setActiveTagId(null)}
      />
      <SavedViewsBar
        surface={SURFACE}
        filters={{
          framework: filters.framework,
          query: filters.query,
        }}
        onApply={(viewFilters) =>
          setFilters({
            ...filters,
            framework: (viewFilters.framework as string) ?? "all",
            query: (viewFilters.query as string) ?? "",
          })
        }
      />
      <Toolbar
        filters={filters}
        frameworks={frameworks}
        onChange={setFilters}
        placeholder="Search by control id, title, framework, owner…"
      />
      <QueryState queries={controls} label="controls">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{filtered.length} controls</CardTitle>
            <CardDescription>
              Click a control to inspect evidence, violations, owner, and
              API-safe facts.
            </CardDescription>
          </CardHeader>
          <div className="grid gap-2 p-5 pt-0 lg:grid-cols-2">
            {filtered.length === 0 && (
              <div className="col-span-full rounded-lg border border-dashed border-line p-4 text-sm text-muted">
                No controls match the current filters.
              </div>
            )}
            {filtered.map((c) => {
              const t = (tests.data ?? []).find(
                (x) => x.control_id === c.control_id,
              );
              return (
                <ControlRow
                  key={c.control_id}
                  control={c}
                  onSelect={() => setSelected(c)}
                  confidence={t?.confidence_score}
                />
              );
            })}
          </div>
        </Card>
      </QueryState>
      <ControlDrawer
        control={selected}
        onClose={() => setSelected(null)}
        onOpenViolation={openViolation}
      />
      <ViolationDrawer
        violation={violation}
        onClose={() => setViolation(null)}
        onToast={notify.success}
      />
    </div>
  );
}
