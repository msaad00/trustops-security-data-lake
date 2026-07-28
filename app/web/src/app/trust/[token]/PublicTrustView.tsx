"use client";

import { useEffect, useState } from "react";
import { Lock, Loader2, ShieldAlert } from "lucide-react";
import { TrustOpsLogo } from "@/components/brand/TrustOpsLogo";
import { Badge } from "@/components/ui/badge";

type FrameworkRow = {
  framework: string | null;
  score: number | null;
  state: string | null;
  control_count: number | null;
  failing_control_count: number | null;
  stale_control_count: number | null;
};

type PublicTrust = {
  schema_version: string;
  data_residency: string;
  issued_by: string | null;
  scope: string | null;
  role: string | null;
  expires_at: string | null;
  evaluated_at: string | null;
  posture: {
    score: number | null;
    state: string | null;
    framework_count: number | null;
    control_count: number | null;
    open_violation_count: number | null;
    critical_violation_count: number | null;
    high_violation_count: number | null;
    stale_control_count: number | null;
  };
  frameworks: FrameworkRow[];
};

function tokenFromPath(): string {
  if (typeof window === "undefined") return "";
  const parts = window.location.pathname.replace(/\/$/, "").split("/");
  return parts[parts.length - 1] ?? "";
}

function stateTone(state: string | null): "ready" | "attention" | "critical" {
  if (state === "ready") return "ready";
  if (state === "critical" || state === "at_risk") return "critical";
  return "attention";
}

function ResidencyBanner() {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-cyan-700/40 bg-[#06283d] p-4 text-cyan-50">
      <Lock className="mt-0.5 h-5 w-5 shrink-0 text-cyan-300" />
      <div>
        <p className="text-sm font-extrabold">
          Evidence never leaves this lake — only this summary is shared.
        </p>
        <p className="mt-1 text-xs leading-5 text-cyan-200/80">
          This is a redacted, read-only posture issued for an external reviewer.
          Owners, notes, raw evidence, and asset internals are not transmitted.
        </p>
      </div>
    </div>
  );
}

export default function PublicTrustView() {
  const [data, setData] = useState<PublicTrust | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "invalid">("loading");

  useEffect(() => {
    const token = tokenFromPath();
    if (!token || token === "share") {
      setStatus("invalid");
      return;
    }
    let cancelled = false;
    fetch(`/api/public/trust/${encodeURIComponent(token)}`, {
      cache: "no-store",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status));
        return (await res.json()) as PublicTrust;
      })
      .then((body) => {
        if (cancelled) return;
        setData(body);
        setStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("invalid");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="grid min-h-screen place-items-center bg-[#04101c] p-6">
      <div className="w-full max-w-[860px]">
        <header className="mb-6 flex items-center gap-4 text-white">
          <TrustOpsLogo
            showWordmark
            subtitle="Trust Center"
            inverted
            markSize="lg"
            gradientId="trustops-trust-gradient"
          />
          <p className="min-w-0 flex-1 text-sm leading-6 text-slate-400">
            Shared, read-only verification for external reviewers.
          </p>
        </header>

        <div className="mb-6">
          <ResidencyBanner />
        </div>

        {status === "loading" && (
          <div className="flex items-center gap-3 rounded-xl border border-[#1e334a] bg-[#07111e] p-8 text-slate-300">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-300" />
            Loading shared posture…
          </div>
        )}

        {status === "invalid" && (
          <div className="rounded-xl border border-rose-700/40 bg-[#1a0c12] p-8 text-rose-100">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-6 w-6 text-rose-300" />
              <h2 className="text-lg font-extrabold">
                This trust link is invalid or has expired.
              </h2>
            </div>
            <p className="mt-3 text-sm leading-6 text-rose-200/80">
              The token may have been revoked, reached its expiry, or was never
              issued. Ask the issuing organization for a fresh link. No posture
              data is disclosed for unrecognized tokens.
            </p>
          </div>
        )}

        {status === "ok" && data && (
          <div className="grid gap-4">
            <div className="rounded-xl border border-[#1e334a] bg-[#07111e] p-6 text-white">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">
                    Overall posture
                  </p>
                  <p className="mt-1 text-5xl font-black">
                    {data.posture.score ?? "—"}
                    <span className="ml-1 text-xl text-slate-500">/ 100</span>
                  </p>
                </div>
                <Badge tone={stateTone(data.posture.state)}>
                  {data.posture.state ?? "unknown"}
                </Badge>
              </div>
              <dl className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-slate-400">Frameworks</dt>
                  <dd className="font-extrabold">
                    {data.posture.framework_count ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">Controls</dt>
                  <dd className="font-extrabold">
                    {data.posture.control_count ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">Open violations</dt>
                  <dd className="font-extrabold">
                    {data.posture.open_violation_count ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">Stale controls</dt>
                  <dd className="font-extrabold">
                    {data.posture.stale_control_count ?? 0}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border border-[#1e334a] bg-[#07111e] p-6 text-white">
              <h2 className="mb-4 text-sm font-extrabold uppercase tracking-wide text-slate-300">
                Framework readiness
              </h2>
              <div className="grid gap-2">
                {data.frameworks.length === 0 && (
                  <p className="text-sm text-slate-400">
                    No framework readiness to report.
                  </p>
                )}
                {data.frameworks.map((row) => (
                  <div
                    key={row.framework ?? Math.random()}
                    className="flex items-center justify-between rounded-lg border border-[#16283c] bg-[#0a1726] px-4 py-3"
                  >
                    <div>
                      <p className="font-extrabold">{row.framework ?? "—"}</p>
                      <p className="text-xs text-slate-400">
                        {row.control_count ?? 0} controls ·{" "}
                        {row.failing_control_count ?? 0} failing ·{" "}
                        {row.stale_control_count ?? 0} stale
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-black">
                        {row.score ?? "—"}
                      </span>
                      <Badge tone={stateTone(row.state)}>
                        {row.state ?? "unknown"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <footer className="rounded-xl border border-[#1e334a] bg-[#07111e] px-6 py-4 text-xs text-slate-400">
              Issued by{" "}
              <span className="font-extrabold text-slate-200">
                {data.issued_by ?? "the data owner"}
              </span>
              {data.expires_at && <> · expires {data.expires_at}</>}
              {data.evaluated_at && <> · evaluated {data.evaluated_at}</>}
            </footer>
          </div>
        )}
      </div>
    </section>
  );
}
