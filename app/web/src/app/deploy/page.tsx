"use client";

import Link from "next/link";
import {
  ArrowRight,
  Cloud,
  DollarSign,
  GitBranch,
  Plug,
  Server,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { FlowStrip, type FlowStep } from "@/components/diagrams/FlowStrip";

const MODELS = [
  {
    title: "OSS local",
    detail:
      "Run fixtures and the console on your laptop or in CI. $0 software license.",
    icon: GitBranch,
    badge: "Free",
  },
  {
    title: "Self-hosted",
    detail:
      "Helm on your cluster. Evidence in your VPC, Snowflake, or lake boundary.",
    icon: Server,
    badge: "Infra only",
  },
  {
    title: "Managed hosted",
    detail:
      "Operator-run workspace URL with SSO and connectors — target ⅓–½ of Vanta/Drata platform TCO.",
    icon: Cloud,
    badge: "POC today",
  },
] as const;

const COMPARE_ROWS = [
  {
    line: "Annual platform fee (est., 1 framework)",
    trustops: "Self-hosted: $0 license",
    vanta: "~$10k–$28k",
  },
  {
    line: "Evidence ownership",
    trustops: "Your lake / warehouse",
    vanta: "Vendor-operated",
  },
  {
    line: "Self-host / air-gap",
    trustops: "Yes",
    vanta: "No",
  },
  {
    line: "Controls-as-code + agent API",
    trustops: "Yes",
    vanta: "Limited",
  },
] as const;

const DEPLOY_FLOW: FlowStep[] = [
  {
    step: "01",
    title: "Choose model",
    detail: "OSS local, self-hosted Helm, or managed hosted workspace.",
    tone: "brand",
  },
  {
    step: "02",
    title: "Mount SSO",
    detail: "OIDC/SAML for humans; API keys for agents and CI.",
    tone: "neutral",
  },
  {
    step: "03",
    title: "Link sources",
    detail: "Read-only connectors — same pattern as Drata/Vanta.",
    tone: "lake",
  },
  {
    step: "04",
    title: "Prove ingestion",
    detail: "Probe, enable, sync into your evidence lake.",
    tone: "assess",
  },
];

export default function DeployPage() {
  return (
    <div className="mx-auto grid w-full max-w-[1200px] min-w-0 gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Open source"
        title="Deploy your way"
        description="TrustOps is OSS-first: run locally, self-host in your cloud, or use managed hosted — continuous compliance without a vendor evidence silo."
        actions={<Badge tone="ready">OSS + self-hosted</Badge>}
      />

      <Card className="overflow-hidden">
        <CardContent className="grid gap-0 p-0 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="border-b border-line p-6 lg:border-b-0 lg:border-r">
            <div className="flex items-center gap-2 text-brand">
              <ShieldCheck className="h-5 w-5" />
              <span className="text-sm font-black uppercase tracking-wide">
                Drata / Vanta alternative
              </span>
            </div>
            <h2 className="mt-3 text-2xl font-black text-ink">
              Same loop, fraction of the platform cost
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
              Link accounts, ingest evidence, evaluate controls, and share trust
              links — with deterministic tests over your evidence lake instead
              of opaque SaaS storage. Managed hosted targets roughly one-third to
              one-half the annual platform TCO of comparable Vanta or Drata
              scope.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button asChild variant="primary">
                <Link href="/poc">
                  Launch checklist
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="default">
                <Link href="/demo">Hosted demo</Link>
              </Button>
            </div>
          </div>
          <div className="grid gap-3 bg-panel p-6">
            {MODELS.map(({ title, detail, icon: Icon, badge }) => (
              <div
                key={title}
                className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 rounded-xl border border-line bg-white p-3"
              >
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-panel text-brand ring-1 ring-line">
                  <Icon className="h-4 w-4" />
                </span>
                <span>
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-black text-ink">{title}</span>
                    <Badge tone="default">{badge}</Badge>
                  </span>
                  <span className="mt-0.5 block text-xs leading-5 text-muted">
                    {detail}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plug className="h-5 w-5" />
            Connectors &amp; ingestion
          </CardTitle>
          <CardDescription>
            16 read-only connectors with vendor marks, setup hints, and live
            ingestion into your evidence lake — AWS, Azure, GCP, GitHub, Okta,
            Snowflake, and more.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="default">
            <Link href="/connectors">Open connector registry</Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Go-live path</CardTitle>
          <CardDescription>
            From zero to shareable POC — OSS license, your infra, your evidence.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FlowStrip steps={DEPLOY_FLOW} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Cost comparison (illustrative)
          </CardTitle>
          <CardDescription>
            Vanta and Drata use custom sales-led pricing. Ranges below are from
            public buyer reports; TrustOps separates OSS software from ops.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs font-black uppercase tracking-wide text-muted">
                <th className="py-2 pr-4">Line item</th>
                <th className="py-2 pr-4">TrustOps</th>
                <th className="py-2">Vanta / Drata (est.)</th>
              </tr>
            </thead>
            <tbody>
              {COMPARE_ROWS.map((row) => (
                <tr key={row.line} className="border-b border-line/60">
                  <td className="py-3 pr-4 font-medium text-ink">{row.line}</td>
                  <td className="py-3 pr-4 text-brand">{row.trustops}</td>
                  <td className="py-3 text-muted">{row.vanta}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-4 text-xs leading-5 text-muted">
            Full positioning, Helm runbooks, and when to choose each model: see{" "}
            <code className="rounded bg-panel px-1 py-0.5 text-ink">
              docs/DEPLOYMENT_AND_PRICING.md
            </code>{" "}
            in the repository.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
