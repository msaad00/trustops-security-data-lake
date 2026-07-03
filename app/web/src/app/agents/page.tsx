"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bot,
  CheckCircle2,
  ClipboardCopy,
  Gauge,
  GitBranch,
  Loader2,
  LockKeyhole,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { useAuditorMode } from "@/lib/state/auditor";
import {
  useAgentRuns,
  useApproveAgentDecisionMutation,
  useCreateAgentRunMutation,
} from "@/lib/api/hooks";
import type { AgentHarness, AgentRun } from "@/lib/api/types";

type BadgeTone = "ready" | "info" | "attention" | "critical" | "default";

interface RouteSpec {
  method: "GET" | "POST";
  path: string;
  description: string;
  scope:
    | "agents"
    | "posture"
    | "controls"
    | "evidence"
    | "assets"
    | "snapshots"
    | "workflows"
    | "trust"
    | "audit"
    | "graph";
  body_example?: Record<string, unknown>;
  path_params?: Array<{ name: string; placeholder: string }>;
}

const ROUTES: RouteSpec[] = [
  {
    method: "GET",
    path: "/api/v1/agent-runs?limit=10",
    description: "Recent governed harness runs.",
    scope: "agents",
  },
  {
    method: "POST",
    path: "/api/v1/agent-runs",
    description: "Run a deterministic harness and persist evals + decisions.",
    scope: "agents",
    body_example: {
      harness: "posture_review",
      objective: "review current trust gaps",
      role: "analyst",
      use_model: false,
      idempotency_key: "manual-posture-review",
    },
  },
  {
    method: "POST",
    path: "/api/v1/agent-runs/{run_id}/decisions/{decision_index}/approve",
    description: "Approve one proposed write through the guarded executor.",
    scope: "agents",
    path_params: [
      { name: "run_id", placeholder: "run_..." },
      { name: "decision_index", placeholder: "0" },
    ],
    body_example: { note: "approved from console" },
  },
  {
    method: "GET",
    path: "/api/v1/healthz",
    description: "Server liveness envelope.",
    scope: "posture",
  },
  {
    method: "GET",
    path: "/api/v1/posture/current",
    description: "Full assessment posture + violations + frameworks.",
    scope: "posture",
  },
  {
    method: "GET",
    path: "/api/v1/control-tests?result=fail&limit=10",
    description: "Paginated control test results with confidence + freshness.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/controls?sort=-risk_score",
    description: "Sortable control posture catalog.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/violations?severity=critical,high",
    description: "Filterable open control failures.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/evidence?control_ids=SOC2-CC6.1",
    description: "Filterable silver normalized events.",
    scope: "evidence",
  },
  {
    method: "GET",
    path: "/api/v1/assets?sort=-risk_score",
    description: "Sortable asset risk roll-up.",
    scope: "assets",
  },
  {
    method: "GET",
    path: "/api/v1/snapshots",
    description: "Point-in-time snapshot list.",
    scope: "snapshots",
  },
  {
    method: "POST",
    path: "/api/v1/snapshots",
    description: "Freeze a snapshot.",
    scope: "snapshots",
    body_example: { reason: "audit_request" },
  },
  {
    method: "GET",
    path: "/api/connectors",
    description: "Connector registry joined with state + last probe.",
    scope: "controls",
  },
  {
    method: "POST",
    path: "/api/connectors/{id}/probe",
    description: "Run a probe against a connector.",
    scope: "controls",
    path_params: [{ name: "id", placeholder: "github-security" }],
    body_example: {},
  },
  {
    method: "GET",
    path: "/api/frameworks",
    description: "Framework registry + provenance + coverage.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/workflows",
    description: "Workflow list (latest version per id).",
    scope: "workflows",
  },
  {
    method: "GET",
    path: "/api/workflows/actions",
    description: "Action library with input/output schemas.",
    scope: "workflows",
  },
  {
    method: "POST",
    path: "/api/workflows/actions/run",
    description: "Execute a single action against the lake.",
    scope: "workflows",
    body_example: {
      node_type: "check.evidence_exists",
      params: { control_id: "SOC2-CC6.1", minimum: 1 },
    },
  },
  {
    method: "GET",
    path: "/api/trust-shares",
    description: "List active trust-share tokens.",
    scope: "trust",
  },
  {
    method: "POST",
    path: "/api/trust-shares",
    description: "Issue a new auditor share (returns raw token once).",
    scope: "trust",
    body_example: {
      role: "auditor",
      scope: "posture_full",
      expires_in_hours: 24,
    },
  },
  {
    method: "GET",
    path: "/api/audit-log",
    description: "Unified activity stream across every append-only log.",
    scope: "audit",
  },
  {
    method: "GET",
    path: "/api/graph",
    description: "Framework -> control -> evidence -> asset graph.",
    scope: "graph",
  },
  {
    method: "GET",
    path: "/api/crosswalk",
    description: "Framework x framework cross-mapping matrix.",
    scope: "graph",
  },
];

