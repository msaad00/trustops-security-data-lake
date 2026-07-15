"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Database, Plug, Search, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { ConnectorEcosystemStrip } from "@/components/connectors/ConnectorEcosystemStrip";
import { OnboardingGuideBanner } from "@/components/onboarding/OnboardingGuideBanner";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { connectorNotify } from "@/lib/connector-notify";
import { CONNECT_FLOW } from "@/lib/console-copy";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

const isRunnableConnector = (connector: ConnectorView) =>
  Boolean(connector.is_implemented);

const toneForState = (state: string) =>
  state === "enabled" ? "ready" : "default";

type Health = {
  label: string;
  tone: "ready" | "attention" | "critical" | "default";
};

type ViewFilter = "all" | "connected" | "setup" | "attention";
type RunnerFilter = "all" | "runnable" | "contract";
type CategoryFilter = "all" | "cloud" | "identity" | "data" | "dev" | "ops";

const VIEW_TABS: Array<{ id: ViewFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "connected", label: "Connected" },
  { id: "setup", label: "Needs setup" },
  { id: "attention", label: "Needs attention" },
];

const RUNNER_TABS: Array<{ id: RunnerFilter; label: string }> = [
  { id: "runnable", label: "Runnable" },
  { id: "all", label: "All runners" },
  { id: "contract", label: "Contract only" },
];

const CATEGORY_TABS: Array<{ id: CategoryFilter; label: string }> = [
  { id: "all", label: "All categories" },
  { id: "cloud", label: "Cloud" },
  { id: "identity", label: "Identity" },
  { id: "data", label: "Data lakes" },
  { id: "dev", label: "Dev tools" },
  { id: "ops", label: "Ops" },
];

function connectorCategory(connector: ConnectorView): CategoryFilter {
  if (connector.category === "cloud") return "cloud";
  if (connector.category === "identity") return "identity";
  if (connector.category === "developer_platform") return "dev";
  if (
    connector.category === "analytics_lake" ||
    connector.category === "warehouse" ||
    connector.category === "evidence_store" ||
    connector.category === "starter_mode"
  ) {
    return "data";
  }
  return "ops";
}

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

function needsAttention(connector: ConnectorView) {
  const health = syncHealth(connector);
  return (
    (health !== null && health.tone !== "ready") ||
    connector.last_probe?.result === "error" ||
    connector.last_sync?.result === "error"
  );
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
      label: "Read",
      detail: "Collect only the granted scope.",
      Icon: Search,
    },
    {
      step: "03",
      label: "Evaluate",
      detail: "Run controls against normalized evidence.",
      Icon: ShieldCheck,
    },
    {
      step: "04",
      label: "Prove",
      detail: "Export raw collection evidence and evaluated gold reports.",
      Icon: Database,
    },
  ] as const;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="p-3 pb-2">
        <CardTitle className="text-sm">Evidence loop</CardTitle>
        <CardDescription className="text-xs">
          One read-only path for people, agents, and scheduled jobs.
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
          {health && <Badge tone={health.tone}>{health.label}</Badge>}
        </span>
        <span className="mt-1 block truncate text-xs text-muted">
          {connector.setup_hint ??
            `Read-only ${connector.category} evidence · daily snapshot ready`}
        </span>
      </span>
      <span className="shrink-0 text-right">
        <Badge tone={probe ? toneForProbe(probe.result) : "default"}>
          {probe ? `Probe ${probe.result}` : "Connect"}
        </Badge>
      </span>
    </button>
  );
}

