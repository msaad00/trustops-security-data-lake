"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ActivityIcon,
  AlertOctagon,
  Bot,
  BookOpen,
  Camera,
  FileSearch,
  LayoutDashboard,
  Layers,
  Network,
  Plug,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api/client";
import type {
  ControlPosture,
  NormalizedEvent,
  Violation,
  Workflow as WorkflowRow,
} from "@/lib/api/types";

interface PaletteItem {
  id: string;
  group:
    | "Actions"
    | "Routes"
    | "Controls"
    | "Violations"
    | "Evidence"
    | "Workflows";
  label: string;
  subtitle?: string;
  href?: string;
  run?: () => void;
  Icon: typeof LayoutDashboard;
}

const ROUTE_ITEMS: PaletteItem[] = [
  {
    id: "r:dashboard",
    group: "Routes",
    label: "Dashboard",
    href: "/dashboard",
    Icon: LayoutDashboard,
  },
  {
    id: "r:controls",
    group: "Routes",
    label: "Controls",
    href: "/controls",
    Icon: ShieldCheck,
  },
  {
    id: "r:violations",
    group: "Routes",
    label: "Findings",
    href: "/violations",
    Icon: AlertOctagon,
  },
  {
    id: "r:risks",
    group: "Routes",
    label: "Risk register",
    href: "/risks",
    Icon: ShieldAlert,
  },
  {
    id: "r:evidence",
    group: "Routes",
    label: "Evidence",
    href: "/evidence",
    Icon: FileSearch,
  },
  {
    id: "r:automation",
    group: "Routes",
    label: "Workflows",
    href: "/automation",
    Icon: Zap,
  },
  {
    id: "r:graph",
    group: "Routes",
    label: "Graph",
    href: "/graph",
    Icon: Network,
  },
  {
    id: "r:audit-log",
    group: "Routes",
    label: "Audit log",
    href: "/audit-log",
    Icon: ActivityIcon,
  },
  {
    id: "r:connectors",
    group: "Routes",
    label: "Connectors",
    href: "/connectors",
    Icon: Plug,
  },
  {
    id: "r:frameworks",
    group: "Routes",
    label: "Frameworks",
    href: "/frameworks",
    Icon: BookOpen,
  },
  {
    id: "r:crosswalk",
    group: "Routes",
    label: "Crosswalk diagnostics",
    href: "/crosswalk",
    Icon: Layers,
  },
  {
    id: "r:trust-center",
    group: "Routes",
    label: "Trust center",
    href: "/trust-center",
    Icon: Sparkles,
  },
  {
    id: "r:agents",
    group: "Routes",
    label: "Agent API",
    href: "/agents",
    Icon: Bot,
  },
];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSnapshot?: () => void;
  onRefresh?: () => void;
}

