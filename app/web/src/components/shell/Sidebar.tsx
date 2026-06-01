"use client";

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
  Layers,
  LayoutDashboard,
  LineChart,
  ListChecks,
  Network,
  Plug,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
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
  group: "Operate" | "Configure";
}

const ITEMS: RailItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    Icon: LayoutDashboard,
    badge: "live",
    group: "Operate",
  },
  { href: "/controls", label: "Controls", Icon: ShieldCheck, group: "Operate" },
  {
    href: "/violations",
    label: "Violations",
    Icon: AlertOctagon,
    group: "Operate",
  },
  {
    href: "/remediation",
    label: "Remediation",
    Icon: ListChecks,
    group: "Operate",
  },
  {
    href: "/risks",
    label: "Risk register",
    Icon: ShieldAlert,
    group: "Operate",
  },
  { href: "/evidence", label: "Evidence", Icon: FileSearch, group: "Operate" },
  { href: "/automation", label: "Workflows", Icon: Zap, group: "Operate" },
  { href: "/graph", label: "Graph", Icon: Network, group: "Operate" },
  { href: "/insights", label: "Insights", Icon: LineChart, group: "Operate" },
  { href: "/audit-log", label: "Audit log", Icon: Activity, group: "Operate" },
  { href: "/connectors", label: "Connectors", Icon: Plug, group: "Configure" },
  {
    href: "/frameworks",
    label: "Frameworks",
    Icon: BookOpen,
    group: "Configure",
  },
  { href: "/crosswalk", label: "Crosswalk", Icon: Layers, group: "Configure" },
  {
    href: "/trust-center",
    label: "Trust center",
    Icon: Sparkles,
    group: "Configure",
  },
  {
    href: "/agents",
    label: "Agent API",
    Icon: Bot,
    badge: "JSON",
    group: "Configure",
  },
];

const GROUPS: RailItem["group"][] = ["Operate", "Configure"];

export function Sidebar() {
  const pathname = usePathname() ?? "/dashboard";
  const [collapsed, setCollapsed] = usePersistentState(
    "trustops:sidebar:collapsed",
    false,
  );
  const [closedGroups, setClosedGroups] = usePersistentState<
    Record<string, boolean>
  >("trustops:sidebar:closed-groups", {});

  const toggleGroup = (group: string) => {
    setClosedGroups({ ...closedGroups, [group]: !closedGroups[group] });
  };

  return (
    <aside
      className={cn(
        "grid grid-rows-[auto_1fr_auto] border-r border-railLine bg-rail text-slate-300 transition-[width]",
        collapsed ? "w-[72px]" : "w-[286px]",
      )}
    >
      <div className="flex items-center justify-between border-b border-railLine p-3">
        {!collapsed && (
          <span className="px-2 text-[10px] font-black uppercase tracking-[0.18em] text-[#708198]">
            Workbench
          </span>
        )}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="ml-auto grid h-7 w-7 place-items-center rounded-md text-[#9aa9bc] hover:bg-[#152030]"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <div className="overflow-y-auto p-3">
        {GROUPS.map((group) => {
          const isClosed = Boolean(closedGroups[group]) && !collapsed;
          const groupItems = ITEMS.filter((i) => i.group === group);
          return (
            <div key={group} className="mb-3">
              {!collapsed ? (
                <button
                  type="button"
                  onClick={() => toggleGroup(group)}
                  className="flex w-full items-center justify-between px-3 py-2 text-[11px] font-black uppercase tracking-[0.08em] text-[#708198] hover:text-[#bcc8d8]"
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
                        title={collapsed ? label : undefined}
                        className={cn(
                          "flex items-center gap-2.5 rounded-xl border px-3 text-[14px] font-extrabold transition-colors",
                          collapsed
                            ? "h-10 justify-center px-0"
                            : "h-[42px] justify-between",
                          active
                            ? "border-[#31435c] bg-[#172436] text-white"
                            : "border-transparent text-[#c6d1df] hover:bg-[#152030]",
                        )}
                      >
                        <span
                          className={cn(
                            "flex items-center gap-2.5",
                            collapsed ? "justify-center" : "",
                          )}
                        >
                          <span
                            className={cn(
                              "grid place-items-center rounded-lg",
                              collapsed ? "h-7 w-7" : "h-[26px] w-[26px]",
                              active
                                ? "bg-[#eff6ff] text-[#1d4ed8]"
                                : "bg-[#1d2b3d] text-[#9cc2ff]",
                            )}
                          >
                            <Icon className="h-4 w-4" />
                          </span>
                          {!collapsed && label}
                        </span>
                        {!collapsed && badge && (
                          <b className="rounded-full bg-[#26364b] px-2 py-0.5 text-[11px] text-[#cfe0f5]">
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

      <SidebarFooter collapsed={collapsed} />
    </aside>
  );
}
