import {
  Activity,
  Bot,
  Bug,
  Database,
  FileClock,
  Fingerprint,
  GitBranch,
  HeartPulse,
  Landmark,
  Layers,
  LockKeyhole,
  Radar,
  Scale,
  ShieldAlert,
  Users,
  Workflow,
} from "lucide-react";

const FAMILIES = {
  identity: { label: "Identity & access", icon: Fingerprint },
  "data-protection": { label: "Data protection", icon: Database },
  "change-management": { label: "Change management", icon: GitBranch },
  governance: { label: "Governance", icon: Landmark },
  detection: { label: "Detection", icon: Radar },
  logging: { label: "Logging", icon: FileClock },
  "vulnerability-management": { label: "Vulnerability management", icon: Bug },
  "third-party-risk": { label: "Third-party risk", icon: Users },
  "risk-management": { label: "Risk management", icon: Scale },
  availability: { label: "Availability", icon: HeartPulse },
  "ai-governance": { label: "AI governance", icon: Bot },
  "incident-response": { label: "Incident response", icon: ShieldAlert },
  privacy: { label: "Privacy", icon: LockKeyhole },
  "controls-operations": { label: "Control operations", icon: Workflow },
  monitoring: { label: "Monitoring", icon: Activity },
};

export function controlFamily(domain: string) {
  return (
    FAMILIES[domain as keyof typeof FAMILIES] ?? {
      label: domain.replaceAll("-", " "),
      icon: Layers,
    }
  );
}

export function ControlFamilyIcon({ domain }: { domain: string }) {
  const { icon: Icon } = controlFamily(domain);
  return (
    <span
      aria-hidden="true"
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600"
    >
      <Icon className="h-[18px] w-[18px]" />
    </span>
  );
}
