"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  PauseCircle,
  PlayCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import {
  useConfigureMutation,
  useConnectorRuns,
  useProbeMutation,
} from "@/lib/api/hooks";
import { useAuditorMode } from "@/lib/state/auditor";
import type {
  ConfigurePayload,
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
      name: "token",
      label: "Scoped credential reference",
      placeholder: "TRUSTOPS_CLICKHOUSE_TOKEN",
      secret: true,
      required: true,
    },
  ],
  "snowflake-evidence-lake": [
    {
      name: "account",
      label: "Snowflake account",
      placeholder: "org-account",
      required: true,
    },
    {
      name: "user",
      label: "Read-only user",
      placeholder: "TRUSTOPS_READER",
      required: true,
    },
    {
      name: "oauth_token",
      label: "OAuth token reference",
      placeholder: "SNOWFLAKE_OAUTH_TOKEN",
      secret: true,
      required: true,
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
      name: "region",
      label: "Region",
      placeholder: "us-east-1",
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
};

const SCOPE_FIELDS: Record<string, FieldDef[]> = {
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
      placeholder: "TRUSTOPS",
      required: true,
    },
    {
      name: "schema",
      label: "Schema",
      placeholder: "GOLD",
      required: true,
    },
    {
      name: "evidence_view",
      label: "Evidence view",
      placeholder: "EVIDENCE_EVENTS",
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
        secret: true,
        required: true,
      },
      {
        name: "refresh_token_ref",
        label: "Refresh token reference",
        placeholder: "TRUSTOPS_REFRESH_TOKEN",
        secret: true,
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
        name: "token",
        label: "Scoped credential reference",
        placeholder: "TRUSTOPS_SOURCE_TOKEN",
        secret: true,
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

export function ConnectorDrawer({ connector, onClose, onToast }: Props) {
  const auditor = useAuditorMode();
  const configure = useConfigureMutation();
  const probe = useProbeMutation();
  const runs = useConnectorRuns(connector?.connector_id ?? null);
  const [creds, setCreds] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<Record<string, string>>({});
  const [accessValidated, setAccessValidated] = useState(false);

  useEffect(() => {
    setCreds({});
    setAccessValidated(false);
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
  const usesDiscoveredReadScope =
    connector.connector_id === "clickhouse-telemetry-lake";
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
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={isEnabled ? "ready" : "default"}>
            {connector.state}
          </Badge>
          <Badge>{labelForStatus(connector.production_status)}</Badge>
          <Badge tone="info">
            {connector.access_boundary.replace("_", " ")}
          </Badge>
          <Badge>freshness {connector.freshness_slo_minutes}m SLO</Badge>
        </div>

        <section className="rounded-xl border border-line p-3">
          <div className="text-xs font-black uppercase tracking-wide text-muted">
            Required permissions
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {connector.minimum_permissions.map((perm) => (
              <li key={perm} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                <code className="text-ink">{perm}</code>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-line p-3">
          <div className="text-xs font-black uppercase tracking-wide text-muted">
            Evidence types this connector lands
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {connector.evidence_types.map((t) => (
              <Badge key={t}>{t}</Badge>
            ))}
          </div>
        </section>

        {!auditor && (
          <section className="rounded-xl border border-line p-3">
            <div className="text-xs font-black uppercase tracking-wide text-muted">
              Scoped access · {connector.credential_type.replace(/_/g, " ")}
            </div>
            <div className="mt-2 grid gap-2">
              {credentialFields.map((field) => (
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
              {scopeFields.length > 0 && (
                <div className="mt-2 border-t border-line pt-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Read scope
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {scopeFields.map((field) => (
                      <label
                        key={field.name}
                        className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                      >
                        {field.label}
                        <input
                          value={options[field.name] ?? ""}
                          onChange={(e) => {
                            setAccessValidated(false);
                            setOptions((current) => ({
                              ...current,
                              [field.name]: e.target.value,
                            }));
                          }}
                          placeholder={field.placeholder}
                          className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                        />
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {usesDiscoveredReadScope && (
                <div className="mt-2 rounded-lg border border-line bg-slate-50 p-3">
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Read scope
                  </div>
                  <div className="mt-1 text-xs font-semibold text-muted">
                    A live probe must validate the token and discover only the
                    databases and tables visible to that read scope before this
                    connector can be enabled.
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge tone="info">discovered tables</Badge>
                    <Badge tone="info">least privilege</Badge>
                    <Badge tone="info">no typed scope</Badge>
                  </div>
                  {!isEnabled && (
                    <div className="mt-2 text-xs text-muted">
                      Enter the host and scoped token, test access, then enable.
                      Raw secrets are not persisted.
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
            {canEnable && !isEnabled && accessValidated && (
              <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900">
                Access checked. Enable writes the redacted configuration event.
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
            <AlertCircle className="h-3 w-3" /> Run history ·{" "}
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
