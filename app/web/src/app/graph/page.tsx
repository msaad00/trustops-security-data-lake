"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  Download,
  Filter,
  GitBranch,
  Layout,
  Network,
  Route,
  Search,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import {
  GraphCanvas,
  type ImperativeRef,
  type LayoutDir,
} from "@/components/graph/GraphCanvas";
import { useComplianceGraph, useRepositoryGraph } from "@/lib/api/hooks";
import type { GraphNode, GraphNodeKind } from "@/lib/api/types";

const COMPLIANCE_KINDS: GraphNodeKind[] = [
  "framework",
  "control",
  "evidence_type",
  "asset",
];

const REPO_KINDS: GraphNodeKind[] = [
  "repository",
  "directory",
  "language",
  "evidence_signal",
  "governance_signal",
  "signal_gap",
  "workflow",
  "dependency_manifest",
  "ownership_file",
  "security_file",
  "file",
  "principal",
  "team",
  "review_rule",
  "status_check",
  "workflow_permission",
  "evidence",
  "control",
];

const KIND_LABEL: Record<GraphNodeKind, string> = {
  framework: "Frameworks",
  control: "Controls",
  evidence_type: "Evidence types",
  asset: "Assets",
  repository: "Repositories",
  directory: "Directories",
  language: "Languages",
  evidence_signal: "Evidence signals",
  governance_signal: "Governance signals",
  signal_gap: "Signal gaps",
  workflow: "Workflows",
  dependency_manifest: "Dependencies",
  ownership_file: "Ownership files",
  security_file: "Security files",
  file: "Files",
  principal: "Principals",
  team: "Teams",
  review_rule: "Review rules",
  status_check: "Status checks",
  workflow_permission: "Workflow permissions",
  evidence: "Evidence refs",
};

const KIND_TONE: Record<
  GraphNodeKind,
  "info" | "ready" | "attention" | "critical"
> = {
  framework: "info",
  control: "ready",
  evidence_type: "attention",
  asset: "critical",
  repository: "info",
  directory: "ready",
  language: "ready",
  evidence_signal: "attention",
  governance_signal: "info",
  signal_gap: "critical",
  workflow: "attention",
  dependency_manifest: "attention",
  ownership_file: "ready",
  security_file: "ready",
  file: "info",
  principal: "critical",
  team: "info",
  review_rule: "ready",
  status_check: "ready",
  workflow_permission: "attention",
  evidence: "info",
};

const KIND_SWATCH: Record<GraphNodeKind, string> = {
  framework: "#4f7cff",
  control: "#16b364",
  evidence_type: "#f79009",
  asset: "#7a35ff",
  repository: "#0ea5e9",
  directory: "#64748b",
  language: "#16b364",
  evidence_signal: "#f79009",
  governance_signal: "#2563eb",
  signal_gap: "#dc2626",
  workflow: "#7c3aed",
  dependency_manifest: "#c2410c",
  ownership_file: "#0891b2",
  security_file: "#059669",
  file: "#94a3b8",
  principal: "#be123c",
  team: "#4338ca",
  review_rule: "#10b981",
  status_check: "#22c55e",
  workflow_permission: "#f59e0b",
  evidence: "#475569",
};

