"use client";

import { useEffect, useMemo, useState } from "react";
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
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import { ConnectorIngestionStrip } from "@/components/connectors/ConnectorIngestionStrip";
import { ConnectorIntegrationCoverage } from "@/components/connectors/ConnectorIntegrationCoverage";
import { ConnectorRegistryGapStrip } from "@/components/connectors/ConnectorRegistryGapStrip";
import { ConnectorAccountLinkingStrip } from "@/components/connectors/ConnectorAccountLinkingStrip";
import { ConnectorEcosystemStrip } from "@/components/connectors/ConnectorEcosystemStrip";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { connectorNotify } from "@/lib/connector-notify";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

const isRunnableConnector = (connector: ConnectorView) =>
  Boolean(connector.is_implemented);

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

type Health = {
  label: string;
  tone: "ready" | "attention" | "critical" | "default";
};

function syncHealth(connector: ConnectorView): Health | null {
  if (connector.state !== "enabled") return null;

  const freshness = connector.freshness_state;
  if (freshness === "fresh") return { label: "healthy", tone: "ready" };
  if (freshness === "stale") return { label: "stale sync", tone: "attention" };
  if (freshness === "never_synced") {
    const failedAttempt =
      connector.last_sync?.result === "error" &&
      connector.last_successful_sync?.result === "ok";
    if (failedAttempt) {
      return { label: "last sync failed", tone: "attention" };
    }
    return { label: "never synced", tone: "attention" };
  }

  const successAt =
    connector.last_sync_at ??
    connector.last_successful_sync?.occurred_at ??
    (connector.last_sync?.result === "ok"
      ? connector.last_sync.occurred_at
      : null);
  if (!successAt) {
    if (connector.last_sync?.result === "error") {
      return { label: "last sync failed", tone: "attention" };
    }
    return { label: "never synced", tone: "attention" };
  }
  const ageMinutes = (Date.now() - Date.parse(successAt)) / 60000;
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
    <Card className="overflow-hidden">
      <CardHeader className="p-3 pb-2">
        <CardTitle className="text-sm">Setup steps</CardTitle>
        <CardDescription className="text-xs">
          Probe-gated workflow for every connector.
        </CardDescription>
      </CardHeader>
      <div className="grid gap-2 p-3 pt-0 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map(({ step, label, detail, Icon }) => (
          <div
            key={step}
            className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-start gap-2 overflow-hidden rounded-lg border border-line bg-white p-2.5"
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-panel text-brand ring-1 ring-line">
              <Icon className="h-3.5 w-3.5" />
            </span>
            <span className="min-w-0 overflow-hidden">
              <span className="flex items-center gap-1.5">
                <span className="shrink-0 text-[10px] font-black text-muted">
                  {step}
                </span>
                <span className="truncate text-xs font-black text-ink">
                  {label}
                </span>
              </span>
              <span className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-muted">
                {detail}
              </span>
            </span>
          </div>
        ))}
      </div>
    </Card>
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
  const runnable = isRunnableConnector(connector);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`grid w-full min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 overflow-hidden rounded-xl border bg-white p-4 text-left transition-colors hover:border-brand hover:shadow-card ${
        runnable
          ? "border-line"
          : "border-dashed border-amber-200/80 bg-amber-50/30"
      }`}
    >
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg">
        <ConnectorMark
          connectorId={connector.connector_id}
          name={connector.name}
          category={connector.category}
          size="md"
        />
      </span>
      <span className="min-w-0 overflow-hidden">
        <span className="flex flex-wrap items-center gap-2">
          <span className="truncate font-black text-ink">{connector.name}</span>
          <Badge tone={toneForState(connector.state)}>{connector.state}</Badge>
          <Badge tone={runnable ? "ready" : "attention"}>
            {runnable ? "Runnable" : "Contract only"}
          </Badge>
          {health && <Badge tone={health.tone}>{health.label}</Badge>}
          <Badge tone={toneForStatus(connector.production_status)}>
            {labelForStatus(connector.production_status)}
          </Badge>
        </span>
        <span className="mt-1 block truncate text-xs text-muted">
          {connector.vendor ?? connector.category} ·{" "}
          {connector.collection_mode.replace(/_/g, " ")} ·{" "}
          {connector.access_boundary.replace(/_/g, " ")} · freshness{" "}
          {connector.freshness_slo_minutes}m SLO
        </span>
        {connector.setup_hint && (
          <span className="mt-0.5 line-clamp-1 block text-[11px] text-muted">
            {connector.setup_hint}
          </span>
        )}
      </span>
      <span className="shrink-0 text-right">
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
  const [connectId, setConnectId] = useState<string | null>(null);
  const [linkSessionId, setLinkSessionId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<
    "all" | "enabled" | "disabled"
  >("all");
  const [runnerFilter, setRunnerFilter] = useState<
    "all" | "runnable" | "contract"
  >("all");
  const [selected, setSelected] = useState<ConnectorView | null>(null);

  const data = connectors.data ?? [];

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setConnectId(params.get("connect"));
    setLinkSessionId(params.get("link_session"));
  }, []);

  useEffect(() => {
    if (!connectId || data.length === 0) return;
    const match = data.find((c) => c.connector_id === connectId);
    if (match) setSelected(match);
  }, [connectId, data]);

  const filtered = useMemo(
    () =>
      data.filter((c) => {
        if (stateFilter !== "all" && c.state !== stateFilter) return false;
        if (runnerFilter === "runnable" && !isRunnableConnector(c))
          return false;
        if (runnerFilter === "contract" && isRunnableConnector(c)) return false;
        if (!query) return true;
        return JSON.stringify(c).toLowerCase().includes(query.toLowerCase());
      }),
    [data, query, stateFilter, runnerFilter],
  );

  const totals = {
    total: data.length,
    runnable: data.filter((c) => isRunnableConnector(c)).length,
    enabled: data.filter((c) => c.state === "enabled").length,
    unhealthy: data.filter((c) => {
      const h = syncHealth(c);
      return h !== null && h.tone !== "ready";
    }).length,
  };

  const selectedLive = selected
    ? (data.find((c) => c.connector_id === selected.connector_id) ?? selected)
    : null;

  const clearDeepLinkParams = () => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (
      !url.searchParams.has("connect") &&
      !url.searchParams.has("link_session")
    ) {
      return;
    }
    url.searchParams.delete("connect");
    url.searchParams.delete("link_session");
    const next = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, "", next);
    setConnectId(null);
    setLinkSessionId(null);
  };

  return (
    <div className="mx-auto grid w-full max-w-[1600px] min-w-0 gap-2 px-3 py-2 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Connectors"
        title="Connector registry"
        description="Connect read-only sources, discover allowed scope, test access, then sync evidence."
        actions={
          <>
            <span className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-black text-slate-600">
              <Plug className="mr-1 inline h-3 w-3" /> {totals.enabled}/
              {totals.total} enabled · {totals.runnable} runnable
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

      <div className="grid gap-2 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <ConnectorAccountLinkingStrip />
        <ConnectorSetupRail />
      </div>

      <CollapsibleCard
        storageKey="connectors-overview"
        title="Registry overview"
        description="Ingestion health, coverage gaps, and ecosystem map."
        defaultOpen={false}
        contentClassName="grid gap-2 p-3 pt-0"
      >
        <ConnectorIngestionStrip />
        <ConnectorIntegrationCoverage />
        <ConnectorRegistryGapStrip onSelect={setSelected} />
        <ConnectorEcosystemStrip compact />
      </CollapsibleCard>

      <div className="flex min-w-0 flex-wrap items-center gap-2 overflow-hidden rounded-lg border border-line bg-white p-2 shadow-card">
        <div className="relative min-w-[min(100%,260px)] flex-1">
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
        <select
          value={runnerFilter}
          onChange={(e) =>
            setRunnerFilter(e.target.value as typeof runnerFilter)
          }
          className="min-w-[160px] rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand"
        >
          <option value="all">All runners</option>
          <option value="runnable">Runnable ({totals.runnable})</option>
          <option value="contract">Contract only</option>
        </select>
      </div>

      <QueryState queries={connectors} label="connectors">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{filtered.length} connectors</CardTitle>
            <CardDescription>
              Runnable connectors support probe, enable, and sync. Contract-only
              entries validate access boundaries before adapters ship.
            </CardDescription>
          </CardHeader>
          <div className="grid gap-2 p-4 pt-0">
            {filtered.length === 0 && (
              <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
                {totals.enabled === 0
                  ? "No connectors enabled yet. Use Link accounts above or pick a connector to connect, test, and sync."
                  : "No connectors match the current filter."}
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
        linkSessionId={linkSessionId}
        onClose={() => {
          setSelected(null);
          clearDeepLinkParams();
        }}
        onToast={connectorNotify}
      />
    </div>
  );
}