const SCOPE_TONE: Record<RouteSpec["scope"], BadgeTone> = {
  agents: "info",
  posture: "info",
  controls: "ready",
  evidence: "info",
  assets: "attention",
  snapshots: "critical",
  workflows: "ready",
  trust: "critical",
  audit: "default",
  graph: "info",
};

const HARNESS_COPY: Record<
  "posture_review" | "soc_triage",
  { label: string; objective: string; icon: typeof ShieldCheck }
> = {
  posture_review: {
    label: "Run posture review",
    objective: "review current trust gaps and propose governed next actions",
    icon: ShieldCheck,
  },
  soc_triage: {
    label: "Run SOC triage",
    objective:
      "triage current security signals and propose governed next actions",
    icon: GitBranch,
  },
};

function expandPath(route: RouteSpec, params: Record<string, string>): string {
  let path = route.path;
  for (const p of route.path_params ?? []) {
    const value = params[p.name] || p.placeholder;
    path = path.replace(`{${p.name}}`, encodeURIComponent(value));
  }
  return path;
}

function curlFor(
  route: RouteSpec,
  path: string,
  body: string,
  role: string,
): string {
  const lines: string[] = [`curl -s -X ${route.method} \\`];
  if (role) lines.push(`  -H 'X-Trust-Role: ${role}' \\`);
  if (route.method === "POST") {
    lines.push(`  -H 'content-type: application/json' \\`);
    lines.push(`  -d '${body || "{}"}' \\`);
  }
  lines.push(`  http://127.0.0.1:8787${path}`);
  return lines.join("\n");
}

function toneForStatus(status: string | undefined): BadgeTone {
  if (status === "completed" || status === "executed" || status === "approved")
    return "ready";
  if (status === "failed") return "critical";
  if (status === "proposed") return "attention";
  return "default";
}

function toneForConfidence(confidence: string | undefined): BadgeTone {
  if (confidence === "high") return "ready";
  if (confidence === "medium") return "attention";
  if (confidence === "low") return "critical";
  return "default";
}

