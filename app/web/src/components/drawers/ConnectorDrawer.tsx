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

interface Props {
  connector: ConnectorView | null;
  onClose: () => void;
  onToast: (msg: string) => void;
}

interface FieldDef {
  name: string;
  label: string;
  placeholder: string;
  secret?: boolean;
  required?: boolean;
}

interface SetupStep {
  label: string;
  detail: string;
  tone: "ready" | "attention" | "default";
}

const CREDENTIAL_FIELDS: Record<string, FieldDef[]> = {
  "clickhouse-telemetry-lake": [
    {
      name: "host",
      label: "ClickHouse host",
      placeholder: "https://cluster.example.clickhouse.cloud:8443",
      required: true,
    },
    {
      name: "user",
      label: "Read-only user",
      placeholder: "trustops_reader",
    },
    {
      name: "credential_ref",
      label: "Scoped credential reference",
      placeholder: "TRUSTOPS_CLICKHOUSE_TOKEN",
      required: true,
    },
  ],
  "snowflake-evidence-lake": [
    {
      name: "account",
      label: "Snowflake account",
      placeholder: "MJFAYEE-YS65534",
      required: true,
    },
    {
      name: "user",
      label: "Service user",
      placeholder: "TRUSTOPS_INGEST_SVC",
      required: true,
    },
    {
      name: "private_key_ref",
      label: "Credential reference",
      placeholder: "SNOWFLAKE_PRIVATE_KEY_FILE",
      required: true,
    },
    {
      name: "role",
      label: "Read-only role (optional)",
      placeholder: "TRUSTOPS_READER",
    },
    {
      name: "private_key_file_pwd_ref",
      label: "Key password env var (optional)",
      placeholder: "SNOWFLAKE_PRIVATE_KEY_FILE_PWD",
    },
  ],
  "aws-posture": [
    {
      name: "account_id",
      label: "AWS account ID",
      placeholder: "123456789012",
      required: true,
    },
    {
      name: "role_arn",
      label: "Read-only role ARN (optional)",
      placeholder: "arn:aws:iam::123456789012:role/TrustOpsPostureReadOnlyRole",
    },
    {
      name: "external_id",
      label: "External ID (optional, with role ARN)",
      placeholder: "shared secret used in the role trust policy",
    },
  ],
  "azure-posture": [
    {
      name: "subscription_id",
      label: "Azure subscription ID",
      placeholder: "00000000-0000-0000-0000-000000000000",
      required: true,
    },
  ],
  "gcp-posture": [
    {
      name: "project_id",
      label: "GCP project ID",
      placeholder: "my-project-123456",
      required: true,
    },
  ],
};

const SCOPE_FIELDS: Record<string, FieldDef[]> = {
  "aws-posture": [
    {
      name: "region",
      label: "Region",
      placeholder: "us-east-1",
    },
  ],
  "snowflake-evidence-lake": [
    {
      name: "warehouse",
      label: "Warehouse",
      placeholder: "TRUSTOPS_READ_WH",
      required: true,
    },
    {
      name: "database",
      label: "Database",
      placeholder: "TRUSTOPS_SECURITY_LAKE",
      required: true,
    },
    {
      name: "schema",
      label: "Schema",
      placeholder: "EVIDENCE",
      required: true,
    },
    {
      name: "audit_events",
      label: "Audit events view",
      placeholder: "TRUSTOPS_AUDIT_EVENTS",
      required: true,
    },
    {
      name: "control_posture",
      label: "Control posture view",
      placeholder: "TRUSTOPS_CONTROL_POSTURE",
      required: true,
    },
    {
      name: "asset_risk",
      label: "Asset risk view",
      placeholder: "TRUSTOPS_ASSET_RISK",
      required: true,
    },
    {
      name: "evidence_bundles",
      label: "Evidence bundles view",
      placeholder: "TRUSTOPS_EVIDENCE_BUNDLES",
      required: true,
    },
  ],
};

const fallbackFieldsFor = (credentialType: string): FieldDef[] => {
  if (credentialType.includes("oauth"))
    return [
      {
        name: "client_id",
        label: "Client ID",
        placeholder: "client id",
        required: true,
      },
      {
        name: "client_secret_ref",
        label: "Client secret reference",
        placeholder: "TRUSTOPS_CLIENT_SECRET",
        required: true,
      },
      {
        name: "refresh_token_ref",
        label: "Refresh token reference",
        placeholder: "TRUSTOPS_REFRESH_TOKEN",
        required: true,
      },
    ];
  if (credentialType.includes("key_pair"))
    return [
      {
        name: "account",
        label: "Account",
        placeholder: "account",
        required: true,
      },
      {
        name: "user",
        label: "User",
        placeholder: "read-only user",
        required: true,
      },
      {
        name: "private_key",
        label: "Private key reference",
        placeholder: "TRUSTOPS_PRIVATE_KEY",
        secret: true,
        required: true,
      },
    ];
  if (credentialType.includes("token"))
    return [
      {
        name: "credential_ref",
        label: "Scoped credential reference",
        placeholder: "TRUSTOPS_SOURCE_TOKEN",
        required: true,
      },
    ];
  if (credentialType.includes("scoped_user"))
    return [
      {
        name: "host",
        label: "Host",
        placeholder: "https://...",
        required: true,
      },
      {
        name: "user",
        label: "Read-only user",
        placeholder: "read-only user",
      },
      {
        name: "token",
        label: "Scoped credential reference",
        placeholder: "TRUSTOPS_SOURCE_TOKEN",
        secret: true,
        required: true,
      },
    ];
  if (credentialType.includes("local"))
    return [
      {
        name: "lake_path",
        label: "Lake path",
        placeholder: "/path/to/lake",
        required: true,
      },
    ];
  return [
    {
      name: "api_key",
      label: "API key reference",
      placeholder: "TRUSTOPS_SOURCE_API_KEY",
      secret: true,
      required: true,
    },
  ];
};

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

