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
import { QueryState } from "@/components/QueryState";
import { usePlatformPricing } from "@/lib/api/hooks";
import type { PricingTier, PricingTierLimits } from "@/lib/api/types";

function tierHighlights(limits: PricingTierLimits): string[] {
  const rows = [
    `${limits.max_users} users`,
    `${limits.max_connectors} connectors`,
  ];
  rows.push(limits.scim ? "SCIM provisioning" : "SSO + trust shares");
  return rows;
}

export default function PricingPage() {
  const pricing = usePlatformPricing();

  return (
    <div className="mx-auto grid max-w-6xl gap-8 p-6 md:p-8">
      <PageHeader
        eyebrow="Managed hosted"
        title="Published pricing tiers"
        description="Annual platform fees for operator-run TrustOps workspaces — loaded live from the platform pricing API. Self-hosted OSS remains $0 license."
      />

      <QueryState queries={pricing} label="pricing tiers">
        {pricing.data && (
          <>
            <p className="text-sm text-muted">{pricing.data.note}</p>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {pricing.data.tiers.map((tier: PricingTier) => (
                <Card
                  key={tier.id}
                  className={
                    tier.id === "team"
                      ? "border-brand shadow-card ring-1 ring-brand/20"
                      : undefined
                  }
                >
                  <CardHeader className="gap-2">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-lg">{tier.name}</CardTitle>
                      {tier.id === "team" && (
                        <Badge tone="ready">Popular</Badge>
                      )}
                    </div>
                    <CardDescription>{tier.tagline}</CardDescription>
                    <div className="pt-1">
                      <span className="text-2xl font-black text-ink">
                        {tier.annual_usd_label}
                      </span>
                      {tier.annual_usd != null && (
                        <span className="text-sm text-muted"> / year</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {tierHighlights(tier.limits).map((h) => (
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
          </>
        )}
      </QueryState>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Compare to managed GRC SaaS
          </CardTitle>
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
          <Button asChild variant="default">
            <Link href="/auth">
              Plan usage (admin)
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
