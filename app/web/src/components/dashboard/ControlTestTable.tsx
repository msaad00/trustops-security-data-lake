"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown } from "lucide-react";
import type { ControlTest } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const helper = createColumnHelper<ControlTest>();

const toneFor = (result: string) =>
  result === "pass" ? "ready" : result === "fail" ? "critical" : "attention";

export function ControlTestTable({ rows }: { rows: ControlTest[] }) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "result", desc: false },
  ]);

  const columns = [
    helper.accessor("name", {
      header: "Test",
      cell: (info) => (
        <div>
          <b className="block">{info.getValue()}</b>
          <span className="block text-xs text-muted">
            {info.row.original.control_id} · {info.row.original.next_action}
          </span>
        </div>
      ),
    }),
    helper.accessor("owner", {
      header: "Owner",
      cell: (info) => (
        <span className="inline-flex items-center gap-2 text-xs font-extrabold">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-blue-50 text-[11px] font-black text-blue-700">
            {info.getValue().slice(0, 1).toUpperCase()}
          </span>
          {info.getValue()}
        </span>
      ),
    }),
    helper.accessor("result", {
      header: "Result",
      cell: (info) => {
        const v = info.getValue();
        return (
          <div>
            <Badge tone={toneFor(v) as "ready" | "critical" | "attention"}>
              {v}
            </Badge>
            <div className="mt-1 text-xs text-muted">
              {info.row.original.confidence_score}% confidence
            </div>
          </div>
        );
      },
    }),
    helper.accessor("freshness_status", {
      header: "Freshness",
      cell: (info) => <Badge tone="info">{info.getValue()}</Badge>,
    }),
    helper.accessor("agent_skill", {
      header: "Skill",
      cell: (info) => (
        <code className="text-xs text-ink">{info.getValue()}</code>
      ),
    }),
  ];

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Live control test queue</CardTitle>
        <CardDescription>
          Sorted by result, freshness, and confidence for reviewer-ready triage.
        </CardDescription>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-y border-line bg-slate-50/60">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    className="cursor-pointer px-4 py-3 text-left text-[11px] font-black uppercase tracking-wide text-muted"
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      <ArrowUpDown className="h-3 w-3 opacity-50" />
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
                className="border-b border-line last:border-0 hover:bg-blue-50/40"
              >
                {r.getVisibleCells().map((c) => (
                  <td key={c.id} className="px-4 py-3 align-top">
                    {flexRender(c.column.columnDef.cell, c.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  className="px-4 py-6 text-center text-sm text-muted"
                  colSpan={5}
                >
                  No control tests reported by the assessment engine.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
