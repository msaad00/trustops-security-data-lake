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
import type { ConfigurePayload, ConnectorView } from "@/lib/api/types";

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
      label: "Scoped access token",
      placeholder: "paste scoped token...",
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
      name: "private_key",
      label: "Private key or OAuth token",
      placeholder: "paste key or token...",
      secret: true,
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
        name: "client_secret",
        label: "Client secret",
        placeholder: "paste secret...",
        secret: true,
        required: true,
      },
      {
        name: "refresh_token",
        label: "Refresh token",
        placeholder: "paste refresh token...",
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
        label: "Private key",
        placeholder: "paste key...",
        secret: true,
        required: true,
      },
    ];
  if (credentialType.includes("token"))
    return [
      {
        name: "token",
        label: "Scoped token",
        placeholder: "paste token...",
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
        label: "User",
        placeholder: "read-only user",
        required: true,
      },
      {
        name: "password",
        label: "Password",
        placeholder: "paste password...",
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
      label: "API key",
      placeholder: "paste API key...",
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

  useEffect(() => {
    setCreds({});
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

  const enable = async () => {
    if (!canEnable) {
      onToast(`Required before enabling: ${missingRequired.join(", ")}.`);
      return;
    }
    const payload: ConfigurePayload = {
      state: "enabled",
      actor: "console",
      credentials: Object.fromEntries(
        Object.entries(creds).filter(([, value]) => value.trim() !== ""),
      ),
      options: Object.fromEntries(
        Object.entries(options).filter(([, value]) => value.trim() !== ""),
      ),
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
      const { run } = await probe.mutateAsync(connector.connector_id);
      onToast(
        run.result === "ok"
          ? `Probe ok — ${run.evidence_count ?? 0} evidence types reachable.`
          : `Probe ${run.result}: ${run.error ?? "see history"}`,
      );
    } catch (err) {
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
              Credentials hashed to a fingerprint server-side; raw secret never
              persisted.
            </span>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="default"
                onClick={runProbe}
                disabled={probe.isPending || !isEnabled}
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
                  disabled={configure.isPending || !canEnable}
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
              Credentials · {connector.credential_type.replace(/_/g, " ")}
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
                    onChange={(e) =>
                      setCreds((c) => ({
                        ...c,
                        [field.name]: e.target.value,
                      }))
                    }
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
                          onChange={(e) =>
                            setOptions((current) => ({
                              ...current,
                              [field.name]: e.target.value,
                            }))
                          }
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
                    After enable, Test connection discovers the databases and
                    tables visible to this token. Select evidence tables from
                    that discovered list instead of typing table names here.
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge tone="info">discovered tables</Badge>
                    <Badge tone="info">least privilege</Badge>
                    <Badge tone="info">no typed scope</Badge>
                  </div>
                  {!isEnabled && (
                    <div className="mt-2 text-xs text-muted">
                      Enable with a scoped read token first; raw secrets are not
                      persisted.
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
