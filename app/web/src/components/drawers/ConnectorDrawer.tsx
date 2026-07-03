"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  KeyRound,
  ListChecks,
  Loader2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import {
  useConfigureMutation,
  useConnectorRuns,
  useDiscoverMutation,
  useProbeMutation,
  useSyncMutation,
} from "@/lib/api/hooks";
import { useAuditorMode } from "@/lib/state/auditor";
import type {
  ConfigurePayload,
  ConnectorRun,
  ConnectorView,
  ProbePayload,
} from "@/lib/api/types";
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import { CloudLinkPanel } from "@/components/connectors/CloudLinkPanel";
import {
  credentialFieldsFor,
  schedulerFieldsFor,
  scopeFieldsFor,
  type ConnectorFieldDef,
} from "@/lib/connector-forms";

interface Props {
  connector: ConnectorView | null;
  linkSessionId?: string | null;
  onClose: () => void;
  onToast: (msg: string) => void;
}

type FieldDef = ConnectorFieldDef;

interface SetupStep {
  label: string;
  detail: string;
  tone: "ready" | "attention" | "default";
}

const isRunnableConnector = (connector: ConnectorView) =>
  Boolean(connector.is_implemented);

function probeToastMessage(run: ConnectorRun, isEnabled: boolean): string {
  if (run.result === "ok") {
    const mode = run.metadata?.probe_mode;
    if (mode === "live") {
      return isEnabled
        ? "Live connection verified."
        : "Live connection verified. You can enable this connector.";
    }
    if (mode === "config_only") {
      return isEnabled
        ? "Configuration validated (probe does not call the vendor API)."
        : "Configuration validated. Enable when ready; sync performs live collection.";
    }
    return isEnabled
      ? "Probe ok."
      : "Access test passed. You can enable this connector.";
  }
  if (run.result === "skipped") {
    return `Contract validated: ${run.error ?? "probe skipped"}`;
  }
  return `Probe error: ${run.error ?? "see history"}`;
}

function validateStepDetail(
  connector: ConnectorView,
  latestProbeOk: boolean,
): string {
  if (!latestProbeOk) return "Run test";
  const mode = connector.last_probe?.metadata?.probe_mode;
  if (mode === "live") return "Live connection verified";
  if (mode === "config_only") return "Configuration validated";
  if (mode === "contract_only") return "Contract validated";
  return "Connection checked";
}

const toneForResult = (r: string | undefined) =>
  r === "ok"
    ? "ready"
    : r === "error"
      ? "critical"
      : r === "skipped"
        ? "attention"
        : "default";

const labelForStatus = (status: string) =>
  status === "primary_lake"
    ? "Primary lake"
    : status === "supported_connector"
      ? "Supported"
      : status === "local_demo"
        ? "Local demo"
        : status.replace(/_/g, " ");

const metadataObject = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};

const stringCandidates = (
  metadata: Record<string, unknown> | undefined,
  key: string,
) => {
  const candidates = metadataObject(metadata?.candidates);
  const values = candidates[key];
  if (!Array.isArray(values)) return [];
  return values
    .filter((value): value is string => typeof value === "string")
    .filter((value) => value.trim() !== "");
};

const candidateKeyForField = (field: string) =>
  field === "warehouse"
    ? "warehouses"
    : field === "database"
      ? "databases"
      : field === "schema"
        ? "schemas"
        : "views";

const isConfigured = (options: Record<string, string>) =>
  Object.values(options).some((value) => value.trim() !== "");

const requiredFirst = (fields: FieldDef[]) =>
  [...fields].sort(
    (a, b) => Number(Boolean(b.required)) - Number(Boolean(a.required)),
  );

const SNOWFLAKE_CORE_SCOPE = new Set(["warehouse", "database", "schema"]);

