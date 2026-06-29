"use client";

import Link from "next/link";
import {
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  Globe2,
  KeyRound,
  Plug,
  Share2,
  UserRoundCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { usePocReadiness } from "@/lib/api/hooks";
import type { PocReadinessStep } from "@/lib/api/types";

const stateCopy: Record<
  string,
  { label: string; tone: "ready" | "attention" }
> = {
  ready: { label: "Ready to share", tone: "ready" },
  internal_ready: { label: "Internal POC ready", tone: "attention" },
  needs_setup: { label: "Needs setup", tone: "attention" },
};

function stepTone(status: string) {
  return status === "ready" ? "ready" : "attention";
}

function stepIcon(step: PocReadinessStep) {
  if (step.id === "public_url") return Globe2;
  if (step.id === "human_access") return UserRoundCheck;
  if (step.id === "headless_access") return KeyRound;
  if (step.id === "source_sync") return Plug;
  if (step.id === "trust_share") return Share2;
  return step.status === "ready" ? CheckCircle2 : CircleAlert;
}

function internalHref(href: string | null) {
  if (!href) return null;
  return href.startsWith("/console") ? href.replace(/^\/console/, "") : href;
}

function Gate({ step }: { step: PocReadinessStep }) {
  const Icon = stepIcon(step);
  const href = internalHref(step.href);
  const content = (
    <div className="grid h-full min-w-0 gap-3 rounded-xl border border-line bg-white p-4 transition-colors hover:border-brand">
      <div className="flex items-start justify-between gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-panel text-brand ring-1 ring-line">
          <Icon className="h-4 w-4" />
        </span>
        <Badge tone={stepTone(step.status)}>
          {step.status === "ready" ? "ready" : "setup"}
        </Badge>
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-black text-ink">{step.label}</div>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
          {step.detail}
        </p>
      </div>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-panel p-3">
      <div className="text-[10px] font-black uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className="mt-1 truncate text-2xl font-black leading-none text-ink">
        {value}
      </div>
      <div className="mt-1 truncate text-xs text-muted">{detail}</div>
    </div>
  );
}

export default function PocPage() {
  const readiness = usePocReadiness();
  const data = readiness.data;
  const state = data
    ? (stateCopy[data.state] ?? stateCopy.needs_setup)
    : stateCopy.needs_setup;

  return (
    <div className="mx-auto grid w-full max-w-[1400px] min-w-0 gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Launch"
        title="POC readiness"
        description="Confirm this deployment can invite users, connect sources, sync evidence, and share trust."
        actions={
          data && (
            <Badge tone={state.tone}>
              {data.shareable ? "shareable" : state.label}
            </Badge>
          )
        }
      />

      {readiness.isLoading && (
        <Card>
          <CardContent className="p-6 text-sm font-bold text-muted">
            Checking launch readiness...
          </CardContent>
        </Card>
      )}

      {readiness.isError && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-start gap-3">
              <CircleAlert className="mt-0.5 h-5 w-5 text-amber-600" />
              <div>
                <div className="font-black text-ink">
                  Admin access is required.
                </div>
                <p className="mt-1 text-sm leading-6 text-muted">
                  POC readiness includes auth, tenant, and connector state, so
                  it is only available to admins.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <Card>
            <CardContent className="grid gap-4 p-5 lg:grid-cols-[300px_minmax(0,1fr)_280px]">
              <div className="rounded-xl border border-line bg-panel p-5">
                <div className="text-[10px] font-black uppercase tracking-wide text-muted">
                  Launch state
                </div>
                <div className="mt-3 text-3xl font-black leading-none text-ink">
                  {state.label}
                </div>
                <p className="mt-3 text-sm leading-6 text-muted">
                  {data.shareable
                    ? "A team can be invited to the hosted POC."
                    : "Finish the next gate before sharing externally."}
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                {data.steps.map((step) => (
                  <Gate key={step.id} step={step} />
                ))}
              </div>

              <div className="rounded-xl border border-line bg-white p-5">
                <div className="text-[10px] font-black uppercase tracking-wide text-muted">
                  Next step
                </div>
                <div className="mt-3 text-lg font-black text-ink">
                  {data.next_step?.label ?? "Ready"}
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {data.next_step?.detail ??
                    "Keep syncs healthy and review trust shares before expiry."}
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Access and sharing</CardTitle>
                <CardDescription>
                  Human login, headless access, and external assurance links.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2">
                <Metric
                  label="Browser login"
                  value={data.access.browser_sso_configured ? "SSO" : "not set"}
                  detail={
                    data.access.require_auth ? "auth required" : "local mode"
                  }
                />
                <Metric
                  label="API keys"
                  value={data.access.active_api_keys}
                  detail="active headless keys"
                />
                <Metric
                  label="Trust shares"
                  value={data.trust_shares.active}
                  detail="active external links"
                />
                <Metric
                  label="Public URL"
                  value={data.public_url ? "set" : "missing"}
                  detail={data.public_url ?? "TRUSTOPS_PUBLIC_URL"}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Source readiness</CardTitle>
                <CardDescription>
                  Connected evidence sources and current ingestion health.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2">
                <Metric
                  label="Sources"
                  value={data.connectors.enabled}
                  detail={`${data.connectors.source_count} evidence source(s)`}
                />
                <Metric
                  label="Evidence"
                  value={data.connectors.evidence_count}
                  detail="normalized rows"
                />
                <Metric
                  label="Failed"
                  value={data.connectors.failed}
                  detail="connector errors"
                />
                <Metric
                  label="Silent"
                  value={data.connectors.silent}
                  detail="missed sync SLO"
                />
              </CardContent>
            </Card>
          </div>

          {data.public_url && (
            <a
              href={data.public_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 text-sm font-black text-ink hover:border-brand"
            >
              Open public URL
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </>
      )}
    </div>
  );
}
