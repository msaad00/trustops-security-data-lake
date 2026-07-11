"use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Cloud,
  GitBranch,
  Monitor,
  Plug,
  Server,
  Terminal,
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
import { ConnectionCompareDiagram } from "@/components/diagrams/ConnectionCompareDiagram";
import { FlowStrip, type FlowStep } from "@/components/diagrams/FlowStrip";
import { BRAND } from "@/lib/brand";

const DEPLOYMENT_MODELS = [
  {
    title: "OSS local",
    detail: "Fixtures + console on laptop or CI. Open-source license.",
    icon: GitBranch,
    badge: "Available",
  },
  {
    title: "Self-hosted",
    detail: "Helm in your VPC. Evidence in your lake or warehouse.",
    icon: Server,
    badge: "Available",
  },
  {
    title: "Managed cloud",
    detail: "Operator-run workspace with SSO, scheduler, and support.",
    icon: Cloud,
    badge: "Coming soon",
  },
] as const;

const SURFACES = [
  {
    surface: "Headless",
    icon: Terminal,
    callers: "CI, scripts, MCP agents, scheduler",
    entry: "REST `/api/v1`, CLI, MCP tools",
    writes: "Gated mutations with Idempotency-Key",
  },
  {
    surface: "Human console",
    icon: Monitor,
    callers: "GRC leads, auditors, operators",
    entry: "/console/* workbench routes",
    writes: "Same API as headless + session audit",
  },
] as const;

const EDITIONS = [
  {
    id: "oss",
    name: "OSS",
    deploy: "Local / CI",
    headless: "Full API + CLI + MCP",
    console: "Full workbench",
    support: "Community",
  },
  {
    id: "self-hosted",
    name: "Self-hosted",
    deploy: "Your cluster",
    headless: "Full API + agents + CI gates",
    console: "Full workbench + OIDC",
    support: "Your ops team",
  },
  {
    id: "managed",
    name: "Managed cloud",
    deploy: "Operator URL (future)",
    headless: "API keys + audit log",
    console: "Full workbench + SSO",
    support: "Commercial (future)",
  },
] as const;

const DEPLOY_FLOW: FlowStep[] = [
  {
    step: "01",
    title: "Choose model",
    detail: "OSS local or self-hosted Helm today; managed cloud later.",
    tone: "brand",
  },
  {
    step: "02",
    title: "Mount auth",
    detail: "OIDC/SAML for humans; API keys for automation.",
    tone: "neutral",
  },
  {
    step: "03",
    title: "Link sources",
    detail: "Read-only connectors — probe, enable, sync.",
    tone: "lake",
  },
  {
    step: "04",
    title: "Operate",
    detail: "Dashboard, audit room, API, trust shares.",
    tone: "assess",
  },
];

export default function DeployPage() {
  return (
    <div className="mx-auto grid w-full max-w-[1200px] min-w-0 gap-3 px-3 py-3 sm:px-4 lg:px-5">
      <PageHeader
        eyebrow="Platform"
        title="Deployment models"
        description={`${BRAND.name} is open source — the Drata/Vanta-style audit loop for AI, cloud, and modern infra. Run locally, self-host in your VPC, or wait for managed cloud.`}
      />

      <div className="grid gap-3 lg:grid-cols-3">
        {DEPLOYMENT_MODELS.map(({ title, detail, icon: Icon, badge }) => (
          <Card key={title} className="overflow-hidden">
            <CardContent className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 p-4">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-panel text-brand ring-1 ring-line">
                <Icon className="h-4 w-4" />
              </span>
              <span className="min-w-0 overflow-hidden">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-black text-ink">
                    {title}
                  </span>
                  <Badge tone={badge === "Coming soon" ? "default" : "ready"}>
                    {badge}
                  </Badge>
                </span>
                <span className="mt-0.5 line-clamp-2 block text-xs leading-5 text-muted">
                  {detail}
                </span>
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-4 w-4" />
            Headless vs human surfaces
          </CardTitle>
          <CardDescription>
            One deterministic core — automation and console read the same JSON.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs font-black uppercase tracking-wide text-muted">
                <th className="py-2 pr-4">Surface</th>
                <th className="py-2 pr-4">Callers</th>
                <th className="py-2 pr-4">Entry</th>
                <th className="py-2">Writes</th>
              </tr>
            </thead>
            <tbody>
              {SURFACES.map((row) => (
                <tr key={row.surface} className="border-b border-line/60">
                  <td className="py-3 pr-4">
                    <span className="inline-flex items-center gap-2 font-black text-ink">
                      <row.icon className="h-4 w-4 shrink-0 text-brand" />
                      {row.surface}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-muted">{row.callers}</td>
                  <td className="py-3 pr-4">
                    <code className="break-all rounded bg-panel px-1 py-0.5 text-xs text-ink">
                      {row.entry}
                    </code>
                  </td>
                  <td className="py-3 text-muted">{row.writes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-base">Editions</CardTitle>
          <CardDescription>
            Feature matrix by deployment — OSS and self-hosted ship today.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs font-black uppercase tracking-wide text-muted">
                <th className="py-2 pr-4">Edition</th>
                <th className="py-2 pr-4">Deploy</th>
                <th className="py-2 pr-4">Headless</th>
                <th className="py-2 pr-4">Console</th>
                <th className="py-2">Support</th>
              </tr>
            </thead>
            <tbody>
              {EDITIONS.map((row) => (
                <tr key={row.id} className="border-b border-line/60">
                  <td className="py-3 pr-4 font-black text-ink">{row.name}</td>
                  <td className="py-3 pr-4 text-muted">{row.deploy}</td>
                  <td className="py-3 pr-4 text-muted">{row.headless}</td>
                  <td className="py-3 pr-4 text-muted">{row.console}</td>
                  <td className="py-3 text-muted">{row.support}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild variant="primary" size="sm">
              <Link href="/agents">
                Agent API reference
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="default" size="sm">
              <Link href="/connectors">Connector registry</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Plug className="h-4 w-4" />
            Connectors
          </CardTitle>
          <CardDescription>
            16 read-only connectors — AWS, Azure, GCP, GitHub, Okta, Snowflake,
            and more.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="default" size="sm">
            <Link href="/connectors">Open connector registry</Link>
          </Button>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-base">Go-live path</CardTitle>
          <CardDescription>
            From zero to operating posture — open-source license, your infra,
            your evidence.
          </CardDescription>
        </CardHeader>
        <CardContent className="min-w-0 overflow-hidden">
          <FlowStrip steps={DEPLOY_FLOW} />
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-base">Evidence boundary</CardTitle>
          <CardDescription>
            Read-only connection families — where synced evidence is stored.
          </CardDescription>
        </CardHeader>
        <CardContent className="min-w-0 overflow-hidden">
          <ConnectionCompareDiagram />
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-base">Launch checklist</CardTitle>
          <CardDescription>
            POC readiness gates, demo kit links, and shareable URLs.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild variant="primary" size="sm">
            <Link href="/poc">
              Open launch checklist
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="default" size="sm">
            <Link href="/demo">Demo landing</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
