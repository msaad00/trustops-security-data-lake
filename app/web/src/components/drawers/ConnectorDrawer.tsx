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

const fieldFor = (credentialType: string): string[] => {
  if (credentialType.includes("oauth"))
    return ["client_id", "client_secret", "refresh_token"];
  if (credentialType.includes("key_pair"))
    return ["account", "user", "private_key"];
  if (credentialType.includes("token")) return ["token"];
  if (credentialType.includes("scoped_user"))
    return ["host", "user", "password"];
  if (credentialType.includes("local")) return ["lake_path"];
  return ["api_key"];
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
    setOptions({});
  }, [connector?.connector_id]);

  if (!connector) {
    return (
      <Drawer open={false} onOpenChange={() => undefined} title="Connector">
        <></>
      </Drawer>
    );
  }

  const credentialFields = fieldFor(connector.credential_type);
  const isEnabled = connector.state === "enabled";

  const enable = async () => {
    const payload: ConfigurePayload = {
      state: "enabled",
      actor: "console",
      credentials: creds,
      options,
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
                disabled={probe.isPending}
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
                  disabled={configure.isPending}
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
                  key={field}
                  className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                >
                  {field}
                  <input
                    type={
                      field.includes("secret") ||
                      field.includes("key") ||
                      field.includes("token") ||
                      field.includes("password")
                        ? "password"
                        : "text"
                    }
                    value={creds[field] ?? ""}
                    onChange={(e) =>
                      setCreds((c) => ({ ...c, [field]: e.target.value }))
                    }
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                    placeholder={
                      field.includes("path")
                        ? "/path/to/lake"
                        : `paste ${field}…`
                    }
                  />
                </label>
              ))}
              <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                Options (optional, e.g. org, region)
                <input
                  value={options["raw"] ?? ""}
                  onChange={(e) =>
                    setOptions(() => {
                      try {
                        return {
                          raw: e.target.value,
                          ...JSON.parse(e.target.value),
                        };
                      } catch {
                        return { raw: e.target.value };
                      }
                    })
                  }
                  placeholder='{"org":"acme","region":"us-east-1"}'
                  className="rounded-lg border border-line bg-white px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-brand"
                />
              </label>
            </div>
            {connector.credential_fingerprint && (
              <div className="mt-2 text-xs text-muted">
                Last fingerprint:{" "}
                <code className="text-ink">
                  {connector.credential_fingerprint}
                </code>{" "}
                · configured {connector.configured_at ?? "—"}
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