export default function ConnectorsPage() {
  const connectors = useConnectors();
  const [connectId, setConnectId] = useState<string | null>(null);
  const [linkSessionId, setLinkSessionId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [viewFilter, setViewFilter] = useState<ViewFilter>("all");
  const [runnerFilter, setRunnerFilter] = useState<RunnerFilter>("runnable");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [selected, setSelected] = useState<ConnectorView | null>(null);
  const [onboarding, setOnboarding] = useState(false);

  const data = connectors.data ?? [];

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setConnectId(params.get("connect"));
    setLinkSessionId(params.get("link_session"));
    setOnboarding(params.get("onboarding") === "1");
  }, []);

  useEffect(() => {
    if (!connectId || data.length === 0) return;
    const match = data.find((c) => c.connector_id === connectId);
    if (match) setSelected(match);
  }, [connectId, data]);

  useEffect(() => {
    if (!onboarding || !connectId) return;
    document.getElementById("connector-drawer-anchor")?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, [onboarding, connectId, selected]);

  const filtered = useMemo(
    () =>
      data.filter((c) => {
        if (viewFilter === "connected" && c.state !== "enabled") return false;
        if (viewFilter === "setup" && c.state === "enabled") return false;
        if (viewFilter === "attention" && !needsAttention(c)) return false;
        if (runnerFilter === "runnable" && !isRunnableConnector(c))
          return false;
        if (runnerFilter === "contract" && isRunnableConnector(c)) return false;
        if (categoryFilter !== "all" && connectorCategory(c) !== categoryFilter)
          return false;
        if (!query) return true;
        return JSON.stringify(c).toLowerCase().includes(query.toLowerCase());
      }),
    [categoryFilter, data, query, runnerFilter, viewFilter],
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
      {onboarding && (
        <OnboardingGuideBanner
          step={1}
          title="Connect a read-only source"
          detail="Pick a connector, test access, enable, then sync evidence — the same probe → enable → sync loop as MCP and CI."
        />
      )}
      <PageHeader
        eyebrow="Sources"
        title="Connect evidence"
        description="Connect a read-only source. TrustOps evaluates it and writes a daily snapshot to your security data lake."
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
          </>
        }
      />

      <ConnectorSetupRail />

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

      <div className="grid min-w-0 gap-2 overflow-hidden rounded-lg border border-line bg-white p-2 shadow-card">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <div className="relative min-w-[min(100%,260px)] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search sources..."
              className="w-full rounded-lg border border-line bg-white py-2.5 pl-10 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>
          <div
            aria-label="Connection view"
            className="flex max-w-full gap-1 overflow-x-auto rounded-lg border border-line bg-panel p-1"
            role="tablist"
          >
            {VIEW_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={viewFilter === tab.id}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-black ${
                  viewFilter === tab.id
                    ? "bg-brand text-white"
                    : "text-muted hover:bg-white"
                }`}
                onClick={() => setViewFilter(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <div
            aria-label="Runner filter"
            className="flex max-w-full gap-1 overflow-x-auto rounded-lg border border-line bg-panel p-1"
            role="tablist"
          >
            {RUNNER_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={runnerFilter === tab.id}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-black ${
                  runnerFilter === tab.id
                    ? "bg-brand text-white"
                    : "text-muted hover:bg-white"
                }`}
                onClick={() => setRunnerFilter(tab.id)}
              >
                {tab.id === "runnable"
                  ? `${tab.label} (${totals.runnable})`
                  : tab.label}
              </button>
            ))}
          </div>
          <div
            aria-label="Category filter"
            className="flex max-w-full flex-1 gap-1 overflow-x-auto rounded-lg border border-line bg-panel p-1"
            role="tablist"
          >
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={categoryFilter === tab.id}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-black ${
                  categoryFilter === tab.id
                    ? "bg-brand text-white"
                    : "text-muted hover:bg-white"
                }`}
                onClick={() => setCategoryFilter(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <QueryState queries={connectors} label="connectors">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{filtered.length} sources</CardTitle>
            <CardDescription>
              Select a source to connect, probe access, and schedule its daily
              evidence snapshot.
            </CardDescription>
          </CardHeader>
          <div className="grid gap-2 p-4 pt-0 lg:grid-cols-2">
            {filtered.length === 0 && (
              <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
                {totals.enabled === 0 ? (
                  <div className="grid gap-3">
                    <p>{CONNECT_FLOW.emptySources}</p>
                    <Button asChild size="sm" className="w-fit">
                      <Link href="/onboarding">Open setup guide</Link>
                    </Button>
                  </div>
                ) : (
                  "No connectors match the current filter."
                )}
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

      <div id="connector-drawer-anchor" />
      <ConnectorDrawer
        connector={selectedLive}
        linkSessionId={linkSessionId}
        onboarding={onboarding}
        onClose={() => {
          setSelected(null);
          clearDeepLinkParams();
        }}
        onToast={connectorNotify}
      />
    </div>
  );
}