export function CommandPalette({
  open,
  onOpenChange,
  onSnapshot,
  onRefresh,
}: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [controls, setControls] = useState<ControlPosture[]>([]);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [evidence, setEvidence] = useState<NormalizedEvent[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRow[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Lazy-load the searchable indexes when first opened.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    Promise.allSettled([
      api.controls().then((r) => setControls(r.controls ?? [])),
      api.violations().then((r) => setViolations(r.violations ?? [])),
      api.evidence().then((r) => setEvidence(r.evidence ?? [])),
      api.listWorkflows().then((r) => setWorkflows(r.workflows ?? [])),
    ]).catch(() => undefined);
  }, [open]);

  // Focus the input every time the dialog opens.
  useEffect(() => {
    if (open) {
      const handle = window.setTimeout(() => inputRef.current?.focus(), 50);
      return () => window.clearTimeout(handle);
    }
  }, [open]);

  const items = useMemo<PaletteItem[]>(() => {
    const actions: PaletteItem[] = [];
    if (onSnapshot) {
      actions.push({
        id: "a:snapshot",
        group: "Actions",
        label: "Create assessment snapshot",
        subtitle: "Freeze current posture for audit / JIT review",
        run: onSnapshot,
        Icon: Camera,
      });
    }
    if (onRefresh) {
      actions.push({
        id: "a:refresh",
        group: "Actions",
        label: "Refresh data",
        subtitle: "Re-read posture from the assessment lake",
        run: onRefresh,
        Icon: RefreshCw,
      });
    }
    const dynamic: PaletteItem[] = [
      ...controls.map<PaletteItem>((c) => ({
        id: `c:${c.control_id}`,
        group: "Controls",
        label: c.control_id,
        subtitle: c.title,
        href: `/controls?id=${encodeURIComponent(c.control_id)}`,
        Icon: ShieldCheck,
      })),
      ...violations.map<PaletteItem>((v) => ({
        id: `v:${v.violation_id}`,
        group: "Violations",
        label: v.violation_id,
        subtitle: `${v.severity} · ${v.asset_id}`,
        href: `/violations?id=${encodeURIComponent(v.violation_id)}`,
        Icon: AlertOctagon,
      })),
      ...evidence.map<PaletteItem>((e) => ({
        id: `e:${e.event_id}`,
        group: "Evidence",
        label: e.event_id,
        subtitle: `${e.source} · ${e.asset_id}`,
        href: `/evidence?id=${encodeURIComponent(e.event_id)}`,
        Icon: FileSearch,
      })),
      ...workflows.map<PaletteItem>((w) => ({
        id: `w:${w.workflow_id}`,
        group: "Workflows",
        label: w.name,
        subtitle: `${w.workflow_id} · v${w.version}`,
        href: `/automation?id=${encodeURIComponent(w.workflow_id)}`,
        Icon: Workflow,
      })),
    ];
    const all = [...actions, ...ROUTE_ITEMS, ...dynamic];
    if (!query) return all.slice(0, 60);
    const lower = query.toLowerCase();
    return all
      .filter((item) =>
        `${item.label} ${item.subtitle ?? ""} ${item.group}`
          .toLowerCase()
          .includes(lower),
      )
      .slice(0, 60);
  }, [controls, violations, evidence, workflows, query, onSnapshot, onRefresh]);

  // Reset active index when filter changes.
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const grouped = useMemo(() => {
    const out = new Map<PaletteItem["group"], PaletteItem[]>();
    for (const item of items) {
      const list = out.get(item.group) ?? [];
      list.push(item);
      out.set(item.group, list);
    }
    return out;
  }, [items]);

  const go = (item: PaletteItem) => {
    onOpenChange(false);
    if (item.run) {
      item.run();
    } else if (item.href) {
      router.push(item.href);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[14%] z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-2xl bg-white shadow-hero">
          <Dialog.Title className="sr-only">Search</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search controls, violations, evidence, workflows, and routes.
          </Dialog.Description>
          <div className="flex items-center gap-3 border-b border-line px-4 py-3">
            <Search className="h-4 w-4 text-muted" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setActiveIndex((i) => Math.min(i + 1, items.length - 1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setActiveIndex((i) => Math.max(i - 1, 0));
                } else if (e.key === "Enter") {
                  e.preventDefault();
                  const target = items[activeIndex];
                  if (target) go(target);
                }
              }}
              placeholder="Search controls, violations, evidence, workflows, routes…"
              className="flex-1 bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
            />
            <kbd className="rounded border border-line bg-slate-50 px-1.5 py-0.5 text-[10px] font-bold text-muted">
              esc
            </kbd>
          </div>
          <div className="max-h-[60vh] overflow-auto p-2">
            {items.length === 0 && (
              <div className="px-3 py-8 text-center text-sm text-muted">
                No matches.
              </div>
            )}
            {Array.from(grouped.entries()).map(([group, list]) => (
              <div key={group} className="grid gap-0.5 px-1 pb-2">
                <div className="px-2 pb-1 pt-3 text-[10px] font-black uppercase tracking-wider text-muted">
                  {group}
                </div>
                {list.map((item) => {
                  const idx = items.indexOf(item);
                  const active = idx === activeIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onMouseEnter={() => setActiveIndex(idx)}
                      onClick={() => go(item)}
                      className={[
                        "grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm",
                        active
                          ? "bg-ink text-white"
                          : "text-ink hover:bg-slate-50",
                      ].join(" ")}
                    >
                      <item.Icon
                        className={
                          active
                            ? "h-4 w-4 text-brand-cyan"
                            : "h-4 w-4 text-muted"
                        }
                      />
                      <span className="min-w-0">
                        <span className="block truncate font-extrabold">
                          {item.label}
                        </span>
                        {item.subtitle && (
                          <span
                            className={[
                              "block truncate text-[11px]",
                              active ? "text-slate-300" : "text-muted",
                            ].join(" ")}
                          >
                            {item.subtitle}
                          </span>
                        )}
                      </span>
                      <kbd
                        className={[
                          "rounded border px-1.5 py-0.5 text-[10px] font-bold",
                          active
                            ? "border-slate-600 bg-slate-800 text-slate-200"
                            : "border-line bg-white text-muted",
                        ].join(" ")}
                      >
                        ↵
                      </kbd>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-line bg-slate-50 px-4 py-2 text-[11px] text-muted">
            <span>
              <kbd className="rounded border border-line bg-white px-1.5 py-0.5 font-bold">
                ↑↓
              </kbd>{" "}
              navigate{" "}
              <kbd className="rounded border border-line bg-white px-1.5 py-0.5 font-bold">
                ↵
              </kbd>{" "}
              open{" "}
              <kbd className="rounded border border-line bg-white px-1.5 py-0.5 font-bold">
                esc
              </kbd>{" "}
              close
            </span>
            <span>{items.length} matches</span>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
