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
    <div className="grid min-w-0 gap-2 overflow-hidden rounded-xl border border-line bg-white p-4">
      <div className={`overflow-hidden rounded-lg border px-3 py-2 ${header}`}>
        <div className="truncate text-[10px] font-black uppercase tracking-wide opacity-80">
          {eyebrow}
        </div>
        <div className="truncate text-sm font-black">{title}</div>
      </div>
      <ol className="grid gap-2">
        {steps.map((step, index) => (
          <li
            key={step}
            className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-2 overflow-hidden text-xs leading-5 text-muted"
          >
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-panel text-[10px] font-black text-ink ring-1 ring-line">
              {index + 1}
            </span>
            <span className="line-clamp-2 min-w-0">{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ConnectionCompareDiagram() {
  return (
    <div className="grid min-w-0 gap-3 overflow-hidden">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-stretch">
        <Column
          eyebrow="Managed GRC SaaS"
          title="Vendor-hosted evidence"
          steps={SAAS_STEPS}
          accent="vendor"
        />
        <ArrowRight
          className="mx-auto hidden h-5 w-5 shrink-0 self-center text-muted lg:block"
          aria-hidden
        />
        <Column
          eyebrow="TrustOps"
          title="Customer-owned lake"
          steps={TRUSTOPS_STEPS}
          accent="customer"
        />
      </div>
      <p className="line-clamp-3 text-xs leading-5 text-muted">
        AWS cross-account IAM, GitHub App tokens, and Okta/Google read-only scopes
        use the same connection patterns — TrustOps stores raw events in your
        boundary.
      </p>
    </div>
  );
}