function formatWhen(value: string | null | undefined) {
  if (!value) return "not yet";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value.slice(0, 19);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function SnowflakeSetupHint({
  canDiscover,
  discovered,
}: {
  canDiscover: boolean;
  discovered: boolean;
}) {
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
      <div className="flex items-start gap-2">
        <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
        <div className="min-w-0">
          <div className="text-sm font-black text-blue-950">
            Connect with a read-only Snowflake service identity.
          </div>
          <div className="mt-1 text-xs leading-5 text-blue-950">
            Add account, service user, and the server-side key reference. Then
            discover what the role can see and choose from the returned
            warehouses, schemas, and views.
          </div>
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg bg-white/70 p-2">
          <Badge tone={canDiscover ? "ready" : "attention"}>
            {canDiscover ? "ready" : "needed"}
          </Badge>
          <div className="mt-1 text-xs font-black text-ink">Identity</div>
        </div>
        <div className="rounded-lg bg-white/70 p-2">
          <Badge tone={discovered ? "ready" : "default"}>
            {discovered ? "done" : "next"}
          </Badge>
          <div className="mt-1 text-xs font-black text-ink">Discovery</div>
        </div>
        <div className="rounded-lg bg-white/70 p-2">
          <Badge tone={discovered ? "attention" : "default"}>
            {discovered ? "choose" : "locked"}
          </Badge>
          <div className="mt-1 text-xs font-black text-ink">Read scope</div>
        </div>
      </div>
    </div>
  );
}

