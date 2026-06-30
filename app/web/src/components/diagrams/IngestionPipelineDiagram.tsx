"use client";

import { FlowStrip, type FlowStep } from "./FlowStrip";

const STEPS: FlowStep[] = [
  {
    step: "01",
    title: "Connect read-only",
    detail: "IAM role, GitHub App, Okta token, or lake SELECT grants.",
    tone: "brand",
  },
  {
    step: "02",
    title: "Discover + probe",
    detail: "Validate scope and fingerprint before enablement.",
    tone: "neutral",
  },
  {
    step: "03",
    title: "Sync to bronze",
    detail: "Immutable raw events land in your /lake boundary.",
    tone: "lake",
  },
  {
    step: "04",
    title: "Materialize gold",
    detail: "Silver facts → control posture, violations, readiness.",
    tone: "assess",
  },
  {
    step: "05",
    title: "Operate + share",
    detail: "Dashboard, API, workflows, trust-center links.",
    tone: "share",
  },
];

export function IngestionPipelineDiagram() {
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-black uppercase tracking-wide text-muted">
          Continuous ingestion path
        </span>
        <span className="text-[11px] font-bold text-muted">
          Same loop as Drata/Vanta — evidence stays in your lake
        </span>
      </div>
      <FlowStrip steps={STEPS} />
    </div>
  );
}
