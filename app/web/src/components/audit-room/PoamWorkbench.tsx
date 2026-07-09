"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { usePoamItems, useUpdatePoamItemMutation } from "@/lib/api/hooks";
import type { PoamItem } from "@/lib/api/types";

const STATUSES: PoamItem["status"][] = [
  "open",
  "in_progress",
  "completed",
  "risk_accepted",
];

const inputClass =
  "w-full min-w-0 rounded-md border border-line bg-white px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-brand";

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function PoamRow({ item }: { item: PoamItem }) {
  const update = useUpdatePoamItemMutation();
  const [status, setStatus] = useState(item.status);
  const [owner, setOwner] = useState(item.owner);
  const [milestone, setMilestone] = useState(item.milestone);
  const [dueAt, setDueAt] = useState(
    item.due_at ? item.due_at.slice(0, 10) : "",
  );

  const dirty =
    status !== item.status ||
    owner !== item.owner ||
    milestone !== item.milestone ||
    dueAt !== (item.due_at ? item.due_at.slice(0, 10) : "");

  const save = () => {
    update.mutate({
      id: item.id,
      payload: {
        status,
        owner,
        milestone,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      },
    });
  };

  return (
    <tr className="border-t border-line align-top">
      <td className="px-3 py-2 text-xs">
        <div className="font-bold text-ink">{item.requirement_id}</div>
        <div className="mt-0.5 text-muted">{item.title}</div>
        <div className="mt-1 text-[10px] text-muted">{item.control_id}</div>
      </td>
      <td className="px-3 py-2">
        <select
          className={inputClass}
          value={status}
          onChange={(e) => setStatus(e.target.value as PoamItem["status"])}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2">
        <input
          className={inputClass}
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          placeholder="owner"
        />
      </td>
      <td className="px-3 py-2">
        <input
          className={inputClass}
          value={milestone}
          onChange={(e) => setMilestone(e.target.value)}
          placeholder="milestone"
        />
      </td>
      <td className="px-3 py-2">
        <input
          className={inputClass}
          type="date"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
        />
        <div className="mt-1 text-[10px] text-muted">
          was {fmtDate(item.due_at)}
        </div>
      </td>
      <td className="px-3 py-2 text-center text-xs font-bold text-ink">
        {item.sprs_points}
      </td>
      <td className="px-3 py-2">
        <Button
          size="sm"
          variant={dirty ? "default" : "ghost"}
          disabled={!dirty || update.isPending}
          onClick={save}
        >
          {update.isPending ? "…" : "Save"}
        </Button>
      </td>
    </tr>
  );
}

export function PoamWorkbench() {
  const poam = usePoamItems({ framework_id: "cmmc-2-level2" });
  const rows = poam.data ?? [];
  const openCount = rows.filter((row) => row.status === "open").length;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
        <div>
          <CardTitle className="text-base">POA&M workbench</CardTitle>
          <p className="mt-1 text-xs text-muted">
            Milestone-tracked CMMC gaps synced from SPRS deductions — edit
            owner, milestone, and status for assessors.
          </p>
        </div>
        <Badge tone={openCount > 0 ? "attention" : "ready"}>
          {openCount} open
        </Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0 pb-3">
        <QueryState queries={poam} label="POA&M items">
          {rows.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted">
              No POA&M items yet. Use Sync POA&M above after failing NIST SP
              800-171 practices appear in posture.
            </p>
          ) : (
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-surfaceMuted text-[10px] font-black uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-3 py-2">Requirement</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Owner</th>
                  <th className="px-3 py-2">Milestone</th>
                  <th className="px-3 py-2">Due</th>
                  <th className="px-3 py-2 text-center">SPRS</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <PoamRow key={item.id} item={item} />
                ))}
              </tbody>
            </table>
          )}
        </QueryState>
      </CardContent>
    </Card>
  );
}
