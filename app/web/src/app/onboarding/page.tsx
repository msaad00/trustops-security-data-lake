"use client";

import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  ListChecks,
  Rocket,
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
import { usePocReadiness } from "@/lib/api/hooks";
import type { PocReadinessStep } from "@/lib/api/types";

function stepHref(step: PocReadinessStep) {
  return step.console_href ?? step.href?.replace(/^\/console/, "") ?? null;
}

export default function OnboardingPage() {
  const readiness = usePocReadiness();
  const data = readiness.data;
  const onboarding = data?.onboarding;
  const progress = onboarding?.progress_percent ?? 0;
  const current = data?.next_step ?? null;

  return (
    <div className="mx-auto grid w-full max-w-3xl min-w-0 gap-4 px-3 py-4 sm:px-4">
      <PageHeader
        eyebrow="Getting started"
        title="First-run onboarding"
        description="Walk through the gates to connect a source, prove sync, and share trust — the same path managed GRC tools use for evaluators."
        actions={
          data && (
            <Badge tone={data.shareable ? "ready" : "attention"}>
              {data.shareable ? "shareable" : `${progress}% ready`}
            </Badge>
          )
        }
      />

      {readiness.isLoading && (
        <Card>
          <CardContent className="p-6 text-sm font-bold text-muted">
            Loading onboarding progress...
          </CardContent>
        </Card>
      )}

      {readiness.isError && (
        <Card>
          <CardContent className="p-6 text-sm text-muted">
            Admin access is required to view onboarding progress.
          </CardContent>
        </Card>
      )}

      {data && onboarding && (
        <>
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between text-xs font-black uppercase tracking-wide text-muted">
                <span>Blocking progress</span>
                <span>
                  {onboarding.completed_blocking}/{onboarding.blocking_total}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#315dff] to-[#21c6c7]"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </CardContent>
          </Card>

          {current && (
            <Card className="border-brand/40 bg-brand/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Rocket className="h-5 w-5 text-brand" />
                  Current step: {current.label}
                </CardTitle>
                <CardDescription>{current.detail}</CardDescription>
              </CardHeader>
              <CardContent>
                {stepHref(current) ? (
                  <Button asChild variant="primary">
                    <Link href={stepHref(current)!}>
                      Continue setup
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                ) : (
                  <Badge tone="attention">Configure in deployment settings</Badge>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Onboarding checklist</CardTitle>
              <CardDescription>
                Complete blocking steps to reach a shareable trust workspace.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2">
              {onboarding.steps.map((step) => {
                const ready = step.status === "ready";
                const href = stepHref(step);
                return (
                  <div
                    key={step.id}
                    className="flex items-start gap-3 rounded-xl border border-line bg-white p-3"
                  >
                    {ready ? (
                      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
                    ) : (
                      <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-black text-ink">{step.label}</div>
                        <Badge tone={ready ? "ready" : "attention"}>
                          {ready ? "done" : "todo"}
                        </Badge>
                        {!step.blocking && (
                          <Badge tone="info">optional</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">{step.detail}</p>
                    </div>
                    {href && !ready && (
                      <Button asChild variant="default" size="sm">
                        <Link href={href}>Open</Link>
                      </Button>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button asChild variant="default">
              <Link href="/poc">
                <ListChecks className="h-4 w-4" />
                Full launch checklist
              </Link>
            </Button>
            {data.shareable && (
              <Button asChild variant="primary">
                <Link href="/demo">
                  Open demo landing
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
