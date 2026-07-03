"use client";

import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
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

const TIERS = [
  {
    id: "starter",
    name: "Starter",
    price: "$4,800",
    period: "/ year",
    tagline: "Evaluator workspace and small-team POC",
    highlights: ["5 users", "2 connectors", "SSO + trust shares"],
    includes: [
      "Hosted workspace URL",
      "OIDC / SAML SSO",
      "2 live connectors",
      "Trust-center shares",
      "Community support",
    ],
  },
  {
    id: "team",
    name: "Team",
    price: "$12,000",
    period: "/ year",
    tagline: "Production pilot for one framework program",
    highlights: ["25 users", "10 connectors", "Workflows + agents"],
    includes: [
      "Everything in Starter",
      "10 connectors + scheduler",
      "Workflow automation",
      "Agent harness + MCP",
      "Email support (business hours)",
    ],
    featured: true,
  },
  {
    id: "business",
    name: "Business",
    price: "$28,000",
    period: "/ year",
    tagline: "Multi-framework GRC with SCIM lifecycle",
    highlights: ["100 users", "SCIM", "Priority support"],
    includes: [
      "Everything in Team",
      "SCIM 2.0 provisioning",
      "Vendor risk + policy library",
      "HA read-replica guidance",
      "Priority support",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    period: "",
    tagline: "Dedicated tenant, custom SLAs, air-gap options",
    highlights: ["Dedicated cluster", "Custom frameworks", "CSM onboarding"],
    includes: [
      "Dedicated or isolated cluster",
      "Custom framework packs",
      "Customer success + onboarding",
      "~⅓–½ managed GRC platform TCO target",
    ],
  },
] as const;

export default function PricingPage() {
  return (
    <div className="mx-auto grid max-w-6xl gap-8 p-6 md:p-8">
      <PageHeader
        eyebrow="Managed hosted"
        title="Published pricing tiers"
        description="Annual platform fees for operator-run TrustOps workspaces. Self-hosted OSS remains $0 license — you own the evidence lake either way."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {TIERS.map((tier) => (
          <Card
            key={tier.id}
            className={
              "featured" in tier && tier.featured
                ? "border-brand shadow-card ring-1 ring-brand/20"
                : undefined
            }
          >
            <CardHeader className="gap-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-lg">{tier.name}</CardTitle>
                {"featured" in tier && tier.featured && (
                  <Badge tone="ready">Popular</Badge>
                )}
              </div>
              <CardDescription>{tier.tagline}</CardDescription>
              <div className="pt-1">
                <span className="text-2xl font-black text-ink">{tier.price}</span>
                <span className="text-sm text-muted">{tier.period}</span>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {tier.highlights.map((h) => (
                  <span
                    key={h}
                    className="rounded-full border border-line bg-panel px-2 py-0.5 text-[10px] font-bold text-muted"
                  >
                    {h}
                  </span>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <ul className="grid gap-2 text-sm text-muted">
                {tier.includes.map((item) => (
                  <li key={item} className="flex gap-2">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand-green" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Compare to managed GRC SaaS</CardTitle>
          <CardDescription>
            Typical SOC 2 platform fees run ~$10k–$28k/year for startups and
            $50k–$110k+ for mid-market multi-framework programs — before
            auditors, pen tests, and renewal uplifts.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button asChild variant="default">
            <Link href="/deploy">
              Deployment models
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="default">
            <Link href="/poc">
              POC readiness
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
