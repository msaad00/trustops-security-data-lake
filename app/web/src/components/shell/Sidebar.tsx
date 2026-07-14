"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertOctagon,
  Bot,
  BookOpen,
  BrainCircuit,
  Building2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileSearch,
  Globe2,
  Layers,
  LayoutDashboard,
  LineChart,
  KeyRound,
  ListChecks,
  Network,
  Plug,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Rocket,
  UserCheck,
  Zap,
} from "lucide-react";
import { SidebarFooter } from "./SidebarFooter";
import { KodaLogo } from "@/components/brand/TrustOpsLogo";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";
import { usePersistentState } from "@/lib/state/preferences";

interface RailItem {
  href: string;
  label: string;
  Icon: typeof LayoutDashboard;
  badge?: string;
  group: "Operate" | "Sources" | "Automate" | "Governance" | "Setup";
}

const ITEMS: RailItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    Icon: LayoutDashboard,
    badge: "live",
    group: "Operate",
  },
  {
    href: "/onboarding",
    label: "Onboarding",
    Icon: Rocket,
    badge: "start",
    group: "Setup",
  },
  {
    href: "/poc",
    label: "Launch",
    Icon: Sparkles,
    badge: "POC",
    group: "Setup",
  },
  {
    href: "/demo",
    label: "Demo",
    Icon: Globe2,
    group: "Setup",
  },
  {
    href: "/deploy",
    label: "Deploy",
    Icon: BookOpen,
    group: "Setup",
  },
  {
    href: "/trust-center",
    label: "Trust center",
    Icon: Sparkles,
    group: "Governance",
  },
  {
    href: "/controls",
    label: "Controls",
    Icon: ShieldCheck,
    group: "Operate",
  },
  { href: "/evidence", label: "Evidence", Icon: FileSearch, group: "Operate" },
  {
    href: "/violations",
    label: "Findings",
    Icon: AlertOctagon,
    group: "Operate",
  },
  {
    href: "/remediation",
    label: "Remediation",
    Icon: ListChecks,
    group: "Operate",
  },
  { href: "/automation", label: "Workflows", Icon: Zap, group: "Automate" },
  { href: "/connectors", label: "Connectors", Icon: Plug, group: "Sources" },
  {
    href: "/frameworks",
    label: "Frameworks",
    Icon: BookOpen,
    group: "Sources",
  },
  {
    href: "/crosswalk",
    label: "Crosswalk",
    Icon: Layers,
    group: "Sources",
  },
  {
    href: "/risks",
    label: "Risk register",
    Icon: ShieldAlert,
    group: "Governance",
  },
  {
    href: "/access-reviews",
    label: "Access reviews",
    Icon: UserCheck,
    group: "Governance",
  },
  {
    href: "/policies",
    label: "Policies",
    Icon: BookOpen,
    group: "Governance",
  },
  {
    href: "/vendor-risk",
    label: "Vendor risk",
    Icon: Building2,
    group: "Governance",
  },
  {
    href: "/auth",
    label: "Access",
    Icon: KeyRound,
    group: "Governance",
  },
  { href: "/graph", label: "Graph", Icon: Network, group: "Operate" },
  { href: "/insights", label: "Insights", Icon: LineChart, group: "Operate" },
  {
    href: "/audit-room",
    label: "Audit room",
    Icon: ClipboardCheck,
    group: "Governance",
  },
  {
    href: "/ai-governance",
    label: "AI governance",
    Icon: BrainCircuit,
    badge: "live",
    group: "Governance",
  },
  {
    href: "/audit-log",
    label: "Audit log",
    Icon: Activity,
    group: "Governance",
  },
  {
    href: "/agents",
    label: "Agent harness",
    Icon: Bot,
    badge: "JSON",
    group: "Automate",
  },
];

const GROUPS: RailItem["group"][] = [
  "Operate",
  "Sources",
  "Automate",
  "Governance",
  "Setup",
];

function isGroupClosed(
  group: RailItem["group"],
  closedGroups: Record<string, boolean>,
  activeGroup: RailItem["group"],
) {
  if (closedGroups[group] !== undefined) return closedGroups[group];
  return group !== activeGroup;
}

