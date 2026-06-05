"use client";

import { useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  Bookmark,
  BookmarkCheck,
  Tag as TagIcon,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import { notify } from "@/lib/toast";
import { Toolbar, matchesQuery } from "@/components/Toolbar";
import { TagChip } from "@/components/TagChip";
import { ViolationDrawer } from "@/components/drawers/ViolationDrawer";
import {
  useControls,
  useViolations,
  useTags,
  useSavedViews,
  useCreateSavedViewMutation,
  useDeleteSavedViewMutation,
} from "@/lib/api/hooks";
import { useToolbar } from "@/lib/state/filters";
import type { Severity, Violation } from "@/lib/api/types";

const helper = createColumnHelper<Violation>();

const toneForSeverity = (s: string) =>
  s === "critical" ? "critical" : s === "high" ? "attention" : "info";

const SURFACE = "violations";

export default function ViolationsPage() {
  const violations = useViolations();
  const controls = useControls();
  const tagsQuery = useTags();
  const savedViewsQuery = useSavedViews(SURFACE);
  const createView = useCreateSavedViewMutation();
  const deleteView = useDeleteSavedViewMutation();

  const { filters, setFilters } = useToolbar();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "severity_score", desc: true },
  ]);
  const [selected, setSelected] = useState<Violation | null>(null);
  const [activeTagId, setActiveTagId] = useState<string | null>(null);
  const [saveViewName, setSaveViewName] = useState("");
  const [showSavePanel, setShowSavePanel] = useState(false);

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
        if (
          filters.framework !== "all" &&
          controlFramework.get(v.control_id) !== filters.framework
        )
          return false;
        if (filters.severity !== "all" && v.severity !== filters.severity)
          return false;
        return matchesQuery(v, filters.query);
      }),
    [violations.data, filters, controlFramework],
  );

  const columns = [
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

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const tags = tagsQuery.data ?? [];
  const savedViews = savedViewsQuery.data ?? [];

  function applyView(view: { filters: Record<string, unknown> }) {
    setFilters({
      framework: (view.filters.framework as string) ?? "all",
      severity: (view.filters.severity as Severity | "all") ?? "all",
      query: (view.filters.query as string) ?? "",
    });
  }

  function handleSaveView() {
    if (!saveViewName.trim()) return;
    createView.mutate(
      {
        surface: SURFACE,
        name: saveViewName.trim(),
        filters: {
          framework: filters.framework,
          severity: filters.severity,
          query: filters.query,
        },
      },
      {
        onSuccess: () => {
          setSaveViewName("");
          setShowSavePanel(false);
          notify.success("View saved");
        },
      },
    );
  }

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Violations"
        title="Violation queue"
        description="Open control failures with severity, asset, source, and evidence reference. Click a row to triage and persist the action server-side."
      />

      {/* Tag filter strip */}
      {tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
            <TagIcon className="h-3 w-3" />
            Tags
          </span>
          {tags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() =>
                setActiveTagId(activeTagId === tag.id ? null : tag.id)
              }
              className={`rounded-full outline-none ring-offset-1 focus:ring-2 focus:ring-violet-500 ${
                activeTagId === tag.id
                  ? "ring-2 ring-violet-500 ring-offset-1"
                  : ""
              }`}
            >
              <TagChip tag={tag} />
            </button>
          ))}
          {activeTagId && (
            <button
              type="button"
              onClick={() => setActiveTagId(null)}
              className="flex items-center gap-1 text-[11px] text-muted hover:text-ink"
            >
              <X className="h-3 w-3" />
              clear
            </button>
          )}
        </div>
      )}

      {/* Saved views */}
      {(savedViews.length > 0 || true) && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
            <Bookmark className="h-3 w-3" />
            Saved views
          </span>
          {savedViews.map((view) => (
            <div key={view.id} className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => applyView(view)}
                className="rounded-md border border-line bg-white px-2 py-0.5 text-[11px] font-medium text-ink hover:bg-slate-50"
              >
                {view.name}
              </button>
              <button
                type="button"
                onClick={() =>
                  deleteView.mutate(
                    { viewId: view.id, surface: SURFACE },
                    {
                      onSuccess: () => {
                        notify.success("View deleted");
                      },
                    },
                  )
                }
                className="rounded p-0.5 text-muted hover:text-ink"
                aria-label="Delete saved view"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setShowSavePanel(!showSavePanel)}
            className="flex items-center gap-1 rounded-md border border-line bg-white px-2 py-0.5 text-[11px] font-medium text-muted hover:text-ink"
          >
            <BookmarkCheck className="h-3 w-3" />
            Save current
          </button>
          {showSavePanel && (
            <div className="flex items-center gap-1">
              <input
                value={saveViewName}
                onChange={(e) => setSaveViewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveView()}
                placeholder="View name…"
                className="rounded border border-line px-2 py-0.5 text-[11px] focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <button
                type="button"
                onClick={handleSaveView}
                className="rounded bg-violet-600 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-violet-700"
              >
                Save
              </button>
            </div>
          )}
        </div>
      )}

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
          <div className="overflow-x-auto">
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
