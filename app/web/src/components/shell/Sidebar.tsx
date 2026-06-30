"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertOctagon,
  Bot,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  Globe2,
  Layers,
  LayoutDashboard,
  LineChart,
  ListChecks,
  Network,
  Plug,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Zap,
} from "lucide-react";
import { SidebarFooter } from "./SidebarFooter";
import { cn } from "@/lib/utils";
import { usePersistentState } from "@/lib/state/preferences";

interface RailItem {
  href: string;
  label: string;
  Icon: typeof LayoutDashboard;
  badge?: string;
  group: "Trust" | "Workflows" | "Sources" | "Review";
}

const ITEMS: RailItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    Icon: LayoutDashboard,
    badge: "live",
    group: "Trust",
  },
  {
    href: "/poc",
    label: "Launch",
    Icon: Sparkles,
    badge: "POC",
    group: "Trust",
  },
  {
    href: "/demo",
    label: "Demo",
    Icon: Globe2,
    group: "Trust",
  },
  {
    href: "/trust-center",
    label: "Trust center",
    Icon: Sparkles,
    group: "Trust",
  },
  {
    href: "/controls",
    label: "Controls",
    Icon: ShieldCheck,
    group: "Trust",
  },
  { href: "/evidence", label: "Evidence", Icon: FileSearch, group: "Trust" },
  {
    href: "/violations",
    label: "Findings",
    Icon: AlertOctagon,
    group: "Trust",
  },
  {
    href: "/remediation",
    label: "Remediation",
    Icon: ListChecks,
    group: "Workflows",
  },
  { href: "/automation", label: "Workflows", Icon: Zap, group: "Workflows" },
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
    group: "Review",
  },
  {
    href: "/access-reviews",
    label: "Access reviews",
    Icon: UserCheck,
    group: "Review",
  },
  { href: "/graph", label: "Graph", Icon: Network, group: "Review" },
  { href: "/insights", label: "Insights", Icon: LineChart, group: "Review" },
  { href: "/audit-log", label: "Audit log", Icon: Activity, group: "Review" },
  {
    href: "/agents",
    label: "Agent API",
    Icon: Bot,
    badge: "JSON",
    group: "Review",
  },
];

const GROUPS: RailItem["group"][] = ["Trust", "Workflows", "Sources", "Review"];

function isGroupClosed(
  group: RailItem["group"],
  closedGroups: Record<string, boolean>,
) {
  if (group === "Review") {
    return closedGroups[group] !== false;
  }
  return Boolean(closedGroups[group]);
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
      [group]: !isGroupClosed(group, closedGroups),
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
          <span className="px-2 text-[10px] font-black uppercase tracking-[0.18em] text-[#708198]">
            Workbench
          </span>
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
            isGroupClosed(group, closedGroups) && !effectiveCollapsed;
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
