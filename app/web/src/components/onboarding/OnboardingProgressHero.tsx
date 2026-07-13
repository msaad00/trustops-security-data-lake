"use client";

import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Plug,
  RefreshCw,
  ShieldCheck,
  Share2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { KodaMark } from "@/components/brand/KodaMark";
import type { PocReadinessStep } from "@/lib/api/types";

const STAGES = [
  {
    id: "connect",
    label: "Connect",
    icon: Plug,
    href: "/connectors/?connect=aws-posture",
  },
  { id: "sync", label: "Sync", icon: RefreshCw, href: "/connectors" },
  { id: "evaluate", label: "Evaluate", icon: ShieldCheck, href: "/dashboard" },
  { id: "share", label: "Share", icon: Share2, href: "/trust-center" },
] as const;

interface Props {
  progress: number;
  shareable: boolean;
  completedBlocking: number;
  blockingTotal: number;
  currentStep: PocReadinessStep | null;
  currentHref: string | null;
}

export function OnboardingProgressHero({
  progress,
  shareable,
  completedBlocking,
  blockingTotal,
  currentStep,
  currentHref,
}: Props) {
  const stageIndex = Math.min(
    STAGES.length - 1,
    Math.floor((progress / 100) * STAGES.length),
  );

  return (
    <Card className="overflow-hidden border-line bg-gradient-to-br from-slate-950 via-[#0b1526] to-[#0a3038] text-white">
      <div className="grid gap-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <KodaMark size="lg" gradientId="onboarding-mark-gradient" />
            <div>
              <div className="text-[10px] font-black uppercase tracking-[0.16em] text-sky-300">
                First-run setup
              </div>
              <div className="text-xl font-black tracking-tight">
                Launch your trust workspace
              </div>
              <p className="mt-1 max-w-xl text-sm font-medium text-slate-300">
                Connect read-only sources (no lake build required), sync
                evidence, and share auditor-ready proof — same loop agents run
                headlessly.
              </p>
            </div>
          </div>
          <Badge tone={shareable ? "ready" : "attention"}>
            {shareable ? "shareable" : `${progress}% ready`}
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-4">
          {STAGES.map((stage, index) => {
            const Icon = stage.icon;
            const done = index < stageIndex || shareable;
            const active = index === stageIndex && !shareable;
            const href =
              active && currentHref
                ? currentHref
                : stage.id === "connect"
                  ? "/connectors?onboarding=1"
                  : stage.id === "sync"
                    ? "/connectors?onboarding=1"
                    : stage.href;
            return (
              <Link
                key={stage.id}
                href={href}
                className={`rounded-xl border p-3 transition-colors ${
                  active
                    ? "border-sky-400/60 bg-sky-500/10"
                    : done
                      ? "border-emerald-500/30 bg-emerald-500/10"
                      : "border-white/10 bg-white/5 hover:border-white/20"
                }`}
              >
                <div className="flex items-center gap-2">
                  {done ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <Circle
                      className={`h-4 w-4 ${active ? "text-sky-300" : "text-slate-500"}`}
                    />
                  )}
                  <Icon
                    className={`h-4 w-4 ${active ? "text-sky-200" : "text-slate-300"}`}
                  />
                  <span className="text-sm font-black">{stage.label}</span>
                </div>
              </Link>
            );
          })}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] font-black uppercase tracking-wide text-slate-400">
            <span>Blocking progress</span>
            <span>
              {completedBlocking}/{blockingTotal}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#4f7cff] to-[#30c7d2]"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {currentStep && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="min-w-0">
              <div className="text-[10px] font-black uppercase tracking-wide text-sky-300">
                Current step
              </div>
              <div className="font-black text-white">{currentStep.label}</div>
              <p className="mt-1 text-sm text-slate-300">
                {currentStep.detail}
              </p>
            </div>
            {currentHref ? (
              <Button asChild variant="primary">
                <Link href={currentHref}>
                  Continue setup
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : null}
          </div>
        )}
      </div>
    </Card>
  );
}
