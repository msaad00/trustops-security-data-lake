"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import type {
  ComplianceGraph,
  GraphNode,
  GraphNodeKind,
} from "@/lib/api/types";

interface GraphNodeData extends Record<string, unknown> {
  label: string;
  subtitle: string;
  kind: GraphNodeKind;
  framework_id?: string;
  owner?: string;
  risk_score?: number;
  /** Render emphasis driven by search / select / path-trace. */
  emphasis: "active" | "dimmed" | "highlight" | "path" | "match";
}

type FlowGraphNode = Node<GraphNodeData, "trustops-graph">;

const KIND_STYLE: Partial<
  Record<GraphNodeKind, { border: string; bg: string; chip: string }>
> = {
  framework: { border: "#4f7cff", bg: "#eff6ff", chip: "#1d4ed8" },
  control: { border: "#16b364", bg: "#ecfdf5", chip: "#067647" },
  evidence_type: { border: "#f79009", bg: "#fffbeb", chip: "#b54708" },
  asset: { border: "#7a35ff", bg: "#f5f0ff", chip: "#6d28d9" },
  repository: { border: "#0ea5e9", bg: "#eff6ff", chip: "#0369a1" },
  directory: { border: "#64748b", bg: "#f8fafc", chip: "#475569" },
  language: { border: "#16b364", bg: "#ecfdf5", chip: "#067647" },
  evidence_signal: { border: "#f79009", bg: "#fffbeb", chip: "#b54708" },
  governance_signal: { border: "#2563eb", bg: "#eff6ff", chip: "#1d4ed8" },
  signal_gap: { border: "#dc2626", bg: "#fef2f2", chip: "#b91c1c" },
  workflow: { border: "#7c3aed", bg: "#f5f3ff", chip: "#6d28d9" },
  dependency_manifest: { border: "#c2410c", bg: "#fff7ed", chip: "#9a3412" },
  principal: { border: "#be123c", bg: "#fff1f2", chip: "#9f1239" },
  team: { border: "#4338ca", bg: "#eef2ff", chip: "#3730a3" },
  evidence: { border: "#475569", bg: "#f8fafc", chip: "#334155" },
};

function emphasisClass(emphasis: GraphNodeData["emphasis"]): string {
  switch (emphasis) {
    case "dimmed":
      return "opacity-25";
    case "highlight":
      return "opacity-100 shadow-[0_0_0_3px_rgba(15,23,42,0.18)]";
    case "path":
      return "opacity-100 shadow-[0_0_0_3px_rgba(245,158,11,0.55)]";
    case "match":
      return "opacity-100 shadow-[0_0_0_3px_rgba(34,197,94,0.55)]";
    default:
      return "opacity-100";
  }
}

function GraphNodeCard({ data, selected }: NodeProps<FlowGraphNode>) {
  const tone = KIND_STYLE[data.kind] ?? {
    border: "#94a3b8",
    bg: "#f8fafc",
    chip: "#475569",
  };
  return (
    <Tooltip.Root delayDuration={120}>
      <Tooltip.Trigger asChild>
        <div
          style={{
            borderColor: selected ? "#101623" : tone.border,
            background: tone.bg,
            borderWidth: selected ? 2 : 1.5,
          }}
          className={`min-w-[180px] max-w-[220px] rounded-xl px-3 py-2.5 transition-all ${emphasisClass(data.emphasis)}`}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wide"
              style={{ color: tone.chip, background: "#ffffff" }}
            >
              {data.kind.replace("_", " ")}
            </span>
            {data.kind === "framework" && data.framework_id && (
              <FrameworkBadge
                frameworkId={data.framework_id}
                fallbackLabel={data.label}
                size={24}
              />
            )}
          </div>
          <div className="mt-1.5 truncate text-sm font-black text-ink">
            {data.label}
          </div>
          <div className="truncate text-[11px] text-slate-600">
            {data.subtitle}
          </div>
          {data.owner && (
            <div className="mt-1 truncate text-[10px] text-slate-500">
              owner {data.owner}
            </div>
          )}
        </div>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="top"
          sideOffset={8}
          className="z-[80] max-w-[280px] rounded-lg border border-line bg-white p-3 text-xs text-ink shadow-hero"
        >
          <div className="text-[10px] font-black uppercase tracking-wider text-muted">
            {data.kind.replace("_", " ")}
          </div>
          <div className="mt-1 font-black">{data.label}</div>
          {data.subtitle && (
            <div className="mt-0.5 text-muted">{data.subtitle}</div>
          )}
          <div className="mt-2 grid gap-0.5 text-[11px]">
            {data.framework_id && (
              <div>
                framework: <code className="text-ink">{data.framework_id}</code>
              </div>
            )}
            {data.owner && (
              <div>
                owner: <b className="text-ink">{data.owner}</b>
              </div>
            )}
            {data.risk_score !== undefined && (
              <div>
                risk: <b className="text-ink">{data.risk_score}</b>
              </div>
            )}
          </div>
          <Tooltip.Arrow className="fill-white" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

const nodeTypes: NodeTypes = { "trustops-graph": GraphNodeCard };

export type LayoutDir = "LR" | "TB" | "BT";

function layoutGraph(
  rfNodes: FlowGraphNode[],
  rfEdges: Edge[],
  rankdir: LayoutDir,
): { nodes: FlowGraphNode[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir, nodesep: 30, ranksep: 70, marginx: 20, marginy: 20 });

  rfNodes.forEach((node) => g.setNode(node.id, { width: 200, height: 80 }));
  rfEdges.forEach((edge) => g.setEdge(edge.source, edge.target));
  dagre.layout(g);

  const laidOut = rfNodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: { x: pos.x - 100, y: pos.y - 40 },
    };
  });
  return { nodes: laidOut, edges: rfEdges };
}

