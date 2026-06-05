"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Edge } from "@xyflow/react";
import { LayoutTemplate, Loader2, Play, Save } from "lucide-react";
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

function emptyEditor(): Editor {
  return {
    workflow_id: null,
    name: "Untitled workflow",
    description: "",
    nodes: [],
    edges: [],
  };
}

function fromWorkflow(w: Workflow, catalog: ActionSpec[]): Editor {
  const byType = new Map(catalog.map((a) => [a.node_type, a]));
  return {
    workflow_id: w.workflow_id,
    name: w.name,
    description: w.description,
    nodes: w.nodes.map((n) => toFlowNode(n, byType.get(n.node_type))),
    edges: w.edges.map((e) => ({
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      animated: true,
      label: e.condition && e.condition !== "always" ? e.condition : undefined,
      data: { condition: e.condition ?? "always" },
    })),
  };
}

function fromTemplate(
  template: WorkflowTemplate,
  catalog: ActionSpec[],
): Editor {
  const byType = new Map(catalog.map((a) => [a.node_type, a]));
  return {
    workflow_id: null,
    name: template.name,
    description: template.description,
    nodes: template.nodes.map((n) => toFlowNode(n, byType.get(n.node_type))),
    edges: template.edges.map((e, idx) => ({
      id: `${e.source}-${e.target}-${idx}`,
      source: e.source,
      target: e.target,
      animated: true,
      label: e.condition && e.condition !== "always" ? e.condition : undefined,
      data: { condition: e.condition ?? "always" },
    })),
  };
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
    setLastRun(null);
    setSelectedNode(null);
    flash(`Loaded "${template.name}" — save to persist.`);
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
        title="Workflow canvas"
        description="Drag actions from the library, connect them, then save and run. Every action publishes its input/output schema; downstream params can reference upstream output with `{{nodeId.output.field}}`. Conditional edges (passed / failed) gate next steps on check results."
        actions={
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <select
              value={activeId}
              onChange={(e) => {
                const next = e.target.value;
                setActiveId(next);
                if (next === NEW_WORKFLOW_ID) setEditor(emptyEditor());
                setSelectedNode(null);
                setLastRun(null);
              }}
              className="max-w-full rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand sm:max-w-[260px]"
            >
              <option value={NEW_WORKFLOW_ID}>+ New workflow</option>
              {(workflows.data ?? []).map((w) => (
                <option key={w.workflow_id} value={w.workflow_id}>
                  {w.name} · v{w.version}
                </option>
              ))}
            </select>
            <Button variant="default" onClick={() => setTemplatesOpen(true)}>
              <LayoutTemplate className="h-4 w-4" /> Templates
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

      <Card className="overflow-hidden">
        <div className="grid gap-3 p-4 sm:grid-cols-[1fr_2fr]">
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
