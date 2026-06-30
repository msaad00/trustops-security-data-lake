"use client";

import { useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";

const LABEL: Record<string, string> = {
  dashboard: "Dashboard",
  controls: "Controls",
  violations: "Violations",
  evidence: "Evidence",
  automation: "Workflows",
  graph: "Graph",
  "audit-log": "Audit log",
  connectors: "Connectors",
  frameworks: "Frameworks",
  crosswalk: "Crosswalk",
  "trust-center": "Trust center",
  agents: "Agent API",
  deploy: "Deploy",
  demo: "Demo",
  poc: "Launch",
};

export function Breadcrumbs() {
  const pathname = usePathname() ?? "/";

  const crumbs = useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    return segments.map((segment, idx) => ({
      segment,
      label: LABEL[segment] ?? segment,
      href: "/" + segments.slice(0, idx + 1).join("/"),
    }));
  }, [pathname]);

  if (crumbs.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex min-w-0 items-center gap-1.5 border-b border-line bg-white/80 px-4 py-2 text-xs text-muted backdrop-blur sm:px-5 lg:px-7"
    >
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1 rounded px-1 py-0.5 font-extrabold text-muted hover:bg-slate-100 hover:text-ink"
      >
        <Home className="h-3 w-3" />
        TrustOps
      </Link>
      {crumbs.map((crumb, idx) => (
        <span key={crumb.href} className="inline-flex items-center gap-1.5">
          <ChevronRight className="h-3 w-3 text-muted/60" />
          {idx === crumbs.length - 1 ? (
            <span className="font-black text-ink">{crumb.label}</span>
          ) : (
            <Link
              href={crumb.href}
              className="rounded px-1 py-0.5 font-extrabold hover:bg-slate-100 hover:text-ink"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
