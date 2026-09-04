"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowUpRight,
  CheckCircle2,
  DatabaseZap,
  FileCheck2,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";

type StageTone = "cyan" | "blue" | "amber" | "mint";

interface SignalStage {
  label: string;
  title: string;
  detail: string;
  href: string;
  tone: StageTone;
  icon: typeof DatabaseZap;
}

const TONE: Record<StageTone, string> = {
  cyan: "border-cyan-300/25 bg-cyan-300/[0.08] text-cyan-200",
  blue: "border-blue-300/25 bg-blue-300/[0.08] text-blue-200",
  amber: "border-amber-300/25 bg-amber-300/[0.08] text-amber-200",
  mint: "border-emerald-300/25 bg-emerald-300/[0.08] text-emerald-200",
};

function percent(value: number | null | undefined) {
  return value == null
    ? "Awaiting eval"
    : `${Math.round(value * 100)}% passing`;
}

export function TrustSignalFlow({
  sourceCount,
  enabledConnectors,
  connectorCount,
  passRate,
  failingTests,
  openFindings,
  criticalFindings,
  proofReady,
  evidenceCount,
}: {
  sourceCount: number;
  enabledConnectors: number;
  connectorCount: number;
  passRate: number | null | undefined;
  failingTests: number;
  openFindings: number;
  criticalFindings: number;
  proofReady: boolean;
  evidenceCount: number;
}) {
  const reduceMotion = useReducedMotion();
  const stages: SignalStage[] = [
    {
      label: "Collect",
      title: `${enabledConnectors}/${connectorCount} connectors`,
      detail: `${sourceCount} read-only sources`,
      href: "/connectors",
      tone: "cyan",
      icon: DatabaseZap,
    },
    {
      label: "Evaluate",
      title: percent(passRate),
      detail: `${failingTests} failing tests`,
      href: "/controls",
      tone: "blue",
      icon: ShieldCheck,
    },
    {
      label: "Operate",
      title: `${openFindings} open findings`,
      detail: `${criticalFindings} critical`,
      href: "/violations",
      tone: "amber",
      icon: TriangleAlert,
    },
    {
      label: "Prove",
      title: proofReady ? "Proof ready" : "Proof pending",
      detail: `${evidenceCount} evidence rows`,
      href: "/audit-room",
      tone: "mint",
      icon: proofReady ? CheckCircle2 : FileCheck2,
    },
  ];

  return (
    <section
      aria-label="Evidence operating loop"
      className="relative border-t border-white/10 px-4 py-3 sm:px-5"
    >
      <div
        aria-hidden
        className="absolute left-[12%] right-[12%] top-[49px] hidden h-px bg-gradient-to-r from-cyan-300/40 via-blue-300/40 to-emerald-300/40 lg:block"
      />
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <motion.div
              key={stage.label}
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, delay: index * 0.045 }}
              whileHover={
                reduceMotion ? undefined : { y: -3, rotateX: 1.5, scale: 1.01 }
              }
              className="relative z-10 [perspective:800px]"
            >
              <Link
                href={stage.href}
                className={cn(
                  "group flex min-h-[74px] items-center gap-3 rounded-xl border px-3 py-2.5 shadow-[0_12px_30px_rgba(2,6,23,0.14)] backdrop-blur transition-[border-color,background-color,box-shadow] duration-base hover:border-white/35 hover:bg-white/[0.11] hover:shadow-[0_18px_38px_rgba(2,6,23,0.24)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300",
                  TONE[stage.tone],
                )}
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-white/15 bg-slate-950/35 shadow-inner">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">
                    <span aria-hidden>
                      {String(index + 1).padStart(2, "0")} ·{" "}
                    </span>
                    <span>{stage.label}</span>
                  </span>
                  <span className="mt-0.5 block truncate text-sm font-black text-white">
                    {stage.title}
                  </span>
                  <span className="block truncate text-[11px] text-slate-400">
                    {stage.detail}
                  </span>
                </span>
                <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-slate-500 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" />
              </Link>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