const LAYOUT_LABEL: Record<LayoutDir, string> = {
  LR: "Left → Right",
  TB: "Top → Bottom",
  BT: "Bottom → Top",
};

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function GraphPage() {
  const complianceGraph = useComplianceGraph();
  const repoGraph = useRepositoryGraph();
  const [graphMode, setGraphMode] = useState<"compliance" | "repository">(
    "compliance",
  );
  const activeKinds =
    graphMode === "compliance" ? COMPLIANCE_KINDS : REPO_KINDS;
  const graph = graphMode === "compliance" ? complianceGraph : repoGraph;
  const [visible, setVisible] = useState<Set<GraphNodeKind>>(
    new Set(activeKinds),
  );
  const [layout, setLayout] = useState<LayoutDir>("LR");
  const [filterOwner, setFilterOwner] = useState("");
  const [filterEnvironment, setFilterEnvironment] = useState("");
  const [filterFramework, setFilterFramework] = useState("");
  const [search, setSearch] = useState("");
  const [pathMode, setPathMode] = useState<null | "from" | "to">(null);
  const [pathFrom, setPathFrom] = useState<string | null>(null);
  const [pathTo, setPathTo] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const canvasRef = useRef<ImperativeRef | null>(null);

  useEffect(() => {
    setVisible(new Set(activeKinds));
    setSelected(null);
    clearPath();
  }, [graphMode]);

  const data = graph.data;
  const counts = useMemo(
    () => (data?.counts ?? {}) as Partial<Record<GraphNodeKind, number>>,
    [data],
  );

  // Facet options derived from graph data so the rail only shows real values.
  const owners = useMemo(
    () =>
      Array.from(
        new Set(
          (data?.nodes ?? []).map((n) => n.owner).filter(Boolean) as string[],
        ),
      ).sort(),
    [data],
  );
  const environments = useMemo(
    () =>
      Array.from(
        new Set(
          (data?.nodes ?? [])
            .map((n) => n.environment)
            .filter(Boolean) as string[],
        ),
      ).sort(),
    [data],
  );
  const frameworks = useMemo(
    () =>
      Array.from(
        new Set(
          (data?.nodes ?? [])
            .map((n) => n.framework_id)
            .filter((id): id is string => Boolean(id)),
        ),
      ).sort(),
    [data],
  );

  const toggle = (kind: GraphNodeKind) => {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  };

  // Intercept node selection when path-trace mode is armed, otherwise behave
  // as a normal selection.
  const handleSelect = (node: GraphNode | null) => {
    setSelected(node);
    if (!node) return;
    if (pathMode === "from") {
      setPathFrom(node.id);
      setPathMode("to");
    } else if (pathMode === "to") {
      setPathTo(node.id);
      setPathMode(null);
    }
  };

  const clearPath = () => {
    setPathFrom(null);
    setPathTo(null);
    setPathMode(null);
  };

  const exportJSON = () => {
    const payload = canvasRef.current?.toJSON();
    if (!payload) return;
    downloadBlob(
      `trustops-graph-${Date.now()}.json`,
      new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      }),
    );
  };

  const exportSVG = () => {
    const svg = canvasRef.current?.toSVG();
    if (!svg) return;
    downloadBlob(
      `trustops-graph-${Date.now()}.svg`,
      new Blob([svg], { type: "image/svg+xml" }),
    );
  };

  // Esc cancels path-trace mode.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && pathMode) setPathMode(null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pathMode]);

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Graph"
        title={
          graphMode === "compliance"
            ? "Framework → control → evidence → asset"
            : "Repository topology and governance"
        }
        description={
          graphMode === "compliance"
            ? "Every framework loaded, the controls under it, the evidence types those controls require, and the assets covered. Use the rail to filter, search, toggle layouts, trace a path between any two nodes, or export the view."
            : "Public repo audit and authenticated governance evidence rendered as repositories, code structure, workflows, owners, required reviews, status checks, controls, and evidence refs. Public-mode gaps stay explicit."
        }
        actions={
          <Badge tone="info">
            <Network className="mr-1 h-3 w-3" />{" "}
            {data
              ? `${data.nodes.length} nodes / ${data.edges.length} edges`
              : "loading"}
          </Badge>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 p-3">
          <div className="inline-flex items-center gap-1 rounded-lg border border-line bg-white p-0.5">
            {(["compliance", "repository"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setGraphMode(mode)}
                className={[
                  "inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-black",
                  graphMode === mode
                    ? "bg-ink text-white"
                    : "text-slate-600 hover:bg-slate-50",
                ].join(" ")}
              >
                {mode === "repository" ? (
                  <GitBranch className="h-3.5 w-3.5" />
                ) : (
                  <Network className="h-3.5 w-3.5" />
                )}
                {mode === "repository" ? "Repository" : "Compliance"}
              </button>
            ))}
          </div>
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes (label, subtitle, owner)…"
              className="w-full rounded-lg border border-line bg-white py-2 pl-9 pr-8 text-xs focus:outline-none focus:ring-1 focus:ring-brand"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 grid h-5 w-5 -translate-y-1/2 place-items-center rounded text-muted hover:bg-slate-100"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="inline-flex items-center gap-1 rounded-lg border border-line bg-white p-0.5">
            <Layout className="ml-1.5 h-3.5 w-3.5 text-muted" />
            {(["LR", "TB", "BT"] as LayoutDir[]).map((dir) => (
              <button
                key={dir}
                type="button"
                onClick={() => setLayout(dir)}
                className={[
                  "rounded-md px-2 py-1 text-[11px] font-black uppercase tracking-wide",
                  layout === dir
                    ? "bg-ink text-white"
                    : "text-slate-600 hover:bg-slate-50",
                ].join(" ")}
                title={LAYOUT_LABEL[dir]}
              >
                {dir}
              </button>
            ))}
          </div>
          <Button
            variant={pathMode ? "primary" : "default"}
            size="sm"
            onClick={() => {
              if (pathFrom || pathTo) {
                clearPath();
              } else {
                setPathMode("from");
              }
            }}
            title="Click two nodes to highlight the shortest path between them"
          >
            <Route className="h-3.5 w-3.5" />
            {pathFrom && pathTo
              ? "Clear path"
              : pathMode === "from"
                ? "Pick start node"
                : pathMode === "to"
                  ? "Pick end node"
                  : "Trace path"}
          </Button>
          <Button variant="default" size="sm" onClick={exportSVG}>
            <ArrowDownToLine className="h-3.5 w-3.5" /> SVG
          </Button>
          <Button variant="default" size="sm" onClick={exportJSON}>
            <Download className="h-3.5 w-3.5" /> JSON
          </Button>
        </div>
      </Card>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[240px_minmax(0,1fr)]">
        <Card className="max-h-[min(680px,calc(100dvh-300px))] min-h-[520px] overflow-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Filter className="h-4 w-4 text-muted" /> Layers + facets
            </CardTitle>
            <CardDescription>
              Persistent filters drive every other view.
            </CardDescription>
          </CardHeader>
          <div className="grid gap-3 p-4 pt-0">
            <section>
              <div className="mb-2 text-[11px] font-black uppercase tracking-wide text-muted">
                Layers
              </div>
              <div className="grid gap-1">
                {activeKinds.map((kind) => {
                  const on = visible.has(kind);
                  return (
                    <button
                      key={kind}
                      type="button"
                      onClick={() => toggle(kind)}
                      className={[
                        "grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-[11px] font-extrabold",
                        on
                          ? "border-ink bg-white text-ink"
                          : "border-line bg-slate-50 text-muted hover:border-brand",
                      ].join(" ")}
                    >
                      <span
                        className="h-3 w-3 rounded"
                        style={{ background: KIND_SWATCH[kind] }}
                      />
                      <span>{KIND_LABEL[kind]}</span>
                      <Badge tone={KIND_TONE[kind]}>{counts[kind] ?? 0}</Badge>
                    </button>
                  );
                })}
              </div>
            </section>

            <section>
              <div className="mb-2 text-[11px] font-black uppercase tracking-wide text-muted">
                Framework
              </div>
              <select
                value={filterFramework}
                onChange={(e) => setFilterFramework(e.target.value)}
                className="w-full rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="">All frameworks</option>
                {frameworks.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </section>

            <section>
              <div className="mb-2 text-[11px] font-black uppercase tracking-wide text-muted">
                Owner
              </div>
              <select
                value={filterOwner}
                onChange={(e) => setFilterOwner(e.target.value)}
                className="w-full rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="">All owners</option>
                {owners.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </section>

            <section>
              <div className="mb-2 text-[11px] font-black uppercase tracking-wide text-muted">
                Environment
              </div>
              <select
                value={filterEnvironment}
                onChange={(e) => setFilterEnvironment(e.target.value)}
                className="w-full rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="">All environments</option>
                {environments.map((env) => (
                  <option key={env} value={env}>
                    {env}
                  </option>
                ))}
              </select>
            </section>

            <section className="rounded-xl border border-line bg-slate-50/60 p-3 text-[11px] text-muted">
              <div className="mb-1 font-black uppercase tracking-wide text-muted">
                Legend
              </div>
              <div className="grid gap-1">
                {activeKinds.map((kind) => (
                  <div key={kind} className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded"
                      style={{ background: KIND_SWATCH[kind] }}
                    />
                    <span className="text-ink">{KIND_LABEL[kind]}</span>
                  </div>
                ))}
                <div className="mt-1 border-t border-line pt-1">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded bg-amber-400" />
                    <span>path trace</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded bg-emerald-500" />
                    <span>search match</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </Card>

        <div className="grid min-w-0 gap-3">
          {pathFrom && pathTo && (
            <div className="min-w-0 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              <b>Path trace:</b>{" "}
              <code className="break-all text-ink">{pathFrom}</code> →{" "}
              <code className="break-all text-ink">{pathTo}</code>. Dimmed
              nodes/edges are outside the shortest path.{" "}
              <button
                type="button"
                className="ml-1 underline"
                onClick={clearPath}
              >
                clear
              </button>
            </div>
          )}
          {pathMode && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
              {pathMode === "from"
                ? "Click any node in the canvas to set the path start."
                : "Click any node in the canvas to set the path end. Esc cancels."}
            </div>
          )}
          <GraphCanvas
            graph={data}
            visibleKinds={visible}
            layout={layout}
            filterOwner={filterOwner}
            filterEnvironment={filterEnvironment}
            filterFramework={filterFramework}
            searchQuery={search}
            pathFrom={pathFrom}
            pathTo={pathTo}
            onSelectNode={handleSelect}
            canvasRef={canvasRef}
          />
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Selected node</CardTitle>
          <CardDescription>
            Click any node in the canvas to inspect. Edges are derived, not
            stored.
          </CardDescription>
        </CardHeader>
        <div className="p-5 pt-0 text-sm">
          {selected ? (
            <div className="grid gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={KIND_TONE[selected.kind]}>
                  {selected.kind.replace("_", " ")}
                </Badge>
                <code className="break-all text-xs text-ink">
                  {selected.id}
                </code>
              </div>
              <dl className="grid min-w-0 grid-cols-[110px_minmax(0,1fr)] gap-x-3 gap-y-1.5 sm:grid-cols-[140px_minmax(0,1fr)]">
                <dt className="text-muted">Label</dt>
                <dd className="min-w-0 break-words font-extrabold">
                  {selected.label}
                </dd>
                {selected.subtitle && (
                  <>
                    <dt className="text-muted">Subtitle</dt>
                    <dd className="min-w-0 break-words">{selected.subtitle}</dd>
                  </>
                )}
                {selected.framework_id && (
                  <>
                    <dt className="text-muted">Framework</dt>
                    <dd className="font-extrabold">{selected.framework_id}</dd>
                  </>
                )}
                {selected.owner && (
                  <>
                    <dt className="text-muted">Owner</dt>
                    <dd className="font-extrabold">{selected.owner}</dd>
                  </>
                )}
                {selected.environment && (
                  <>
                    <dt className="text-muted">Environment</dt>
                    <dd className="font-extrabold">{selected.environment}</dd>
                  </>
                )}
                {selected.risk_score !== undefined && (
                  <>
                    <dt className="text-muted">Risk score</dt>
                    <dd className="font-extrabold">{selected.risk_score}</dd>
                  </>
                )}
                {selected.event_count !== undefined && (
                  <>
                    <dt className="text-muted">Evidence count</dt>
                    <dd className="font-extrabold">{selected.event_count}</dd>
                  </>
                )}
              </dl>
            </div>
          ) : (
            <div className="text-xs text-muted">No node selected.</div>
          )}
        </div>
      </Card>
    </div>
  );
}