function shortHash(value: string | null | undefined): string {
  if (!value) return "none";
  return value.length <= 10 ? value : value.slice(0, 10);
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function jsonPreview(value: unknown): string {
  if (!value || typeof value !== "object") return "{}";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

function harnessLabel(harness: AgentHarness): string {
  return harness.replaceAll("_", " ");
}

type Orchestrator = "sequential" | "langgraph";
type BudgetProfile = "small" | "standard";

const BUDGETS: Record<
  BudgetProfile,
  {
    label: string;
    max_fact_items: number;
    max_context_chars: number;
    max_output_tokens: number;
  }
> = {
  small: {
    label: "Small context",
    max_fact_items: 20,
    max_context_chars: 12000,
    max_output_tokens: 600,
  },
  standard: {
    label: "Standard review",
    max_fact_items: 40,
    max_context_chars: 20000,
    max_output_tokens: 900,
  },
};

export default function AgentsPage() {
  const auditor = useAuditorMode();
  const agentRuns = useAgentRuns();
  const createRun = useCreateAgentRunMutation();
  const approveDecision = useApproveAgentDecisionMutation();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selected, setSelected] = useState<RouteSpec>(ROUTES[0]);
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [body, setBody] = useState(
    ROUTES[0].body_example
      ? JSON.stringify(ROUTES[0].body_example, null, 2)
      : "",
  );
  const [role, setRole] = useState(auditor ? "auditor" : "");
  const [response, setResponse] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [orchestrator, setOrchestrator] = useState<Orchestrator>("sequential");
  const [useModel, setUseModel] = useState(false);
  const [budgetProfile, setBudgetProfile] = useState<BudgetProfile>("small");

  const runs = agentRuns.data ?? [];
  const selectedRun =
    runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null;
  const pendingDecisionCount = runs.reduce(
    (sum, run) =>
      sum +
      run.decisions.filter((decision) => decision.status === "proposed").length,
    0,
  );

  useEffect(() => {
    if (!selectedRunId && runs[0]) setSelectedRunId(runs[0].id);
  }, [runs, selectedRunId]);

  const flash = (msg: string) => notify.message(msg);

  const path = useMemo(
    () => expandPath(selected, pathParams),
    [selected, pathParams],
  );
  const curl = useMemo(
    () => curlFor(selected, path, body, role),
    [selected, path, body, role],
  );

  const runHarness = async (harness: "posture_review" | "soc_triage") => {
    const spec = HARNESS_COPY[harness];
    const budget = BUDGETS[budgetProfile];
    const safeOrchestrator = orchestrator;
    try {
      const run = await createRun.mutateAsync({
        harness,
        objective: spec.objective,
        role: "analyst",
        orchestrator: safeOrchestrator,
        use_model: useModel,
        idempotency_key: `console-${harness}-${Date.now()}`,
        max_fact_items: budget.max_fact_items,
        max_context_chars: budget.max_context_chars,
        max_output_tokens: budget.max_output_tokens,
      });
      setSelectedRunId(run.id);
      flash("Harness run saved.");
    } catch (err) {
      flash(String((err as Error).message));
    }
  };

  const approve = async (run: AgentRun, decisionIndex: number) => {
    try {
      const updated = await approveDecision.mutateAsync({
        runId: run.id,
        decisionIndex,
        note: "approved from console",
      });
      setSelectedRunId(updated.id);
      flash("Decision approved.");
    } catch (err) {
      flash(String((err as Error).message));
    }
  };

  const execute = async () => {
    setBusy(true);
    setResponse(null);
    setStatus(null);
    try {
      const init: RequestInit = {
        method: selected.method,
        headers: {
          ...(role ? { "X-Trust-Role": role } : {}),
          ...(selected.method === "POST"
            ? { "content-type": "application/json" }
            : {}),
        },
      };
      if (selected.method === "POST") init.body = body || "{}";
      const res = await fetch(path, init);
      setStatus(res.status);
      const text = await res.text();
      try {
        setResponse(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setResponse(text);
      }
    } catch (err) {
      setResponse(String((err as Error).message));
    } finally {
      setBusy(false);
    }
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      flash("Copied.");
    } catch {
      flash("Clipboard unavailable.");
    }
  };

  const selectRoute = (route: RouteSpec) => {
    setSelected(route);
    setPathParams({});
    setBody(
      route.body_example ? JSON.stringify(route.body_example, null, 2) : "",
    );
    setResponse(null);
    setStatus(null);
  };

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Agent harness"
        title="Governed runs"
        description="Run deterministic harnesses, inspect evaluations, and approve proposed writes."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={agentRuns.isError ? "critical" : "info"}>
              <Bot className="mr-1 h-3 w-3" /> {runs.length} runs
            </Badge>
            {pendingDecisionCount > 0 && (
              <Badge tone="attention">{pendingDecisionCount} pending</Badge>
            )}
          </div>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Start a harness</CardTitle>
            <CardDescription>
              Choose orchestration and budget, then run an approval-gated
              review.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="grid gap-3 rounded-xl border border-line bg-slate-50 p-3">
              <div className="grid gap-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-black uppercase tracking-wide text-muted">
                    Orchestrator
                  </span>
                  <Badge tone={orchestrator === "langgraph" ? "info" : "ready"}>
                    {orchestrator}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {(["sequential", "langgraph"] as const).map((value) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setOrchestrator(value)}
                      className={[
                        "rounded-lg border px-3 py-2 text-left text-xs font-black capitalize",
                        orchestrator === value
                          ? "border-brand bg-blue-50 text-brand"
                          : "border-line bg-white text-ink",
                      ].join(" ")}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </div>

              <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-line bg-white p-3">
                <input
                  type="checkbox"
                  checked={useModel}
                  onChange={(event) => setUseModel(event.target.checked)}
                  className="mt-1"
                />
                <span className="min-w-0">
                  <span className="block text-xs font-black text-ink">
                    Use configured model
                  </span>
                  <span className="mt-0.5 block text-xs leading-5 text-muted">
                    Off means rules-only. On still keeps decisions budgeted,
                    evaluated, and approval-gated.
                  </span>
                </span>
              </label>

              <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                Budget
                <select
                  value={budgetProfile}
                  onChange={(event) =>
                    setBudgetProfile(event.target.value as BudgetProfile)
                  }
                  className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                >
                  {Object.entries(BUDGETS).map(([value, budget]) => (
                    <option key={value} value={value}>
                      {budget.label} · {budget.max_fact_items} facts ·{" "}
                      {budget.max_output_tokens} tokens
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-lg border border-line bg-white p-3">
                <LockKeyhole className="h-4 w-4 text-brand" />
                <div className="mt-2 text-xs font-black text-ink">
                  Writes require approval
                </div>
              </div>
              <div className="rounded-lg border border-line bg-white p-3">
                <Gauge className="h-4 w-4 text-brand" />
                <div className="mt-2 text-xs font-black text-ink">
                  Budget is enforced
                </div>
              </div>
              <div className="rounded-lg border border-line bg-white p-3">
                <ShieldCheck className="h-4 w-4 text-brand" />
                <div className="mt-2 text-xs font-black text-ink">
                  Core owns verdicts
                </div>
              </div>
            </div>

            {(["posture_review", "soc_triage"] as const).map((harness) => {
              const spec = HARNESS_COPY[harness];
              const Icon = spec.icon;
              return (
                <Button
                  key={harness}
                  variant="default"
                  className="h-auto justify-start whitespace-normal px-3 py-3 text-left"
                  disabled={createRun.isPending}
                  onClick={() => runHarness(harness)}
                >
                  {createRun.isPending ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4 shrink-0" />
                  )}
                  <span className="min-w-0">
                    <span className="block">{spec.label}</span>
                    <span className="block truncate text-xs font-bold text-muted">
                      {harness === "posture_review"
                        ? `${orchestrator} · ${useModel ? "model assisted" : "rules only"}`
                        : `${orchestrator} · ${useModel ? "model assisted" : "rules only"}`}
                    </span>
                  </span>
                </Button>
              );
            })}
            {agentRuns.isError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
                Agent run API is unreachable.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle>Recent runs</CardTitle>
              <CardDescription>
                Persisted evals, decisions, budget, and input hash.
              </CardDescription>
            </div>
            {agentRuns.isFetching && (
              <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-muted" />
            )}
          </CardHeader>
          <div className="grid max-h-[360px] gap-2 overflow-auto p-4 pt-0">
            {runs.length === 0 ? (
              <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm font-bold text-muted">
                No persisted runs yet.
              </div>
            ) : (
              runs.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  onClick={() => setSelectedRunId(run.id)}
                  className={[
                    "grid min-w-0 gap-2 rounded-lg border px-3 py-3 text-left transition",
                    selectedRun?.id === run.id
                      ? "border-brand bg-blue-50"
                      : "border-line bg-white hover:bg-slate-50",
                  ].join(" ")}
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-black capitalize text-ink">
                      {harnessLabel(run.harness)}
                    </span>
                    <Badge tone={toneForStatus(run.status)}>{run.status}</Badge>
                    <Badge tone={toneForConfidence(run.evaluation.confidence)}>
                      {run.evaluation.confidence ?? "no confidence"}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-bold text-muted md:grid-cols-4">
                    <span>{run.decisions.length} decisions</span>
                    <span>{run.evaluation.score ?? 0} score</span>
                    <span>{shortHash(run.input_hash)}</span>
                    <span>{formatTime(run.created_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader className="flex-row items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle>Decision review</CardTitle>
            <CardDescription>
              Only allowlisted actions can execute from approval.
            </CardDescription>
          </div>
          {selectedRun && (
            <Badge tone={toneForStatus(selectedRun.status)}>
              {selectedRun.status}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          {!selectedRun ? (
            <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm font-bold text-muted">
              Select or create a run.
            </div>
          ) : (
            <div className="grid gap-4">
              <div className="grid gap-3 rounded-lg border border-line bg-slate-50 p-3 md:grid-cols-4">
                <div>
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Harness
                  </div>
                  <div className="truncate text-sm font-black capitalize text-ink">
                    {harnessLabel(selectedRun.harness)}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Confidence
                  </div>
                  <div className="text-sm font-black text-ink">
                    {selectedRun.evaluation.confidence ?? "none"}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Input hash
                  </div>
                  <code className="block truncate text-sm font-black text-ink">
                    {shortHash(selectedRun.input_hash)}
                  </code>
                </div>
                <div>
                  <div className="text-xs font-black uppercase tracking-wide text-muted">
                    Budget
                  </div>
                  <div className="truncate text-sm font-black text-ink">
                    {jsonPreview(selectedRun.budget).replace(/\s+/g, " ")}
                  </div>
                </div>
              </div>

              {selectedRun.errors.length > 0 && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
                  {selectedRun.errors.join(" ")}
                </div>
              )}

              <div className="grid gap-3">
                {selectedRun.decisions.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-line px-4 py-6 text-sm font-bold text-muted">
                    This run did not propose any writes.
                  </div>
                ) : (
                  selectedRun.decisions.map((decision, index) => (
                    <div
                      key={`${selectedRun.id}-${index}`}
                      className="grid min-w-0 gap-3 rounded-lg border border-line bg-white p-3 lg:grid-cols-[minmax(0,1fr)_auto]"
                    >
                      <div className="min-w-0">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <span className="truncate text-sm font-black text-ink">
                            {decision.action}
                          </span>
                          <Badge tone={toneForStatus(decision.status)}>
                            {decision.status ?? "proposed"}
                          </Badge>
                          {decision.requires_approval && (
                            <Badge tone="attention">approval</Badge>
                          )}
                        </div>
                        <p className="mt-1 text-sm font-bold leading-5 text-muted">
                          {decision.reason ?? "No reason provided."}
                        </p>
                        <pre className="mt-2 max-h-32 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-ink">
                          {jsonPreview(decision.payload)}
                        </pre>
                      </div>
                      <div className="flex items-start justify-end">
                        {decision.status === "proposed" ? (
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={approveDecision.isPending}
                            onClick={() => approve(selectedRun, index)}
                          >
                            {approveDecision.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <CheckCircle2 className="h-4 w-4" />
                            )}
                            Approve
                          </Button>
                        ) : (
                          <Badge tone={toneForStatus(decision.status)}>
                            {decision.status ?? "done"}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <details className="grid gap-3 rounded-xl border border-line bg-white p-4">
        <summary className="flex min-w-0 cursor-pointer list-none flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-black text-ink">API runner</h2>
            <p className="text-sm font-bold text-muted">
              Advanced contracts for CLI, scheduler, MCP, and headless agents.
            </p>
          </div>
          <Badge tone="info">
            <Sparkles className="mr-1 h-3 w-3" /> {ROUTES.length} routes
          </Badge>
        </summary>

        <div className="mt-4 grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>Routes</CardTitle>
              <CardDescription>Click to load into the runner.</CardDescription>
            </CardHeader>
            <div className="grid gap-1 p-4 pt-0">
              {ROUTES.map((route) => (
                <button
                  key={route.method + route.path}
                  type="button"
                  onClick={() => selectRoute(route)}
                  className={[
                    "grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs",
                    selected.method + selected.path ===
                    route.method + route.path
                      ? "bg-ink text-white"
                      : "text-slate-700 hover:bg-slate-50",
                  ].join(" ")}
                >
                  <Badge tone={route.method === "POST" ? "critical" : "ready"}>
                    {route.method}
                  </Badge>
                  <code className="truncate">{route.path}</code>
                </button>
              ))}
            </div>
          </Card>

          <div className="grid gap-5">
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle className="flex min-w-0 flex-wrap items-center gap-2">
                  <Badge
                    tone={selected.method === "POST" ? "critical" : "ready"}
                  >
                    {selected.method}
                  </Badge>
                  <code className="min-w-0 truncate text-sm text-ink">
                    {selected.path}
                  </code>
                  <Badge tone={SCOPE_TONE[selected.scope]}>
                    {selected.scope}
                  </Badge>
                </CardTitle>
                <CardDescription>{selected.description}</CardDescription>
              </CardHeader>
              <div className="grid gap-3 p-5 pt-0">
                {(selected.path_params ?? []).map((p) => (
                  <label
                    key={p.name}
                    className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                  >
                    {p.name}
                    <input
                      value={pathParams[p.name] ?? ""}
                      placeholder={p.placeholder}
                      onChange={(e) =>
                        setPathParams((prev) => ({
                          ...prev,
                          [p.name]: e.target.value,
                        }))
                      }
                      className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                    />
                  </label>
                ))}
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  X-Trust-Role (optional)
                  <input
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="auditor (leave blank for default)"
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
                {selected.method === "POST" && (
                  <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                    Body (JSON)
                    <textarea
                      rows={6}
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      className="rounded-lg border border-line bg-white px-3 py-2 font-mono text-xs text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                    />
                  </label>
                )}
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="primary" onClick={execute} disabled={busy}>
                    {busy ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}{" "}
                    Run
                  </Button>
                  <Button variant="default" onClick={() => copy(curl)}>
                    <ClipboardCopy className="h-4 w-4" /> Copy curl
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>curl</CardTitle>
                <CardDescription>
                  Reproduce this call from any shell.
                </CardDescription>
              </CardHeader>
              <pre className="overflow-auto bg-slate-950 p-4 text-xs text-slate-100">
                {curl}
              </pre>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle>Response</CardTitle>
                  {status !== null && (
                    <Badge
                      tone={
                        status < 300
                          ? "ready"
                          : status < 500
                            ? "attention"
                            : "critical"
                      }
                    >
                      {status}
                    </Badge>
                  )}
                </div>
                <CardDescription>
                  Raw response from the selected endpoint.
                </CardDescription>
              </CardHeader>
              <pre className="max-h-[420px] overflow-auto bg-slate-50 p-4 text-xs text-ink">
                {response ?? "Click Run to fire the request."}
              </pre>
            </Card>
          </div>
        </div>
      </details>
    </div>
  );
}
