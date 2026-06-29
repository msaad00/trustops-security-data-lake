"use client";

import { useMemo, useState } from "react";
import { Plug, RefreshCw, Search, ShieldCheck } from "lucide-react";
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
import { notify } from "@/lib/toast";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

const toneForStatus = (status: string) =>
  status === "primary_lake"
    ? "ready"
    : status === "supported_connector"
      ? "info"
      : "attention";

const labelForStatus = (status: string) =>
  status === "primary_lake"
    ? "Primary lake"
    : status === "supported_connector"
      ? "Supported"
      : status === "local_demo"
        ? "Local demo"
        : status.replace(/_/g, " ");

const toneForState = (state: string) =>
  state === "enabled" ? "ready" : "default";

// Sync health for an enabled connector, derived (like the backend) from the last
// successful sync vs the connector's freshness SLO: within SLO is healthy, past
// it is stale, and 3x past it is silent (likely a broken collection).
type Health = {
  label: string;
  tone: "ready" | "attention" | "critical" | "default";
};

function syncHealth(connector: ConnectorView): Health | null {
  if (connector.state !== "enabled") return null;
  const sync = connector.last_sync;
  if (!sync || sync.result !== "ok" || !sync.occurred_at) {
    return { label: "never synced", tone: "attention" };
  }
  const ageMinutes = (Date.now() - Date.parse(sync.occurred_at)) / 60000;
  const slo = connector.freshness_slo_minutes || 1440;
  if (ageMinutes <= slo) return { label: "healthy", tone: "ready" };
  if (ageMinutes <= slo * 3) return { label: "stale sync", tone: "attention" };
  return { label: "silent", tone: "critical" };
}

const toneForProbe = (result?: string) =>
  result === "ok"
    ? "ready"
    : result === "error"
      ? "critical"
      : result === "skipped"
        ? "attention"
        : "default";

function ConnectorSetupRail() {
  const steps = [
    {
      step: "01",
      label: "Connect",
      detail: "Service role, OAuth, or key pair.",
      Icon: Plug,
    },
    {
      step: "02",
      label: "Discover",
      detail: "Show only granted scope.",
      Icon: Search,
    },
    {
      step: "03",
      label: "Test",
      detail: "Validate access before enablement.",
      Icon: ShieldCheck,
    },
    {
      step: "04",
      label: "Sync",
      detail: "Refresh evidence and posture.",
      Icon: RefreshCw,
    },
  ] as const;

  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {steps.map(({ step, label, detail, Icon }) => (
        <div
          key={step}
          className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-xl border border-line bg-white p-3 shadow-card"
        >
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-panel text-brand ring-1 ring-line">
            <Icon className="h-4 w-4" />
          </span>
          <span className="min-w-0">
            <span className="flex items-center gap-2">
              <span className="text-[10px] font-black text-muted">{step}</span>
              <span className="truncate text-sm font-black text-ink">
                {label}
              </span>
            </span>
            <span className="mt-0.5 block truncate text-xs text-muted">
              {detail}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

function ConnectorRow({
  connector,
  onSelect,
}: {
  connector: ConnectorView;
  onSelect: () => void;
}) {
  const probe = connector.last_probe;
  const health = syncHealth(connector);
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
          {health && <Badge tone={health.tone}>{health.label}</Badge>}
          <Badge tone={toneForStatus(connector.production_status)}>
            {labelForStatus(connector.production_status)}
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
          <Badge tone="default">connection not tested</Badge>
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
    primary: data.filter((c) => c.production_status === "primary_lake").length,
    unhealthy: data.filter((c) => {
      const h = syncHealth(c);
      return h !== null && h.tone !== "ready";
    }).length,
  };

  const selectedLive = selected
    ? (data.find((c) => c.connector_id === selected.connector_id) ?? selected)
    : null;

  return (
    <div className="mx-auto grid w-full max-w-[1500px] min-w-0 gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Connectors"
        title="Connector registry"
        description="Connect read-only sources, discover allowed scope, test access, then sync evidence into TrustOps."
        actions={
          <>
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
              <Plug className="mr-1 inline h-3 w-3" /> {totals.enabled}/
              {totals.total} enabled
            </span>
            {totals.unhealthy > 0 && (
              <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-black text-rose-700">
                {totals.unhealthy} need attention
              </span>
            )}
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
              <ShieldCheck className="mr-1 inline h-3 w-3 text-emerald-600" />{" "}
              least privilege
            </span>
          </>
        }
      />

      <ConnectorSetupRail />

      <div className="flex min-w-0 flex-wrap items-center gap-2 rounded-xl border border-line bg-white p-2.5 shadow-card">
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
          className="min-w-[140px] rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand"
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
              Click a row to connect, test, enable, sync, or disable a source.
            </CardDescription>
          </CardHeader>
          <div className="grid gap-2 p-4 pt-0">
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
        onToast={notify.success}
      />
    </div>
  );
}
