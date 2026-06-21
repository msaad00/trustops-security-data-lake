"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { MarkerType, type Edge } from "@xyflow/react";
import {
  ArrowRight,
  LayoutTemplate,
  Loader2,
  Play,
  Plus,
  Save,
  ServerCog,
  Shuffle,
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
import { notify } from "@/lib/toast";
import { ActionPalette } from "@/components/workflow/ActionPalette";
import { NodeConfigPanel } from "@/components/workflow/NodeConfigPanel";
import { TemplateGallery } from "@/components/workflow/TemplateGallery";
import {
  WorkflowCanvas,
  toFlowNode,
  type FlowNode,
} from "@/components/workflow/WorkflowCanvas";
import {
  useActionCatalog,
  useRunWorkflow,
  useSaveWorkflow,
  useWorkflowRuns,
  useWorkflows,
} from "@/lib/api/hooks";
import type {
  ActionSpec,
  Workflow,
  WorkflowNode,
  WorkflowRun,
} from "@/lib/api/types";
import { useAuditorMode } from "@/lib/state/auditor";
import type { WorkflowTemplate } from "@/lib/workflow/templates";
import { WORKFLOW_TEMPLATES } from "@/lib/workflow/templates";

const NEW_WORKFLOW_ID = "__new__";

let counter = 0;
const nextNodeId = () => `n${Date.now()}_${counter++}`;

interface Editor {
  workflow_id: string | null;
  name: string;
  description: string;
  nodes: FlowNode[];
  edges: Edge[];
}

type WorkflowCondition = "always" | "passed" | "failed";

function emptyEditor(): Editor {
  return {
    workflow_id: null,
    name: "Untitled workflow",
    description: "",
    nodes: [],
    edges: [],
  };
}

function edgeTone(condition: WorkflowCondition) {
  if (condition === "passed") return "#16b364";
  if (condition === "failed") return "#d92d20";
  return "#64748b";
}

function toFlowEdge(
  source: string,
  target: string,
  condition: WorkflowCondition = "always",
  index = 0,
): Edge {
  const tone = edgeTone(condition);
  return {
    id: `${source}-${target}-${index}`,
    source,
    target,
    animated: true,
    label: condition === "always" ? undefined : condition,
    data: { condition },
    markerEnd: { type: MarkerType.ArrowClosed, color: tone },
    style: { stroke: tone, strokeWidth: 2 },
  };
}

function arrangeNodes(nodes: FlowNode[], edges: Edge[]): FlowNode[] {
  if (nodes.length === 0) return nodes;
  const inbound = new Map(nodes.map((n) => [n.id, 0]));
  const outgoing = new Map(nodes.map((n) => [n.id, [] as string[]]));
  for (const edge of edges) {
    inbound.set(
      String(edge.target),
      (inbound.get(String(edge.target)) ?? 0) + 1,
    );
    outgoing.get(String(edge.source))?.push(String(edge.target));
  }

  const depth = new Map<string, number>();
  const queue = nodes
    .filter((n) => (inbound.get(n.id) ?? 0) === 0)
    .map((n) => n.id);
  for (const id of queue) depth.set(id, 0);

  while (queue.length > 0) {
    const id = queue.shift()!;
    const nextDepth = (depth.get(id) ?? 0) + 1;
    for (const target of outgoing.get(id) ?? []) {
      if ((depth.get(target) ?? -1) < nextDepth) {
        depth.set(target, nextDepth);
        queue.push(target);
      }
    }
  }

  const byDepth = new Map<number, FlowNode[]>();
  for (const node of nodes) {
    const fallback =
      node.data.kind === "trigger" ? 0 : node.data.kind === "check" ? 1 : 2;
    const d = depth.get(node.id) ?? fallback;
    byDepth.set(d, [...(byDepth.get(d) ?? []), node]);
  }

  return nodes.map((node) => {
    const fallback =
      node.data.kind === "trigger" ? 0 : node.data.kind === "check" ? 1 : 2;
    const d = depth.get(node.id) ?? fallback;
    const column = byDepth.get(d) ?? [node];
    const row = column.findIndex((n) => n.id === node.id);
    const offset = ((column.length - 1) * 78) / 2;
    return {
      ...node,
      position: {
        x: 110 + d * 270,
        y: 170 + row * 156 - offset,
      },
    };
  });
}

function arrangeEditor(editor: Editor): Editor {
  return { ...editor, nodes: arrangeNodes(editor.nodes, editor.edges) };
}

function fromWorkflow(w: Workflow, catalog: ActionSpec[]): Editor {
  const byType = new Map(catalog.map((a) => [a.node_type, a]));
  return arrangeEditor({
    workflow_id: w.workflow_id,
    name: w.name,
    description: w.description,
    nodes: w.nodes.map((n) => toFlowNode(n, byType.get(n.node_type))),
    edges: w.edges.map((e, idx) =>
      toFlowEdge(e.source, e.target, e.condition ?? "always", idx),
    ),
  });
}

function fromTemplate(
  template: WorkflowTemplate,
  catalog: ActionSpec[],
): Editor {
  const byType = new Map(catalog.map((a) => [a.node_type, a]));
  return arrangeEditor({
    workflow_id: null,
    name: template.name,
    description: template.description,
    nodes: template.nodes.map((n) => toFlowNode(n, byType.get(n.node_type))),
    edges: template.edges.map((e, idx) =>
      toFlowEdge(e.source, e.target, e.condition ?? "always", idx),
    ),
  });
}

function toApiNodes(nodes: FlowNode[]): WorkflowNode[] {
  return nodes.map((n) => ({
    id: n.id,
    node_type: n.data.node_type,
    params: n.data.params,
    position: n.position,
  }));
}

function toApiEdges(edges: Edge[]) {
  return edges.map((e) => ({
    source: String(e.source),
    target: String(e.target),
    condition:
      (e.data as { condition?: "always" | "passed" | "failed" } | undefined)
        ?.condition ?? "always",
  }));
}

function WorkflowSpine({ nodes, edges }: { nodes: FlowNode[]; edges: Edge[] }) {
  const counts = {
    triggers: nodes.filter((n) => n.data.kind === "trigger").length,
    checks: nodes.filter((n) => n.data.kind === "check").length,
    actions: nodes.filter((n) => n.data.kind === "action").length,
    edges: edges.length,
  };
  const connected = counts.edges > 0 || nodes.length <= 1;
  const stages = [
    {
      label: "Trigger",
      value: counts.triggers,
      detail: "evidence changed, cron, or webhook",
    },
    {
      label: "Check",
      value: counts.checks,
      detail: "control pass, evidence exists, branch conditions",
    },
    {
      label: "Action",
      value: counts.actions,
      detail: "assign owner, create ticket, freeze snapshot, notify",
    },
  ];

  return (
    <section className="grid gap-2 rounded-xl border border-line bg-white p-3 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-black text-ink">
            Workflow connection map
          </h2>
          <p className="mt-0.5 text-xs leading-5 text-muted">
            A workflow is a directed graph: trigger inputs, check branches, and
            actions write back to remediation, snapshots, audit, or external
            systems.
          </p>
        </div>
        <Badge tone={connected ? "ready" : "attention"}>
          {connected ? `${counts.edges} connected edges` : "connect nodes"}
        </Badge>
      </div>
      <div className="grid gap-2 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-stretch">
        {stages.map((stage, idx) => (
          <Fragment key={stage.label}>
            <div className="rounded-lg border border-line bg-panel p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-black uppercase tracking-wide text-muted">
                  {stage.label}
                </span>
                <span className="text-lg font-black tabular-nums text-ink">
                  {stage.value}
                </span>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                {stage.detail}
              </p>
            </div>
            {idx < stages.length - 1 && (
              <div className="hidden items-center justify-center text-muted lg:flex">
                <ArrowRight className="h-5 w-5" />
              </div>
            )}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

export default function AutomationPage() {
  const auditor = useAuditorMode();
  const workflows = useWorkflows();
  const catalog = useActionCatalog();
  const save = useSaveWorkflow();
  const run = useRunWorkflow();
  const [activeId, setActiveId] = useState<string>(NEW_WORKFLOW_ID);
  const [editor, setEditor] = useState<Editor>(emptyEditor);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [lastRun, setLastRun] = useState<WorkflowRun | null>(null);
  const [starterLoaded, setStarterLoaded] = useState(false);
  const [fitTrigger, setFitTrigger] = useState(0);
  const runs = useWorkflowRuns(editor.workflow_id);

  const flash = useCallback((msg: string) => notify.success(msg), []);

  // Sync the editor whenever the user selects a different workflow.
  useEffect(() => {
    if (activeId === NEW_WORKFLOW_ID) return;
    const w = (workflows.data ?? []).find((x) => x.workflow_id === activeId);
    if (w) {
      setEditor(fromWorkflow(w, catalog.data ?? []));
      setLastRun(null);
    }
  }, [activeId, workflows.data, catalog.data]);

  useEffect(() => {
    if (starterLoaded || (catalog.data ?? []).length === 0) return;
    const firstWorkflow = (workflows.data ?? [])[0];
    if (firstWorkflow) {
      setActiveId(firstWorkflow.workflow_id);
      setStarterLoaded(true);
      return;
    }
    const starter = WORKFLOW_TEMPLATES[0];
    if (starter) {
      setEditor(fromTemplate(starter, catalog.data ?? []));
      setStarterLoaded(true);
    }
  }, [catalog.data, workflows.data, starterLoaded]);

  const specByType = useMemo(
    () => new Map((catalog.data ?? []).map((a) => [a.node_type, a])),
    [catalog.data],
  );

  // Merge last-run results into each node's render data so the canvas paints
  // a green/red halo around fired nodes after Run.
  const nodesWithRunState = useMemo<FlowNode[]>(() => {
    if (!lastRun) return editor.nodes;
    const byId = new Map(lastRun.node_results.map((r) => [r.node_id, r]));
    return editor.nodes.map((node) => {
      const result = byId.get(node.id);
      return {
        ...node,
        data: {
          ...node.data,
          runResult: result ? result.result : null,
        },
      };
    });
  }, [editor.nodes, lastRun]);

  const addNode = useCallback(
    (spec: ActionSpec, position?: { x: number; y: number }) => {
      const id = nextNodeId();
      const node: FlowNode = {
        id,
        type: "trustops",
        position: position ?? {
          x: 120 + (editor.nodes.length % 4) * 220,
          y: 140 + Math.floor(editor.nodes.length / 4) * 130,
        },
        data: {
          label: spec.label,
          kind: spec.kind,
          node_type: spec.node_type,
          params: {},
        },
      };
      setEditor((e) => ({ ...e, nodes: [...e.nodes, node] }));
      setSelectedNode(id);
    },
    [editor.nodes.length],
  );

  const updateNodeParams = useCallback(
    (id: string, params: Record<string, unknown>) => {
      setEditor((e) => ({
        ...e,
        nodes: e.nodes.map((n) =>
          n.id === id ? { ...n, data: { ...n.data, params } } : n,
        ),
      }));
    },
    [],
  );

  const deleteNode = useCallback((id: string) => {
    setEditor((e) => ({
      ...e,
      nodes: e.nodes.filter((n) => n.id !== id),
      edges: e.edges.filter((edge) => edge.source !== id && edge.target !== id),
    }));
  }, []);

  const loadTemplate = (template: WorkflowTemplate) => {
    setEditor(fromTemplate(template, catalog.data ?? []));
    setActiveId(NEW_WORKFLOW_ID);
    setStarterLoaded(true);
    setLastRun(null);
    setSelectedNode(null);
    flash(`Loaded "${template.name}" — save to persist.`);
  };

  const startNewWorkflow = () => {
    setActiveId(NEW_WORKFLOW_ID);
    setEditor(emptyEditor());
    setStarterLoaded(true);
    setLastRun(null);
    setSelectedNode(null);
    flash("New blank workflow opened.");
  };

  const persist = async () => {
    if (!editor.name.trim()) {
      flash("Workflow needs a name");
      return;
    }
    if (editor.nodes.length === 0) {
      flash("Add at least one node before saving");
      return;
    }
    try {
      const { workflow } = await save.mutateAsync({
        workflow_id: editor.workflow_id ?? undefined,
        name: editor.name.trim(),
        description: editor.description.trim(),
        nodes: toApiNodes(editor.nodes),
        edges: toApiEdges(editor.edges),
      });
      setActiveId(workflow.workflow_id);
      flash(`Saved ${workflow.name} v${workflow.version}.`);
    } catch (err) {
      flash(`Save failed: ${(err as Error).message}`);
    }
  };

  const execute = async () => {
    if (!editor.workflow_id) {
      flash("Save the workflow first.");
      return;
    }
    try {
      const { run: result } = await run.mutateAsync(editor.workflow_id);
      setLastRun(result);
      flash(
        `Run ${result.result.toUpperCase()} — ${result.node_results.length} nodes executed.`,
      );
    } catch (err) {
      flash(`Run failed: ${(err as Error).message}`);
    }
  };

  const selected = nodesWithRunState.find((n) => n.id === selectedNode) ?? null;
  const selectedSpec = selected
    ? (specByType.get(selected.data.node_type) ?? null)
    : null;
  const selectedRunResult = useMemo(() => {
    if (!lastRun || !selectedNode) return null;
    const match = lastRun.node_results.find((r) => r.node_id === selectedNode);
    if (!match) return null;
    return { result: match.result, output: match.output, error: match.error };
  }, [lastRun, selectedNode]);

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Workflows"
        title="Workflow builder"
        description="Design, save, and run closed-loop trust operations from one canvas."
        actions={
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Button variant="primary" onClick={startNewWorkflow}>
              <Plus className="h-4 w-4" /> New
            </Button>
            <select
              value={activeId === NEW_WORKFLOW_ID ? "" : activeId}
              onChange={(e) => {
                const next = e.target.value;
                if (!next) return;
                setActiveId(next);
                setSelectedNode(null);
                setLastRun(null);
              }}
              className="max-w-full rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand sm:max-w-[260px]"
            >
              <option value="">Saved workflows</option>
              {(workflows.data ?? []).map((w) => (
                <option key={w.workflow_id} value={w.workflow_id}>
                  {w.name} · v{w.version}
                </option>
              ))}
            </select>
            <Button variant="default" onClick={() => setTemplatesOpen(true)}>
              <LayoutTemplate className="h-4 w-4" /> Templates
            </Button>
            <Button
              variant="default"
              onClick={() => {
                setEditor((current) => arrangeEditor(current));
                setFitTrigger((value) => value + 1);
                flash("Canvas arranged.");
              }}
            >
              <Shuffle className="h-4 w-4" /> Arrange
            </Button>
            {!auditor && (
              <>
                <Button
                  variant="default"
                  onClick={persist}
                  disabled={save.isPending}
                >
                  {save.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}{" "}
                  Save
                </Button>
                <Button
                  variant="primary"
                  onClick={execute}
                  disabled={run.isPending || !editor.workflow_id}
                >
                  {run.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}{" "}
                  Run
                </Button>
              </>
            )}
          </div>
        }
      />

      <Card className="overflow-hidden border-brand/20">
        <div className="grid gap-3 p-3 sm:grid-cols-[minmax(220px,0.75fr)_minmax(260px,1.25fr)]">
          <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
            Name
            <input
              value={editor.name}
              onChange={(e) =>
                setEditor((ed) => ({ ...ed, name: e.target.value }))
              }
              className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
              disabled={auditor}
            />
          </label>
          <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
            Description
            <input
              value={editor.description}
              onChange={(e) =>
                setEditor((ed) => ({ ...ed, description: e.target.value }))
              }
              className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
              disabled={auditor}
            />
          </label>
        </div>
      </Card>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[240px_minmax(0,1fr)] 2xl:grid-cols-[240px_minmax(0,1fr)_340px]">
        <ActionPalette catalog={catalog.data ?? []} onAdd={addNode} />
        <WorkflowCanvas
          nodes={nodesWithRunState}
          edges={editor.edges}
          catalog={catalog.data ?? []}
          onNodesChange={(n) => setEditor((e) => ({ ...e, nodes: n }))}
          onEdgesChange={(es) => setEditor((e) => ({ ...e, edges: es }))}
          onSelectNode={setSelectedNode}
          onDropAction={addNode}
          fitTrigger={fitTrigger}
          lastRun={lastRun}
          onDismissRun={() => setLastRun(null)}
          onOpenTemplates={() => setTemplatesOpen(true)}
        />
        <NodeConfigPanel
          node={selected}
          spec={selectedSpec}
          lastResult={selectedRunResult}
          onClose={() => setSelectedNode(null)}
          onUpdateParams={updateNodeParams}
          onDelete={deleteNode}
        />
      </div>

      <WorkflowSpine nodes={editor.nodes} edges={editor.edges} />

      <Card className="grid gap-3 p-4 lg:grid-cols-[auto_minmax(0,1fr)] lg:items-start">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-panel text-brand ring-1 ring-line">
          <ServerCog className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="text-sm font-black text-ink">
            One runner for UI, API, scheduler, CLI, and agents
          </div>
          <p className="mt-1 text-sm leading-5 text-muted">
            Save writes an append-only workflow version to{" "}
            <code>gold/workflows.jsonl</code>. Run executes the same DAG through
            the backend workflow engine, enforces RBAC and egress guards, writes
            results to <code>gold/workflow_runs.jsonl</code>, and exposes the
            run through the console, REST API, CLI, scheduler, and MCP tools.
          </p>
          <div className="mt-3 grid gap-2 text-xs md:grid-cols-4">
            <div className="rounded-lg border border-line bg-panel p-2">
              <b className="text-ink">Human</b>
              <div className="mt-1 text-muted">
                Design, approve, run, inspect.
              </div>
            </div>
            <div className="rounded-lg border border-line bg-panel p-2">
              <b className="text-ink">Headless</b>
              <div className="mt-1 text-muted">REST/CLI run saved DAGs.</div>
            </div>
            <div className="rounded-lg border border-line bg-panel p-2">
              <b className="text-ink">Scheduler</b>
              <div className="mt-1 text-muted">
                Cron triggers fire due flows.
              </div>
            </div>
            <div className="rounded-lg border border-line bg-panel p-2">
              <b className="text-ink">Agents</b>
              <div className="mt-1 text-muted">
                MCP lists and runs workflows.
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Run history</CardTitle>
          <CardDescription>
            Latest runs for{" "}
            {editor.workflow_id ? (
              <code>{editor.workflow_id}</code>
            ) : (
              "this canvas"
            )}
            .
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {(runs.data ?? []).length === 0 ? (
            <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
              No runs yet. Save the workflow then click Run.
            </div>
          ) : (
            (runs.data ?? []).slice(0, 10).map((r) => (
              <button
                key={r.started_at + r.actor}
                type="button"
                onClick={() => setLastRun(r)}
                className="grid w-full gap-1 rounded-lg border border-line bg-white p-3 text-left text-xs hover:border-brand"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-black">
                    v{r.workflow_version} · {r.node_results.length} nodes
                  </span>
                  <Badge tone={r.result === "ok" ? "ready" : "critical"}>
                    {r.result}
                  </Badge>
                </div>
                <div className="text-muted">
                  actor <b className="text-ink">{r.actor}</b> · {r.started_at}
                </div>
              </button>
            ))
          )}
        </div>
      </Card>

      <TemplateGallery
        open={templatesOpen}
        onClose={() => setTemplatesOpen(false)}
        onPick={loadTemplate}
      />
    </div>
  );
}