function LatestSyncProof({
  connector,
  syncing,
  onSync,
  runnable,
}: {
  connector: ConnectorView;
  syncing: boolean;
  onSync: () => void;
  runnable: boolean;
}) {
  const sync = connector.last_sync;
  const enabled = connector.state === "enabled";
  const ok = sync?.result === "ok";
  const failed = sync?.result === "error";
  const evidenceCount = sync?.evidence_count ?? 0;
  const tone = ok
    ? "ready"
    : failed
      ? "critical"
      : enabled
        ? "attention"
        : "default";
  const title = !runnable
    ? "Sync not available yet"
    : ok
      ? "Evidence sync complete"
      : failed
        ? "Latest sync failed"
        : enabled
          ? "Ready to sync evidence"
          : "Enable before syncing";
  const detail = !runnable
    ? "This connector is an access contract only. Probes validate configuration; a collection adapter is required before evidence sync."
    : ok
      ? `${evidenceCount} evidence row(s) landed and posture surfaces will refresh.`
      : failed
        ? (sync?.error ?? "Review run history for the connector error.")
        : enabled
          ? "Run sync to land evidence, refresh posture, and update trust views."
          : "Test access, enable the connector, then run the first sync.";

  return (
    <section className="rounded-xl border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-black uppercase tracking-wide text-muted">
              Latest sync
            </span>
            <Badge tone={tone}>{sync?.result ?? connector.state}</Badge>
          </div>
          <div className="mt-2 text-base font-black text-ink">{title}</div>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">
            {detail}
          </p>
        </div>
        <Button
          variant={ok ? "default" : "primary"}
          onClick={onSync}
          disabled={!enabled || syncing || !runnable}
        >
          {syncing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Sync now
        </Button>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-line bg-panel p-2">
          <div className="text-[10px] font-black uppercase tracking-wide text-muted">
            Evidence
          </div>
          <div className="mt-1 text-sm font-black text-ink">
            {sync?.evidence_count ?? "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-panel p-2">
          <div className="text-[10px] font-black uppercase tracking-wide text-muted">
            Last run
          </div>
          <div className="mt-1 text-sm font-black text-ink">
            {formatWhen(sync?.occurred_at)}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-panel p-2">
          <div className="text-[10px] font-black uppercase tracking-wide text-muted">
            Duration
          </div>
          <div className="mt-1 text-sm font-black text-ink">
            {sync?.duration_ms !== null && sync?.duration_ms !== undefined
              ? `${sync.duration_ms} ms`
              : "—"}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ConnectorDrawer({
  connector,
  linkSessionId,
  onClose,
  onToast,
}: Props) {
  const auditor = useAuditorMode();
  const configure = useConfigureMutation();
  const discover = useDiscoverMutation();
  const probe = useProbeMutation();
  const sync = useSyncMutation();
  const runs = useConnectorRuns(connector?.connector_id ?? null);
  const [creds, setCreds] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<Record<string, string>>({});
  const [accessValidated, setAccessValidated] = useState(false);
  const [discoveryRun, setDiscoveryRun] = useState<ConnectorRun | null>(null);

  useEffect(() => {
    setCreds({});
    setAccessValidated(false);
    setDiscoveryRun(null);
    const configured = connector?.configured_options ?? {};
    setOptions(
      Object.fromEntries(
        Object.entries(configured)
          .filter(([key]) => key !== "raw")
          .map(([key, value]) => [key, String(value ?? "")]),
      ),
    );
  }, [connector?.connector_id, connector?.configured_options]);

  useEffect(() => {
    if (!connector?.connector_id || !runs.data?.length) return;
    const latestDiscover = runs.data.find(
      (run) =>
        run.kind === "discover" &&
        run.result === "ok" &&
        run.metadata &&
        typeof run.metadata === "object" &&
        Object.keys(run.metadata).length > 0,
    );
    if (latestDiscover) {
      setDiscoveryRun(latestDiscover);
    }
  }, [connector?.connector_id, runs.data]);

  if (!connector) {
    return (
      <Drawer open={false} onOpenChange={() => undefined} title="Connector">
        <></>
      </Drawer>
    );
  }

  const credentialFields = credentialFieldsFor(
    connector.connector_id,
    connector.credential_type,
  );
  const scopeFields = scopeFieldsFor(connector.connector_id);
  const schedulerFields = schedulerFieldsFor(isRunnableConnector(connector));
  const isSnowflake = connector.connector_id === "snowflake-evidence-lake";
  const usesDiscoveredReadScope =
    connector.connector_id === "clickhouse-telemetry-lake" || isSnowflake;
  const isEnabled = connector.state === "enabled";
  const isRunnable = isRunnableConnector(connector);
  const missingCredentials = credentialFields
    .filter((field) => field.required && !(creds[field.name] ?? "").trim())
    .map((field) => field.label);
  const missingScope = scopeFields
    .filter((field) => field.required && !(options[field.name] ?? "").trim())
    .map((field) => field.label);
  const missingRequired = [...missingCredentials, ...missingScope];
  const canEnable = missingRequired.length === 0 && isRunnable;
  const stagedCredentials = Object.fromEntries(
    Object.entries(creds).filter(([, value]) => value.trim() !== ""),
  );
  const stagedOptions = Object.fromEntries(
    Object.entries(options).filter(([, value]) => value.trim() !== ""),
  );
  const canTestAccess = isEnabled || missingRequired.length === 0;
  const canDiscover = isEnabled || missingCredentials.length === 0;
  const discoveryMetadata = discoveryRun?.metadata;
  const showSnowflakeScopeFields =
    !isSnowflake || isEnabled || Boolean(discoveryRun) || isConfigured(options);
  const actionableMissingRequired =
    isSnowflake && !showSnowflakeScopeFields
      ? [...missingCredentials, "Discovered read scope"]
      : missingRequired;
  const coreScopeFields = isSnowflake
    ? scopeFields.filter((field) => SNOWFLAKE_CORE_SCOPE.has(field.name))
    : scopeFields;
  const advancedScopeFields = isSnowflake
    ? scopeFields.filter((field) => !SNOWFLAKE_CORE_SCOPE.has(field.name))
    : [];
  const liveDiscoveryError =
    typeof discoveryMetadata?.live_discovery_error === "string"
      ? discoveryMetadata.live_discovery_error
      : null;
  const latestError = (runs.data ?? []).find((run) => run.error);
  const latestProbeOk =
    connector.last_probe?.result === "ok" ||
    connector.last_probe?.result === "skipped" ||
    accessValidated;
  const latestSyncOk =
    connector.last_successful_sync?.result === "ok" ||
    connector.last_sync?.result === "ok";
  const scopeReady = scopeFields.length === 0 || missingScope.length === 0;
  const needsDiscovery =
    usesDiscoveredReadScope &&
    !isEnabled &&
    !discoveryRun &&
    !isConfigured(options);
  const setupSteps: SetupStep[] = [
    {
      label: "Access",
      detail:
        missingCredentials.length === 0
          ? "Identity staged"
          : `${missingCredentials.length} field(s) needed`,
      tone: missingCredentials.length === 0 ? "ready" : "attention",
    },
    {
      label: "Scope",
      detail: needsDiscovery
        ? "Discover available objects"
        : scopeReady
          ? "Read scope selected"
          : `${missingScope.length} field(s) needed`,
      tone: needsDiscovery || !scopeReady ? "attention" : "ready",
    },
    {
      label: "Validate",
      detail: validateStepDetail(connector, latestProbeOk),
      tone: latestProbeOk ? "ready" : "default",
    },
    {
      label: "Sync",
      detail: !isRunnable
        ? "Contract only"
        : latestSyncOk
          ? "Evidence landed"
          : isEnabled
            ? "Ready to sync"
            : "Enable first",
      tone: !isRunnable
        ? "default"
        : latestSyncOk
          ? "ready"
          : isEnabled
            ? "attention"
            : "default",
    },
  ];
  const enable = async () => {
    if (!isRunnable) {
      onToast(
        "This connector is contract-only — sync adapter not shipped yet. Use Test connection to validate access.",
      );
      return;
    }
    if (!canEnable) {
      onToast(
        `Required before enabling: ${actionableMissingRequired.join(", ")}.`,
      );
      return;
    }
    if (!isEnabled && !accessValidated) {
      onToast("Test connection before enabling this connector.");
      return;
    }
    const payload: ConfigurePayload = {
      state: "enabled",
      actor: "console",
      credentials: stagedCredentials,
      options: stagedOptions,
    };
    try {
      await configure.mutateAsync({ id: connector.connector_id, payload });
      onToast(`${connector.name} enabled — credentials redacted server-side.`);
    } catch (err) {
      onToast(`Configure failed: ${(err as Error).message}`);
    }
  };

  const disable = async () => {
    try {
      await configure.mutateAsync({
        id: connector.connector_id,
        payload: { state: "disabled", actor: "console" },
      });
      onToast(`${connector.name} disabled.`);
    } catch (err) {
      onToast(`Disable failed: ${(err as Error).message}`);
    }
  };

  const runProbe = async () => {
    try {
      const payload: ProbePayload = { actor: "console" };
      if (!isEnabled) {
        payload.credentials = stagedCredentials;
        payload.options = stagedOptions;
      }
      const { run } = await probe.mutateAsync({
        id: connector.connector_id,
        payload,
      });
      const validated = run.result === "ok";
      setAccessValidated(validated);
      onToast(probeToastMessage(run, isEnabled));
    } catch (err) {
      setAccessValidated(false);
      onToast(`Probe failed: ${(err as Error).message}`);
    }
  };

  const runSync = async () => {
    try {
      const result = await sync.mutateAsync({
        id: connector.connector_id,
        payload: { actor: "console" },
      });
      onToast(
        result.result === "ok"
          ? `Sync complete: ${result.evidence_count ?? 0} evidence item(s) landed.`
          : "Sync finished with errors; see history.",
      );
    } catch (err) {
      onToast(`Sync failed: ${(err as Error).message}`);
    }
  };

  const runDiscovery = async () => {
    try {
      const payload: ProbePayload = { actor: "console" };
      if (!isEnabled) {
        payload.credentials = stagedCredentials;
        payload.options = stagedOptions;
      }
      const { run } = await discover.mutateAsync({
        id: connector.connector_id,
        payload,
      });
      setDiscoveryRun(run);
      if (
        run.result === "ok" &&
        run.metadata?.recommended_options &&
        typeof run.metadata.recommended_options === "object"
      ) {
        const recommended = Object.entries(
          run.metadata.recommended_options as Record<string, unknown>,
        ).reduce<Record<string, string>>((acc, [key, value]) => {
          if (typeof value === "string" && value.trim() !== "") {
            acc[key] = value;
          }
          return acc;
        }, {});
        if (Object.keys(recommended).length > 0) {
          setOptions((current) => ({ ...current, ...recommended }));
        }
      }
      onToast(
        run.result === "ok"
          ? "Scope discovery complete."
          : `Discovery error: ${run.error ?? "see history"}`,
      );
    } catch (err) {
      setDiscoveryRun(null);
      onToast(`Discovery failed: ${(err as Error).message}`);
    }
  };

  return (
    <Drawer
      open={true}
      onOpenChange={(o) => !o && onClose()}
      title={connector.name}
      description={`${connector.category} · ${connector.collection_mode.replace("_", " ")}`}
      width="lg"
      footer={
        !auditor && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted">
              Access secret hashed to a fingerprint server-side; raw value never
              persisted.
            </span>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="default"
                onClick={runDiscovery}
                disabled={discover.isPending || !canDiscover}
              >
                {discover.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}{" "}
                {isSnowflake ? "Discover objects" : "Discover scope"}
              </Button>
              <Button
                variant="default"
                onClick={runProbe}
                disabled={probe.isPending || !canTestAccess}
              >
                {probe.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}{" "}
                Test connection
              </Button>
              {isEnabled ? (
                <Button
                  variant="primary"
                  onClick={runSync}
                  disabled={sync.isPending || !isRunnable}
                >
                  {sync.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}{" "}
                  Sync now
                </Button>
              ) : null}
              {isEnabled ? (
                <Button
                  variant="default"
                  onClick={disable}
                  disabled={configure.isPending}
                >
                  <PauseCircle className="h-4 w-4" /> Disable
                </Button>
              ) : (
                <Button
                  variant="primary"
                  onClick={enable}
                  disabled={
                    configure.isPending ||
                    !canEnable ||
                    (!isEnabled && !accessValidated)
                  }
                >
                  {configure.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <PlayCircle className="h-4 w-4" />
                  )}{" "}
                  Enable connector
                </Button>
              )}
            </div>
          </div>
        )
      }
    >
      <div className="grid gap-5 text-sm">
        <section className="rounded-xl border border-line bg-white p-4">
          <ConnectorMark
            connectorId={connector.connector_id}
            name={connector.name}
            category={connector.category}
            size="lg"
            showVendor
          />
          {(connector.description || connector.setup_hint) && (
            <div className="mt-3 space-y-2 text-xs leading-5 text-muted">
              {connector.description && (
                <p className="text-sm text-ink">{connector.description}</p>
              )}
              {connector.setup_hint && (
                <p>
                  <span className="font-black uppercase tracking-wide text-muted">
                    Connection:{" "}
                  </span>
                  {connector.setup_hint}
                </p>
              )}
              <p>
                <span className="font-black uppercase tracking-wide text-muted">
                  Ingestion route:{" "}
                </span>
                {connector.default_route} ·{" "}
                {connector.collection_mode.replace(/_/g, " ")}
              </p>
            </div>
          )}
        </section>

        {!isRunnable && (
          <section className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <div className="font-black uppercase tracking-wide">
                  Access contract only
                </div>
                <p className="mt-1">
                  Probes and discovery validate read-only scope. Evidence sync
                  and enablement require a collection adapter — tracked in the
                  connector catalog roadmap.
                </p>
              </div>
            </div>
          </section>
        )}

        <section className="rounded-xl border border-line bg-slate-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={isEnabled ? "ready" : "default"}>
              {connector.state}
            </Badge>
            <Badge tone={isRunnable ? "ready" : "attention"}>
              {isRunnable ? "Runnable" : "Contract only"}
            </Badge>
            <Badge>{labelForStatus(connector.production_status)}</Badge>
            <Badge tone="info">
              {connector.access_boundary.replace("_", " ")}
            </Badge>
            <Badge>freshness {connector.freshness_slo_minutes}m</Badge>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            {setupSteps.map((step, index) => (
              <div
                key={step.label}
                className="rounded-lg border border-line bg-white p-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-black uppercase tracking-wide text-muted">
                    {index + 1}. {step.label}
                  </span>
                  <Badge tone={step.tone}>
                    {step.tone === "ready" ? "done" : "next"}
                  </Badge>
                </div>
                <div className="mt-1 truncate text-xs font-bold text-ink">
                  {step.detail}
                </div>
              </div>
            ))}
          </div>
        </section>

        <details className="rounded-xl border border-line p-3">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-black uppercase tracking-wide text-muted">
            <ListChecks className="h-3.5 w-3.5" /> Connector contract
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <div className="text-xs font-black uppercase tracking-wide text-muted">
                Permissions
              </div>
              <ul className="mt-2 space-y-1 text-xs">
                {connector.minimum_permissions.map((perm) => (
                  <li key={perm} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                    <code className="text-ink">{perm}</code>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-black uppercase tracking-wide text-muted">
                Evidence
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {connector.evidence_types.map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            </div>
          </div>
        </details>

        {!auditor && connector && (
          <CloudLinkPanel
            connector={connector}
            linkSessionId={linkSessionId}
            onLinked={(linked) => {
              setAccessValidated(false);
              setCreds((current) => ({ ...current, ...linked }));
            }}
            onToast={onToast}
          />
        )}

        {!auditor && (
          <section className="rounded-xl border border-line p-3">
            <div className="text-xs font-black uppercase tracking-wide text-muted">
              Scoped access · {connector.credential_type.replace(/_/g, " ")}
            </div>
            {connector.connector_id === "snowflake-evidence-lake" && (
              <div className="mt-2">
                <SnowflakeSetupHint
                  canDiscover={canDiscover}
                  discovered={showSnowflakeScopeFields}
                />
              </div>
            )}
            <div className="mt-2 grid gap-2">
              {requiredFirst(credentialFields)
                .filter((field) => field.required)
                .map((field) => (
                  <label
                    key={field.name}
                    className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                  >
                    {field.label}
                    <input
                      type={field.secret ? "password" : "text"}
                      value={creds[field.name] ?? ""}
                      onChange={(e) => {
                        setAccessValidated(false);
                        setCreds((c) => ({
                          ...c,
                          [field.name]: e.target.value,
                        }));
                      }}
                      className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                      placeholder={field.placeholder}
                    />
                    {field.hint && (
                      <span className="font-normal normal-case tracking-normal text-muted">
                        {field.hint}
                      </span>
                    )}
                  </label>
                ))}
              {credentialFields.some((field) => !field.required) && (
                <details className="rounded-lg border border-line bg-slate-50 p-3">
                  <summary className="cursor-pointer list-none text-xs font-black uppercase tracking-wide text-muted">
                    Advanced identity settings
                  </summary>
                  <div className="mt-3 grid gap-2">
                    {requiredFirst(credentialFields)
                      .filter((field) => !field.required)
                      .map((field) => (
                        <label
                          key={field.name}
                          className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                        >
                          {field.label}
                          <input
                            type={field.secret ? "password" : "text"}
                            value={creds[field.name] ?? ""}
                            onChange={(e) => {
                              setAccessValidated(false);
                              setCreds((c) => ({
                                ...c,
                                [field.name]: e.target.value,
                              }));
                            }}
                            className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                            placeholder={field.placeholder}
                          />
                        </label>
                      ))}
                  </div>
                </details>
              )}
              {credentialFields.length === 0 && (
                <div className="rounded-lg border border-line bg-slate-50 p-3 text-xs font-semibold text-muted">
                  This connector uses ambient platform credentials.
                </div>
              )}
              {isSnowflake && !showSnowflakeScopeFields && (
                <div className="mt-2 rounded-lg border border-line bg-slate-50 p-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Read scope
                  </div>
                  <div className="mt-1 text-xs font-semibold text-muted">
                    Click <b>Discover objects</b> after entering the service
                    identity. TrustOps will show only Snowflake objects visible
                    to that role, then prefill the recommended read scope.
                  </div>
                </div>
              )}
              {scopeFields.length > 0 && showSnowflakeScopeFields && (
                <div className="mt-2 border-t border-line pt-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs font-black uppercase tracking-wide text-muted">
                        Read scope
                      </div>
                      {isSnowflake && (
                        <div className="mt-1 text-xs font-semibold text-muted">
                          Choose the warehouse, database, and schema this role
                          can read. View names are auto-filled from discovery.
                        </div>
                      )}
                    </div>
                    {isSnowflake && (
                      <Badge
                        tone={missingScope.length === 0 ? "ready" : "attention"}
                      >
                        {missingScope.length === 0
                          ? "scope ready"
                          : `${missingScope.length} missing`}
                      </Badge>
                    )}
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {coreScopeFields.map((field) => {
                      const candidates = stringCandidates(
                        discoveryMetadata,
                        candidateKeyForField(field.name),
                      );
                      const currentValue = options[field.name] ?? "";
                      const selectValues = currentValue
                        ? Array.from(new Set([currentValue, ...candidates]))
                        : candidates;
                      const onScopeChange = (value: string) => {
                        setAccessValidated(false);
                        setOptions((current) => {
                          const next = { ...current, [field.name]: value };
                          if (isSnowflake && field.name === "database") {
                            delete next.schema;
                            delete next.audit_events;
                            delete next.control_posture;
                            delete next.asset_risk;
                            delete next.evidence_bundles;
                          }
                          if (isSnowflake && field.name === "schema") {
                            delete next.audit_events;
                            delete next.control_posture;
                            delete next.asset_risk;
                            delete next.evidence_bundles;
                          }
                          return next;
                        });
                      };
                      return (
                        <label
                          key={field.name}
                          className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                        >
                          {field.label}
                          {isSnowflake && selectValues.length > 0 ? (
                            <select
                              value={currentValue}
                              onChange={(e) => onScopeChange(e.target.value)}
                              className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                            >
                              <option value="">
                                Select {field.label.toLowerCase()}
                              </option>
                              {selectValues.map((value) => (
                                <option key={value} value={value}>
                                  {value}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              value={currentValue}
                              onChange={(e) => onScopeChange(e.target.value)}
                              placeholder={field.placeholder}
                              className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                            />
                          )}
                        </label>
                      );
                    })}
                  </div>
                  {advancedScopeFields.length > 0 && (
                    <details className="mt-3 rounded-lg border border-line bg-slate-50 p-3">
                      <summary className="cursor-pointer list-none text-xs font-black uppercase tracking-wide text-muted">
                        Advanced view mapping
                      </summary>
                      <div className="mt-2 text-xs leading-5 text-muted">
                        Defaults work for the TrustOps Snowflake schema. Change
                        these only when your evidence lake uses custom view
                        names.
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {advancedScopeFields.map((field) => {
                          const candidates = stringCandidates(
                            discoveryMetadata,
                            candidateKeyForField(field.name),
                          );
                          const currentValue = options[field.name] ?? "";
                          const selectValues = currentValue
                            ? Array.from(new Set([currentValue, ...candidates]))
                            : candidates;
                          const onScopeChange = (value: string) => {
                            setAccessValidated(false);
                            setOptions((current) => ({
                              ...current,
                              [field.name]: value,
                            }));
                          };
                          return (
                            <label
                              key={field.name}
                              className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                            >
                              {field.label}
                              {selectValues.length > 0 ? (
                                <select
                                  value={currentValue}
                                  onChange={(e) =>
                                    onScopeChange(e.target.value)
                                  }
                                  className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                                >
                                  <option value="">
                                    Select {field.label.toLowerCase()}
                                  </option>
                                  {selectValues.map((value) => (
                                    <option key={value} value={value}>
                                      {value}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <input
                                  value={currentValue}
                                  onChange={(e) =>
                                    onScopeChange(e.target.value)
                                  }
                                  placeholder={field.placeholder}
                                  className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                                />
                              )}
                            </label>
                          );
                        })}
                      </div>
                    </details>
                  )}
                </div>
              )}
              {schedulerFields.length > 0 && (
                <div className="mt-2 border-t border-line pt-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Scheduled sync
                  </div>
                  <div className="mt-1 text-xs font-semibold text-muted">
                    Optional interval for the in-process scheduler. Leave empty
                    to sync manually from the console or API.
                  </div>
                  <div className="mt-2 grid gap-2">
                    {schedulerFields.map((field) => (
                      <label
                        key={field.name}
                        className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                      >
                        {field.label}
                        <input
                          value={options[field.name] ?? ""}
                          onChange={(e) =>
                            setOptions((current) => ({
                              ...current,
                              [field.name]: e.target.value,
                            }))
                          }
                          placeholder={field.placeholder}
                          className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                        />
                        {field.hint && (
                          <span className="font-normal normal-case tracking-normal text-muted">
                            {field.hint}
                          </span>
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {usesDiscoveredReadScope && !isSnowflake && (
                <div className="mt-2 rounded-lg border border-line bg-slate-50 p-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Read scope
                  </div>
                  <div className="mt-1 text-xs font-semibold text-muted">
                    Discover only the databases and tables visible to the scoped
                    read identity before this connector is enabled.
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge tone="info">discovered tables</Badge>
                    <Badge tone="info">least privilege</Badge>
                    <Badge tone="info">no typed scope</Badge>
                  </div>
                  {!isEnabled && (
                    <div className="mt-2 text-xs text-muted">
                      Enter the host and credential reference, test access, then
                      enable. Raw secrets are not persisted.
                    </div>
                  )}
                </div>
              )}
            </div>
            {!canEnable && !isEnabled && (
              <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                Required before enabling: {actionableMissingRequired.join(", ")}
                .
              </div>
            )}
            {canEnable && !isEnabled && !accessValidated && (
              <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900">
                Test connection before enabling. Snowflake runs a live probe;
                other runnable connectors validate configuration only until
                sync.
              </div>
            )}
            {discoveryRun?.metadata && (
              <div className="mt-2 rounded-lg border border-line bg-slate-50 p-3 text-xs">
                <div className="font-black uppercase tracking-wide text-muted">
                  Discovered scope
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Array.isArray(discoveryRun.metadata.selectors) &&
                    discoveryRun.metadata.selectors
                      .filter((item): item is Record<string, unknown> =>
                        Boolean(item && typeof item === "object"),
                      )
                      .slice(0, 8)
                      .map((item, index) => (
                        <Badge
                          key={`${String(item.kind)}-${String(item.name)}-${index}`}
                          tone={item.selected ? "ready" : "info"}
                        >
                          {String(item.kind)}: {String(item.name)}
                        </Badge>
                      ))}
                </div>
                <div className="mt-2 text-muted">
                  {liveDiscoveryError
                    ? `Live metadata was unavailable (${liveDiscoveryError}); defaults remain editable.`
                    : "Select the discovered scope, then test connection before enabling."}
                </div>
              </div>
            )}
            {canEnable && !isEnabled && accessValidated && (
              <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900">
                Access checked. Enable writes the redacted configuration event.
              </div>
            )}
            {latestError?.error && (
              <div className="mt-2 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <div>
                  <b>Latest run needs attention:</b> {latestError.error}
                </div>
              </div>
            )}
            {isEnabled && connector.credential_fingerprint ? (
              <div className="mt-2 text-xs text-muted">
                Last fingerprint:{" "}
                <code className="text-ink">
                  {connector.credential_fingerprint}
                </code>{" "}
                · configured {connector.configured_at ?? "—"}
              </div>
            ) : (
              <div className="mt-2 text-xs text-muted">
                No active credential configured.
              </div>
            )}
          </section>
        )}

        <LatestSyncProof
          connector={connector}
          syncing={sync.isPending}
          onSync={runSync}
          runnable={isRunnable}
        />

        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-wide text-muted">
            <ShieldCheck className="h-3 w-3" /> Run history ·{" "}
            {runs.data?.length ?? 0} events
          </div>
          <div className="grid gap-2">
            {(runs.data ?? []).slice(0, 8).map((r) => (
              <div
                key={r.occurred_at + r.kind}
                className="rounded-lg border border-line p-3 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    <Badge tone={toneForResult(r.result)}>{r.result}</Badge>{" "}
                    <Badge>{r.kind}</Badge>
                  </span>
                  <span className="text-muted">{r.occurred_at}</span>
                </div>
                <div className="mt-1 text-muted">
                  actor <b className="text-ink">{r.actor}</b>
                  {r.duration_ms !== null && <> · {r.duration_ms} ms</>}
                  {r.evidence_count !== null && (
                    <>
                      {" "}
                      ·{" "}
                      {r.kind === "sync"
                        ? `${r.evidence_count} evidence row(s)`
                        : `${r.evidence_count} object(s)`}
                    </>
                  )}
                </div>
                {r.error && <div className="mt-1 text-rose-700">{r.error}</div>}
              </div>
            ))}
            {(runs.data ?? []).length === 0 && (
              <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
                No probes or syncs recorded yet. Click <b>Test connection</b> to
                run one.
              </div>
            )}
          </div>
        </section>
      </div>
    </Drawer>
  );
}
