"use client";

import Link from "next/link";
import {
  ClipboardCheck,
  Database,
  FileCheck2,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StageId = "frameworks" | "evidence" | "controls" | "findings" | "proof";

const stages = [
  {
    id: "frameworks",
    label: "Map",
    title: "Framework map",
    detail: "Official controls and mappings define what eval can prove.",
    href: "/frameworks",
    Icon: ClipboardCheck,
  },
  {
    id: "evidence",
    label: "Collect",
    title: "Evidence facts",
    detail: "Connector sync lands normalized, hash-backed evidence.",
    href: "/evidence",
    Icon: Database,
  },
  {
    id: "controls",
    label: "Evaluate",
    title: "Control eval",
    detail: "Deterministic rules produce gold pass/fail posture.",
    href: "/controls",
    Icon: ShieldCheck,
  },
  {
    id: "findings",
    label: "Triage",
    title: "Findings",
    detail: "Failed controls become owner-ready findings.",
    href: "/violations",
    Icon: TriangleAlert,
  },
  {
    id: "proof",
    label: "Prove",
    title: "Proof export",
    detail: "Audit room freezes snapshots and exports reports.",
    href: "/audit-room",
    Icon: FileCheck2,
  },
] as const;

export function TrustPipelineStrip({
  activeStage,
  className,
}: {
  activeStage: StageId;
  className?: string;
}) {
  return (
    <div
      aria-label="Trust pipeline"
      className={cn(
        "overflow-x-auto rounded-xl border border-line bg-white",
        className,
      )}
    >
      <div className="grid min-w-[920px] grid-cols-5 divide-x divide-line">
        {stages.map(({ id, label, title, detail, href, Icon }) => {
          const active = id === activeStage;
          return (
            <Link
              key={id}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "grid min-w-0 gap-2 p-3 text-left transition-colors hover:bg-blue-50/50",
                active ? "bg-blue-50/80" : "bg-white",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg border",
                    active
                      ? "border-brand bg-brand text-white"
                      : "border-line bg-panel text-brand",
                  )}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <Badge tone={active ? "info" : "default"}>{label}</Badge>
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-black text-ink">
                  {title}
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
                  {detail}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