interface Props {
  graph: ComplianceGraph | undefined;
  visibleKinds: Set<GraphNodeKind>;
  layout: LayoutDir;
  filterOwner: string;
  filterEnvironment: string;
  filterFramework: string;
  searchQuery: string;
  pathFrom: string | null;
  pathTo: string | null;
  onSelectNode: (node: GraphNode | null) => void;
}

interface ImperativeRef {
  toJSON: () => unknown;
  toSVG: () => string | null;
}

export function GraphCanvas(
  props: Props & { canvasRef?: React.MutableRefObject<ImperativeRef | null> },
) {
  return (
    <ReactFlowProvider>
      <Tooltip.Provider>
        <InnerGraphCanvas {...props} />
      </Tooltip.Provider>
    </ReactFlowProvider>
  );
}

function InnerGraphCanvas({
  graph,
  visibleKinds,
  layout,
  filterOwner,
  filterEnvironment,
  filterFramework,
  searchQuery,
  pathFrom,
  pathTo,
  onSelectNode,
  canvasRef,
}: Props & { canvasRef?: React.MutableRefObject<ImperativeRef | null> }) {
  const [hydrated, setHydrated] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  useEffect(() => setHydrated(true), []);
  const { setCenter } = useReactFlow();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Apply layer + facet filters in one place so the canvas + path-trace + search agree.
  const filteredNodes = useMemo(() => {
    if (!graph) return [];
    return graph.nodes.filter((n) => {
      if (!visibleKinds.has(n.kind)) return false;
      if (filterOwner && (n.owner ?? "") !== filterOwner) return false;
      if (filterEnvironment && (n.environment ?? "") !== filterEnvironment)
        return false;
      if (
        filterFramework &&
        n.kind !== "framework" &&
        (n.framework_id ?? "") !== filterFramework
      )
        return false;
      if (
        filterFramework &&
        n.kind === "framework" &&
        n.framework_id !== filterFramework
      )
        return false;
      return true;
    });
  }, [graph, visibleKinds, filterOwner, filterEnvironment, filterFramework]);

  const allowedIds = useMemo(
    () => new Set(filteredNodes.map((n) => n.id)),
    [filteredNodes],
  );

  // Compute neighbor sets for the currently selected node so the canvas can
  // bright-highlight it + its 1-hop neighbors and dim the rest.
  const adjacency = useMemo(() => {
    const out = new Map<string, Set<string>>();
    if (!graph) return out;
    for (const e of graph.edges) {
      if (!allowedIds.has(e.source) || !allowedIds.has(e.target)) continue;
      if (!out.has(e.source)) out.set(e.source, new Set());
      if (!out.has(e.target)) out.set(e.target, new Set());
      out.get(e.source)!.add(e.target);
      out.get(e.target)!.add(e.source);
    }
    return out;
  }, [graph, allowedIds]);

  const highlightSet = useMemo<Set<string> | null>(() => {
    if (!selectedId) return null;
    const out = new Set<string>([selectedId]);
    for (const n of adjacency.get(selectedId) ?? []) out.add(n);
    return out;
  }, [selectedId, adjacency]);

  // Two-click path trace via BFS over the filtered subgraph.
  const pathSet = useMemo<{
    nodes: Set<string>;
    edges: Set<string>;
  } | null>(() => {
    if (!graph || !pathFrom || !pathTo || pathFrom === pathTo) return null;
    if (!allowedIds.has(pathFrom) || !allowedIds.has(pathTo)) return null;
    const visited = new Map<string, string | null>([[pathFrom, null]]);
    const queue: string[] = [pathFrom];
    while (queue.length > 0) {
      const cur = queue.shift()!;
      if (cur === pathTo) break;
      for (const next of adjacency.get(cur) ?? []) {
        if (visited.has(next)) continue;
        visited.set(next, cur);
        queue.push(next);
      }
    }
    if (!visited.has(pathTo)) return null;
    const nodes = new Set<string>();
    let step: string | null = pathTo;
    while (step) {
      nodes.add(step);
      step = visited.get(step) ?? null;
    }
    const edges = new Set<string>();
    for (const e of graph.edges) {
      if (nodes.has(e.source) && nodes.has(e.target)) edges.add(e.id);
    }
    return { nodes, edges };
  }, [graph, pathFrom, pathTo, allowedIds, adjacency]);

  // Search highlight: case-insensitive match against label / subtitle / id.
  const matchSet = useMemo<Set<string> | null>(() => {
    if (!searchQuery.trim()) return null;
    const lower = searchQuery.trim().toLowerCase();
    const out = new Set<string>();
    for (const n of filteredNodes) {
      const hay =
        `${n.label} ${n.subtitle ?? ""} ${n.id} ${n.owner ?? ""}`.toLowerCase();
      if (hay.includes(lower)) out.add(n.id);
    }
    return out;
  }, [searchQuery, filteredNodes]);

  const { nodes: rfNodes, edges: rfEdges } = useMemo(() => {
    if (!graph) return { nodes: [] as FlowGraphNode[], edges: [] as Edge[] };
    const list: FlowGraphNode[] = filteredNodes.map((n) => {
      let emphasis: GraphNodeData["emphasis"] = "active";
      if (matchSet) emphasis = matchSet.has(n.id) ? "match" : "dimmed";
      else if (pathSet) emphasis = pathSet.nodes.has(n.id) ? "path" : "dimmed";
      else if (highlightSet)
        emphasis = highlightSet.has(n.id) ? "highlight" : "dimmed";
      return {
        id: n.id,
        type: "trustops-graph",
        position: { x: 0, y: 0 },
        data: {
          label: n.label,
          subtitle: n.subtitle ?? "",
          kind: n.kind,
          framework_id: n.framework_id,
          owner: n.owner,
          risk_score: n.risk_score,
          emphasis,
        },
      };
    });
    const edges: Edge[] = graph.edges
      .filter((e) => allowedIds.has(e.source) && allowedIds.has(e.target))
      .map((e) => {
        const onPath = pathSet?.edges.has(e.id) ?? false;
        const onHighlight =
          highlightSet &&
          (highlightSet.has(e.source) || highlightSet.has(e.target));
        const dimmed =
          (matchSet && !matchSet.has(e.source) && !matchSet.has(e.target)) ||
          (pathSet && !onPath) ||
          (highlightSet && !onHighlight);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          animated: e.kind === "evidence_covers_asset" || onPath,
          style: {
            stroke: onPath ? "#f59e0b" : onHighlight ? "#0f172a" : "#94a3b8",
            strokeWidth: onPath ? 2.5 : 1.5,
            opacity: dimmed && !onPath && !onHighlight ? 0.2 : 1,
          },
        };
      });
    return layoutGraph(list, edges, layout);
  }, [
    graph,
    filteredNodes,
    allowedIds,
    layout,
    matchSet,
    pathSet,
    highlightSet,
  ]);

  // When the search has exactly one match, recentre the viewport on it so the
  // user sees the result immediately.
  useEffect(() => {
    if (!matchSet || matchSet.size !== 1) return;
    const match = rfNodes.find((n) => matchSet.has(n.id));
    if (!match) return;
    setCenter(match.position.x + 100, match.position.y + 40, {
      zoom: 1.1,
      duration: 300,
    });
  }, [matchSet, rfNodes, setCenter]);

  // Expose imperative export helpers to the parent (Export menu).
  useEffect(() => {
    if (!canvasRef) return;
    canvasRef.current = {
      toJSON: () => graph ?? null,
      toSVG: () => {
        const root = wrapperRef.current;
        if (!root) return null;
        const svg = root.querySelector(
          "svg.react-flow__edges",
        ) as SVGSVGElement | null;
        if (!svg) return null;
        const clone = svg.cloneNode(true) as SVGSVGElement;
        clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        return new XMLSerializer().serializeToString(clone);
      },
    };
  }, [graph, canvasRef]);

  const handleSelectionChange = useCallback(
    ({ nodes: selected }: { nodes: Node[] }) => {
      const first = selected[0];
      setSelectedId(first?.id ?? null);
      if (!first) return onSelectNode(null);
      const original = graph?.nodes.find((n) => n.id === first.id) ?? null;
      onSelectNode(original);
    },
    [graph, onSelectNode],
  );

  if (!hydrated) {
    return (
      <div className="h-[min(680px,calc(100dvh-300px))] min-h-[520px] rounded-2xl border border-line bg-white" />
    );
  }

  return (
    <div
      ref={wrapperRef}
      className="h-[min(680px,calc(100dvh-300px))] min-h-[520px] overflow-hidden rounded-2xl border border-line bg-white"
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        nodesDraggable
        nodesConnectable={false}
        edgesReconnectable={false}
        defaultViewport={{ x: 96, y: 96, zoom: 0.82 }}
        minZoom={0.25}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
        onSelectionChange={handleSelectionChange}
      >
        <Background gap={20} color="#e2e8f0" />
        <MiniMap pannable zoomable maskColor="rgba(15,23,42,0.06)" />
        <Controls position="bottom-left" />
      </ReactFlow>
    </div>
  );
}

export type { ImperativeRef };