export function ConnectorDrawer({ connector, onClose, onToast }: Props) {
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

  if (!connector) {
    return (
      <Drawer open={false} onOpenChange={() => undefined} title="Connector">
        <></>
      </Drawer>
    );
  }

  const credentialFields =
    CREDENTIAL_FIELDS[connector.connector_id] ??
    fallbackFieldsFor(connector.credential_type);
  const scopeFields = SCOPE_FIELDS[connector.connector_id] ?? [];
  const isSnowflake = connector.connector_id === "snowflake-evidence-lake";
  const usesDiscoveredReadScope =
    connector.connector_id === "clickhouse-telemetry-lake" || isSnowflake;
  const isEnabled = connector.state === "enabled";
  const missingCredentials = credentialFields
    .filter((field) => field.required && !(creds[field.name] ?? "").trim())
    .map((field) => field.label);
  const missingScope = scopeFields
    .filter((field) => field.required && !(options[field.name] ?? "").trim())
    .map((field) => field.label);
  const missingRequired = [...missingCredentials, ...missingScope];
  const canEnable = missingRequired.length === 0;
  const stagedCredentials = Object.fromEntries(
    Object.entries(creds).filter(([, value]) => value.trim() !== ""),
  );
  const stagedOptions = Object.fromEntries(
    Object.entries(options).filter(([, value]) => value.trim() !== ""),
  );
  const canTestAccess = isEnabled || canEnable;
  const canDiscover = isEnabled || missingCredentials.length === 0;
  const discoveryMetadata = discoveryRun?.metadata;
  const showSnowflakeScopeFields =
    !isSnowflake || isEnabled || Boolean(discoveryRun) || isConfigured(options);
  const liveDiscoveryError =
    typeof discoveryMetadata?.live_discovery_error === "string"
      ? discoveryMetadata.live_discovery_error
      : null;
  const latestError = (runs.data ?? []).find((run) => run.error);
  const latestProbeOk =
    connector.last_probe?.result === "ok" || accessValidated || isEnabled;
  const latestSyncOk = connector.last_sync?.result === "ok";
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
      detail: latestProbeOk ? "Connection checked" : "Run test",
      tone: latestProbeOk ? "ready" : "default",
    },
    {
      label: "Sync",
      detail: latestSyncOk
        ? "Evidence landed"
        : isEnabled
          ? "Ready to sync"
          : "Enable first",
      tone: latestSyncOk ? "ready" : isEnabled ? "attention" : "default",
    },
  ];
  const enable = async () => {
    if (!canEnable) {
      onToast(`Required before enabling: ${missingRequired.join(", ")}.`);
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
      onToast(
        run.result === "ok"
          ? isEnabled
            ? "Probe ok."
            : "Access test passed. You can enable this connector."
          : run.result === "skipped"
            ? `No live probe yet: ${run.error ?? "probe skipped"}`
            : `Probe error: ${run.error ?? "see history"}`,
      );
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
                Discover scope
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
                  disabled={sync.isPending}
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
        <section className="rounded-xl border border-line bg-slate-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={isEnabled ? "ready" : "default"}>
              {connector.state}
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

        {!auditor && (
          <section className="rounded-xl border border-line p-3">
            <div className="text-xs font-black uppercase tracking-wide text-muted">
              Scoped access · {connector.credential_type.replace(/_/g, " ")}
            </div>
            {connector.connector_id === "snowflake-evidence-lake" && (
              <div className="mt-2 flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-950">
                <KeyRound className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <div>
                  Enter the account, service user, and server-side credential
                  reference. Discovery signs in with that role and returns only
                  warehouses, databases, schemas, and views Snowflake grants to
                  it. Raw keys and OAuth tokens never enter the browser.
                </div>
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
                    Click <b>Discover scope</b> after entering the service
                    identity. TrustOps will replace typed object names with
                    selectable Snowflake objects visible to that read-only role.
                  </div>
                </div>
              )}
              {scopeFields.length > 0 && showSnowflakeScopeFields && (
                <div className="mt-2 border-t border-line pt-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Read scope
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {scopeFields.map((field) => {
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
                </div>
              )}
              {usesDiscoveredReadScope && (
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
                Required before enabling: {missingRequired.join(", ")}.
              </div>
            )}
            {canEnable && !isEnabled && !accessValidated && (
              <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900">
                Test connection before enabling. The probe validates required
                fields without persisting raw credentials.
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
                    <> · {r.evidence_count} evidence types</>
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
