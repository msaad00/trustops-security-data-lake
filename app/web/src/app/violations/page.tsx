"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  createColumnHelper,
  flexRender,
  useTable,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { SavedViewsBar } from "@/components/SavedViewsBar";
import { QueryState } from "@/components/QueryState";
import { TrustPipelineStrip } from "@/components/TrustPipelineStrip";
import { notify } from "@/lib/toast";
import { Toolbar, matchesQuery } from "@/components/Toolbar";
import { TagFilterBar } from "@/components/TagFilterBar";
import { ViolationDrawer } from "@/components/drawers/ViolationDrawer";
import {
  useControls,
  useTagEntityIds,
  useViolations,
  useTags,
} from "@/lib/api/hooks";
import { useToolbar } from "@/lib/state/filters";
import {
  sortableTableFeatures,
  type SortableColumnDefs,
} from "@/lib/table-features";
import type { Severity, Violation } from "@/lib/api/types";

const helper = createColumnHelper<typeof sortableTableFeatures, Violation>();

const toneForSeverity = (s: string) =>
  s === "critical" ? "critical" : s === "high" ? "attention" : "info";

const SURFACE = "violations";

function ViolationsPageContent() {
  const violations = useViolations();
  const controls = useControls();
  const tagsQuery = useTags();
  const searchParams = useSearchParams();

  const { filters, setFilters } = useToolbar();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "severity_score", desc: true },
  ]);
  const [selected, setSelected] = useState<Violation | null>(null);
  const [activeTagId, setActiveTagId] = useState<string | null>(null);

  const deepLinkId = searchParams.get("id");
  useEffect(() => {
    if (!deepLinkId || !violations.data) return;
    const match = violations.data.find((v) => v.violation_id === deepLinkId);
    if (match) setSelected(match);
  }, [deepLinkId, violations.data]);
  const taggedViolations = useTagEntityIds(activeTagId, "violation");
  const taggedIds = useMemo(
    () => new Set(taggedViolations.data ?? []),
    [taggedViolations.data],
  );

  const frameworks = useMemo(
    () => Array.from(new Set((controls.data ?? []).map((c) => c.framework))),
    [controls.data],
  );

  const controlFramework = useMemo(() => {
    const map = new Map<string, string>();
    (controls.data ?? []).forEach((c) => map.set(c.control_id, c.framework));
    return map;
  }, [controls.data]);

  const filtered = useMemo(
    () =>
      (violations.data ?? []).filter((v) => {
        if (activeTagId && !taggedIds.has(v.violation_id)) return false;
        if (
          filters.framework !== "all" &&
          controlFramework.get(v.control_id) !== filters.framework
        )
          return false;
        if (filters.severity !== "all" && v.severity !== filters.severity)
          return false;
        return matchesQuery(v, filters.query);
      }),
    [violations.data, filters, controlFramework, activeTagId, taggedIds],
  );

  const columns: SortableColumnDefs<Violation> = [
    helper.accessor("violation_id", {
      header: "Violation",
      cell: (info) => (
        <div>
          <code className="text-xs text-ink">{info.getValue()}</code>
          <div className="text-xs text-muted">
            {info.row.original.event_type}
          </div>
        </div>
      ),
    }),
    helper.accessor("control_id", {
      header: "Control",
      cell: (info) => <code className="text-xs">{info.getValue()}</code>,
    }),
    helper.accessor("asset_id", {
      header: "Asset",
      cell: (info) => (
        <div>
          <code className="text-xs text-ink">{info.getValue()}</code>
          <div className="text-xs text-muted">
            {info.row.original.asset_owner}
          </div>
        </div>
      ),
    }),
    helper.accessor("severity", {
      header: "Severity",
      cell: (info) => {
        const v = info.getValue() as string;
        return (
          <div>
            <Badge tone={toneForSeverity(v)}>{v}</Badge>
            <div className="mt-1 text-xs text-muted">
              score {info.row.original.severity_score}
            </div>
          </div>
        );
      },
    }),
    helper.accessor("severity_score", {
      header: "Score",
      cell: (info) => info.getValue(),
    }),
    helper.accessor("source", {
      header: "Source",
      cell: (info) => <Badge>{info.getValue()}</Badge>,
    }),
    helper.accessor("evidence_ref", {
      header: "Evidence",
      cell: (info) => <code className="text-xs">{info.getValue()}</code>,
    }),
  ];

  const table = useTable({
    features: sortableTableFeatures,
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
  });

  const tags = tagsQuery.data ?? [];

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Findings"
        title="Findings queue"
        description="Failed deterministic controls with severity, asset, source, and evidence reference. Click a row to triage and persist the action server-side."
      />
      <TrustPipelineStrip activeStage="findings" />

      <TagFilterBar
        tags={tags}
        activeTagId={activeTagId}
        onSelect={setActiveTagId}
        onClear={() => setActiveTagId(null)}
      />

      {/* Saved views */}
      <SavedViewsBar
        surface={SURFACE}
        filters={{
          framework: filters.framework,
          severity: filters.severity,
          query: filters.query,
        }}
        onApply={(viewFilters) =>
          setFilters({
            framework: (viewFilters.framework as string) ?? "all",
            severity: (viewFilters.severity as Severity | "all") ?? "all",
            query: (viewFilters.query as string) ?? "",
          })
        }
      />

      <Toolbar
        filters={filters}
        frameworks={frameworks}
        onChange={setFilters}
        placeholder="Search by violation, asset, source, owner…"
      />
      <QueryState queries={violations} label="violations">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{filtered.length} open violations</CardTitle>
            <CardDescription>
              Click any column to re-sort. Click any row to open the triage
              drawer.
            </CardDescription>
          </CardHeader>
          <div
            className="overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Open violations table"
          >
            <table className="min-w-[820px] w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr
                    key={hg.id}
                    className="border-y border-line bg-slate-50/60"
                  >
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        onClick={h.column.getToggleSortingHandler()}
                        className="cursor-pointer px-4 py-3 text-left text-[11px] font-black uppercase tracking-wide text-muted"
                      >
                        <span className="inline-flex items-center gap-1">
                          {flexRender(
                            h.column.columnDef.header,
                            h.getContext(),
                          )}
                          {h.column.getCanSort() && (
                            <ArrowUpDown className="h-3 w-3 opacity-40" />
                          )}
                        </span>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => setSelected(r.original)}
                    className="cursor-pointer border-b border-line last:border-0 hover:bg-blue-50/40"
                  >
                    {r.getVisibleCells().map((c) => (
                      <td key={c.id} className="px-4 py-3 align-top">
                        {flexRender(c.column.columnDef.cell, c.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      className="px-4 py-8 text-center text-sm text-muted"
                      colSpan={columns.length}
                    >
                      No violations match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </QueryState>
      <ViolationDrawer
        violation={selected}
        onClose={() => setSelected(null)}
        onToast={notify.success}
      />
    </div>
  );
}

export default function ViolationsPage() {
  return (
    <Suspense
      fallback={
        <div className="px-4 py-5 text-sm text-muted">Loading findings…</div>
      }
    >
      <ViolationsPageContent />
    </Suspense>
  );
}