export function Sidebar() {
  const pathname = usePathname() ?? "/dashboard";
  const [collapsed, setCollapsed] = usePersistentState(
    "trustops:sidebar:collapsed",
    false,
  );
  const [compactViewport, setCompactViewport] = useState(false);
  const [closedGroups, setClosedGroups] = usePersistentState<
    Record<string, boolean>
  >("trustops:sidebar:closed-groups", {});
  const effectiveCollapsed = collapsed || compactViewport;
  const activeGroup =
    ITEMS.find(
      (item) => pathname === item.href || pathname.startsWith(item.href + "/"),
    )?.group ?? "Operate";

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const update = () => setCompactViewport(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const toggleGroup = (group: RailItem["group"]) => {
    setClosedGroups({
      ...closedGroups,
      [group]: !isGroupClosed(group, closedGroups, activeGroup),
    });
  };

  return (
    <aside
      className={cn(
        "grid grid-rows-[auto_1fr_auto] border-r border-railLine bg-rail text-slate-300 transition-[width]",
        effectiveCollapsed ? "w-[64px]" : "w-[248px]",
      )}
    >
      <div className="flex items-center justify-between border-b border-railLine p-2.5">
        {!effectiveCollapsed && (
          <KodaLogo
            href="/dashboard"
            inverted
            markSize="sm"
            subtitle={BRAND.consoleSubtitle}
            wordmarkClassName="max-w-[140px]"
            gradientId="trustops-sidebar-gradient"
          />
        )}
        <button
          type="button"
          onClick={() => {
            if (!compactViewport) setCollapsed(!collapsed);
          }}
          aria-label={
            compactViewport
              ? "Sidebar is compact on small screens"
              : effectiveCollapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
          }
          className="ml-auto grid h-7 w-7 place-items-center rounded-md text-[#9aa9bc] hover:bg-[#152030]"
        >
          {effectiveCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <div className="overflow-y-auto p-2.5">
        {GROUPS.map((group) => {
          const isClosed =
            isGroupClosed(group, closedGroups, activeGroup) &&
            !effectiveCollapsed;
          const groupItems = ITEMS.filter((i) => i.group === group);
          return (
            <div key={group} className="mb-3">
              {!effectiveCollapsed ? (
                <button
                  type="button"
                  onClick={() => toggleGroup(group)}
                  className="flex w-full items-center justify-between px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.08em] text-[#708198] hover:text-[#bcc8d8]"
                >
                  <span>{group}</span>
                  {isClosed ? (
                    <ChevronRight className="h-3 w-3" />
                  ) : (
                    <ChevronLeft className="h-3 w-3 rotate-180" />
                  )}
                </button>
              ) : (
                <div className="mb-2 px-1 text-center text-[9px] font-black uppercase tracking-[0.12em] text-[#5b6a7e]">
                  {group.charAt(0)}
                </div>
              )}
              {!isClosed && (
                <div className="grid gap-1">
                  {groupItems.map(({ href, label, Icon, badge }) => {
                    const active =
                      pathname === href || pathname.startsWith(href + "/");
                    return (
                      <Link
                        key={href}
                        href={href}
                        title={effectiveCollapsed ? label : undefined}
                        className={cn(
                          "flex items-center gap-2 rounded-lg border px-2.5 text-[13px] font-extrabold transition-colors",
                          effectiveCollapsed
                            ? "h-9 justify-center px-0"
                            : "h-9 justify-between",
                          active
                            ? "border-[#31435c] bg-[#172436] text-white"
                            : "border-transparent text-[#c6d1df] hover:bg-[#152030]",
                        )}
                      >
                        <span
                          className={cn(
                            "flex items-center gap-2.5",
                            effectiveCollapsed ? "justify-center" : "",
                          )}
                        >
                          <span
                            className={cn(
                              "grid place-items-center rounded-lg",
                              effectiveCollapsed ? "h-7 w-7" : "h-6 w-6",
                              active
                                ? "bg-[#eff6ff] text-[#1d4ed8]"
                                : "bg-[#1d2b3d] text-[#9cc2ff]",
                            )}
                          >
                            <Icon className="h-4 w-4" />
                          </span>
                          {!effectiveCollapsed && label}
                        </span>
                        {!effectiveCollapsed && badge && (
                          <b className="rounded-full bg-[#26364b] px-1.5 py-0.5 text-[10px] text-[#cfe0f5]">
                            {badge}
                          </b>
                        )}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <SidebarFooter collapsed={effectiveCollapsed} />
    </aside>
  );
}
