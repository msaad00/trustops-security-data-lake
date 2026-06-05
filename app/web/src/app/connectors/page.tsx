"use client";

import { useMemo, useState } from "react";
import { Plug, Search, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import { ConnectorDrawer } from "@/components/drawers/ConnectorDrawer";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

const toneForStatus = (status: string) =>
  status === "hero_path"
    ? "ready"
    : status === "supported_path"
      ? "info"
      : "attention";

const toneForState = (state: string) =>
  state === "enabled" ? "ready" : "default";

const toneForProbe = (result?: string) =>
  result === "ok"
    ? "ready"
    : result === "error"
      ? "critical"
      : result === "skipped"
        ? "attention"
        : "default";

function ConnectorRow({
  connector,
  onSelect,
}: {
  connector: ConnectorView;
  onSelect: () => void;
}) {
  const probe = connector.last_probe;
  return (
    <button
      type="button"
      onClick={onSelect}
      className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 rounded-xl border border-line bg-white p-4 text-left transition-colors hover:border-brand hover:shadow-card"
    >
      <span className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-brand to-brand-cyan font-black text-white">
        {connector.name.slice(0, 1)}
      </span>
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-2">
          <span className="truncate font-black text-ink">{connector.name}</span>
          <Badge tone={toneForState(connector.state)}>{connector.state}</Badge>
          <Badge tone={toneForStatus(connector.production_status)}>
            {connector.production_status.replace("_", " ")}
          </Badge>
        </span>
        <span className="mt-1 block truncate text-xs text-muted">
          {connector.collection_mode.replace(/_/g, " ")} ·{" "}
          {connector.access_boundary.replace(/_/g, " ")} · freshness{" "}
          {connector.freshness_slo_minutes}m SLO
        </span>
      </span>
      <span className="text-right">
        {probe ? (
          <>
            <Badge tone={toneForProbe(probe.result)}>
              last probe {probe.result}
            </Badge>
            <span className="mt-1 block text-[11px] text-muted">
              {probe.occurred_at?.slice(0, 19)}
            </span>
          </>
        ) : (
          <Badge tone="default">no probe yet</Badge>
        )}
      </span>
    </button>
  );
}

export default function ConnectorsPage() {
  const connectors = useConnectors();
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<
    "all" | "enabled" | "disabled"
  >("all");
  const [selected, setSelected] = useState<ConnectorView | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const data = connectors.data ?? [];

  const filtered = useMemo(
    () =>
      data.filter((c) => {
        if (stateFilter !== "all" && c.state !== stateFilter) return false;
        if (!query) return true;
        return JSON.stringify(c).toLowerCase().includes(query.toLowerCase());
      }),
    [data, query, stateFilter],
  );

  const totals = {
    total: data.length,
    enabled: data.filter((c) => c.state === "enabled").length,
    hero: data.filter((c) => c.production_status === "hero_path").length,
  };

  const selectedLive = selected
    ? (data.find((c) => c.connector_id === selected.connector_id) ?? selected)
    : null;

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Connectors"
        title="Connector registry"
        description="Configure read-only credentials per source, run a live probe, and watch evidence land in bronze. Credentials are hashed to a fingerprint server-side — the raw secret is never persisted to disk or sent back over the wire."
        actions={
          <>
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
              <Plug className="mr-1 inline h-3 w-3" /> {totals.enabled}/
              {totals.total} enabled
            </span>
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
              <ShieldCheck className="mr-1 inline h-3 w-3 text-emerald-600" />{" "}
              least-privilege roles only
            </span>
          </>
        }
      />

      <div className="card flex flex-wrap items-center gap-3 p-3">
        <div className="relative min-w-[260px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, category, evidence type, permission…"
            className="w-full rounded-lg border border-line bg-white py-2.5 pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
          />
        </div>
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value as typeof stateFilter)}
          className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand"
        >
          <option value="all">All states</option>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>

      <QueryState queries={connectors} label="connectors">
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>{filtered.length} connectors</CardTitle>
          <CardDescription>
            Click a row to configure credentials, run a probe, or disable the
            connector. {totals.hero} live as hero paths (Snowflake / ClickHouse
            / object storage).
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {filtered.length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
              No connectors match the current filter.
            </div>
          )}
          {filtered.map((c) => (
            <ConnectorRow
              key={c.connector_id}
              connector={c}
              onSelect={() => setSelected(c)}
            />
          ))}
        </div>
      </Card>
      </QueryState>

      <ConnectorDrawer
        connector={selectedLive}
        onClose={() => setSelected(null)}
        onToast={setToast}
      />
      {toast && (
        <div className="fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 rounded-lg bg-ink px-3.5 py-3 text-sm text-white shadow-hero">
          {toast}
        </div>
      )}
    </div>
  );
}
