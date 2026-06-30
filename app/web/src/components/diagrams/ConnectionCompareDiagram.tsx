"use client";

import { ArrowRight } from "lucide-react";

const SAAS_STEPS = [
  "Read-only IAM role / OAuth / API token",
  "Vendor SaaS pulls on schedule",
  "Evidence in vendor database",
  "Automated control tests",
] as const;

const TRUSTOPS_STEPS = [
  "Same read-only roles & tokens",
  "Your TrustOps scheduler syncs",
  "Evidence in your /lake or warehouse",
  "Deterministic control tests",
] as const;

function Column({
  title,
  eyebrow,
  steps,
  accent,
}: {
  title: string;
  eyebrow: string;
  steps: readonly string[];
  accent: "vendor" | "customer";
}) {
  const header =
    accent === "vendor"
      ? "border-rose-200 bg-rose-50 text-rose-900"
      : "border-emerald-200 bg-emerald-50 text-emerald-900";
  return (
    <div className="grid min-w-0 gap-2 rounded-xl border border-line bg-white p-4 shadow-card">
      <div className={`rounded-lg border px-3 py-2 ${header}`}>
        <div className="text-[10px] font-black uppercase tracking-wide opacity-80">
          {eyebrow}
        </div>
        <div className="text-sm font-black">{title}</div>
      </div>
      <ol className="grid gap-2">
        {steps.map((step, index) => (
          <li
            key={step}
            className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-2 text-xs leading-5 text-muted"
          >
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-panel text-[10px] font-black text-ink ring-1 ring-line">
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ConnectionCompareDiagram() {
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-black uppercase tracking-wide text-muted">
          How connections compare
        </span>
        <span className="text-[11px] font-bold text-muted">
          Read-only APIs and roles — different evidence boundary
        </span>
      </div>
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-center">
        <Column
          eyebrow="Typical GRC SaaS"
          title="Drata / Vanta"
          steps={SAAS_STEPS}
          accent="vendor"
        />
        <ArrowRight
          className="mx-auto hidden h-5 w-5 text-muted lg:block"
          aria-hidden
        />
        <Column
          eyebrow="OSS + self-hosted"
          title="TrustOps"
          steps={TRUSTOPS_STEPS}
          accent="customer"
        />
      </div>
      <p className="text-xs leading-5 text-muted">
        AWS uses cross-account IAM assume-role with External ID. GitHub uses App
        installation tokens. Okta and Google use read-only API/OAuth scopes.
        TrustOps uses the same connection families; you keep the lake.
      </p>
    </div>
  );
}
