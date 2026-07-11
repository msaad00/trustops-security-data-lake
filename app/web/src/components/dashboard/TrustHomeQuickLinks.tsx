"use client";

import Link from "next/link";
import {
  ClipboardCheck,
  GitBranch,
  Plug,
  ShieldCheck,
  TrendingUp,
  Workflow,
} from "lucide-react";

const LINKS = [
  {
    href: "/audit-room",
    label: "Audit room",
    icon: ClipboardCheck,
  },
  {
    href: "/evidence",
    label: "Evidence",
    icon: ShieldCheck,
  },
  {
    href: "/insights",
    label: "Insights",
    icon: TrendingUp,
  },
  {
    href: "/automation",
    label: "Workflows",
    icon: Workflow,
  },
  {
    href: "/connectors",
    label: "Connectors",
    icon: Plug,
  },
  {
    href: "/graph",
    label: "Repo graph",
    icon: GitBranch,
  },
] as const;

export function TrustHomeQuickLinks() {
  return (
    <nav
      aria-label="Trust Home shortcuts"
      className="flex snap-x snap-mandatory gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:thin]"
    >
      {LINKS.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className="inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-black text-ink transition-colors hover:border-brand hover:text-brand"
        >
          <Icon className="h-3.5 w-3.5" aria-hidden />
          {label}
        </Link>
      ))}
    </nav>
  );
}
