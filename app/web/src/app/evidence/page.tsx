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
import { ArrowUpDown, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import { Toolbar, matchesQuery } from "@/components/Toolbar";
import { EvidenceDrawer } from "@/components/drawers/EvidenceDrawer";
import { useControls, useEvidence } from "@/lib/api/hooks";
import { useToolbar } from "@/lib/state/filters";
import type { NormalizedEvent } from "@/lib/api/types";

const helper = createColumnHelper<NormalizedEvent>();

const toneForStatus = (status: string) =>
  status === "passed"
    ? "ready"
    : status === "blocked" || status === "failed"
      ? "critical"
      : "attention";

export default function EvidencePage() {
  const evidence = useEvidence();
  const controls = useControls();
  const { filters, setFilters } = useToolbar();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "event_time", desc: true },
  ]);
  const [selected, setSelected] = useState<NormalizedEvent | null>(null);

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
      (evidence.data ?? []).filter((e) => {
        if (filters.framework !== "all") {
          const hit = e.control_ids.some(
            (cid) => controlFramework.get(cid) === filters.framework,
          );
          if (!hit) return false;
        }
        if (filters.severity !== "all" && e.severity !== filters.severity)
          return false;
        return matchesQuery(e, filters.query);
      }),
    [evidence.data, filters, controlFramework],
  );

  const columns = [
    helper.accessor("event_time", {
      header: "Time",
      cell: (info) => (
        <code className="text-xs text-ink">
          {String(info.getValue()).slice(0, 19)}
        </code>
      ),
    }),
    helper.accessor("source", {
      header: "Source",
      cell: (info) => <Badge tone="info">{info.getValue()}</Badge>,
    }),
    helper.accessor("asset_id", {
      header: "Asset",
      cell: (info) => (
        <div className="min-w-[160px] max-w-[260px]">
          <code className="break-all text-xs text-ink">{info.getValue()}</code>
          <div className="text-xs text-muted">
            {info.row.original.asset_owner}
          </div>
        </div>
      ),
    }),
    helper.accessor("control_ids", {
      header: "Controls",
      cell: (info) => (
        <div className="flex flex-wrap gap-1">
          {(info.getValue() as string[]).map((c) => (
            <Badge key={c}>{c}</Badge>
          ))}
        </div>
      ),
    }),
    helper.accessor("status", {
      header: "Status",
      cell: (info) => {
        const v = info.getValue() as string;
        return <Badge tone={toneForStatus(v)}>{v}</Badge>;
      },
    }),
    helper.accessor("evidence_ref", {
      header: "Evidence ref",
      cell: (info) => (
        <code className="block min-w-[180px] max-w-[360px] break-all text-xs">
          {info.getValue()}
        </code>
      ),
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

  return (
    <div className="mx-auto grid w-full max-w-[1500px] min-w-0 gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Evidence room"
        title="Normalized evidence facts"
        description="Click any row to open the evidence drawer and verify the SHA-256 hash against the immutable bronze record server-side."
        actions={
          <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
            <ShieldCheck className="mr-1 inline h-3 w-3 text-emerald-600" />
            {(evidence.data ?? []).length} normalized
          </span>
        }
      />
      <Toolbar
        filters={filters}
        frameworks={frameworks}
        onChange={setFilters}
        placeholder="Search by source, asset, evidence ref, control…"
      />
      <QueryState queries={evidence} label="evidence">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{filtered.length} matching records</CardTitle>
            <CardDescription>
              All rows are append-only silver facts written from immutable
              bronze evidence.
            </CardDescription>
          </CardHeader>
          <div className="max-w-full overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
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
                        className="cursor-pointer px-3 py-2.5 text-left text-[10px] font-black uppercase tracking-wide text-muted"
                      >
                        <span className="inline-flex items-center gap-1">
                          {flexRender(
                            h.column.columnDef.header,
                            h.getContext(),
                          )}
                          <ArrowUpDown className="h-3 w-3 opacity-40" />
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
                      <td key={c.id} className="px-3 py-2.5 align-top">
                        {flexRender(c.column.columnDef.cell, c.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      className="px-3 py-7 text-center text-sm text-muted"
                    >
                      No evidence records match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </QueryState>
      <EvidenceDrawer evidence={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
