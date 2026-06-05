"use client";

import { useState } from "react";
import { Activity, ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import { useAuditLog } from "@/lib/api/hooks";
import type { AuditLogEntry } from "@/lib/api/types";

const CATEGORIES: Array<AuditLogEntry["category"] | "all"> = [
  "all",
  "triage",
  "connector",
  "snapshot",
  "workflow",
  "trust_share",
];

const CATEGORY_TONE: Record<
  AuditLogEntry["category"],
  "info" | "ready" | "attention" | "critical" | "default"
> = {
  triage: "attention",
  connector: "info",
  snapshot: "ready",
  workflow: "ready",
  trust_share: "critical",
};

function Row({ entry }: { entry: AuditLogEntry }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-line bg-white">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 p-3 text-left"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted" />
        )}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={CATEGORY_TONE[entry.category]}>{entry.category}</Badge>
            <span className="truncate font-black text-ink">
              {entry.summary}
            </span>
          </div>
          <div className="mt-1 text-xs text-muted">
            actor <b className="text-ink">{entry.actor}</b> · subject{" "}
            <code className="text-ink">{entry.subject}</code> ·{" "}
            {entry.occurred_at}
          </div>
        </div>
        {entry.result && <Badge>{entry.result}</Badge>}
      </button>
      {open && (
        <div className="border-t border-line bg-slate-50/40 p-3">
          <pre className="overflow-auto rounded bg-white p-3 font-mono text-[11px] text-ink">
            {JSON.stringify(entry.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function AuditLogPage() {
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>("all");
  const log = useAuditLog({
    category: category === "all" ? undefined : category,
    limit: 200,
  });

  const entries = log.data ?? [];
  const totals = entries.reduce<Record<string, number>>((acc, e) => {
    acc[e.category] = (acc[e.category] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Audit log"
        title="Workbench activity"
        description="Every posture-changing event in one stream: triage decisions, connector configuration and probes, snapshot freezes, workflow runs, and trust-share lifecycle. All entries come from append-only logs in gold/."
        actions={
          <Badge tone="info">
            <Activity className="mr-1 h-3 w-3" /> {entries.length} entries
          </Badge>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 p-3">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              className={[
                "rounded-full border px-3 py-1.5 text-xs font-black",
                category === c
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-white text-slate-600 hover:border-brand",
              ].join(" ")}
            >
              {c === "all"
                ? `all (${entries.length})`
                : `${c} (${totals[c] ?? 0})`}
            </button>
          ))}
        </div>
      </Card>

      <QueryState queries={log} label="audit log">
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>{entries.length} events</CardTitle>
          <CardDescription>
            Newest first. Click any row to expand its raw payload.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {entries.length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
              No events match this category yet. Configure a connector, triage a
              violation, or run a workflow.
            </div>
          )}
          {entries.map((entry) => (
            <Row
              key={entry.occurred_at + entry.subject + entry.category}
              entry={entry}
            />
          ))}
        </div>
      </Card>
      </QueryState>
    </div>
  );
}
