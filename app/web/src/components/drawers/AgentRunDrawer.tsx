"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { useAgentRun, useApproveAgentDecisionMutation } from "@/lib/api/hooks";
import type { AgentRun } from "@/lib/api/types";

interface Props {
  runId: string | null;
  onClose: () => void;
}

function toneForStatus(status: string | undefined) {
  if (status === "completed" || status === "executed") return "ready" as const;
  if (status === "failed") return "critical" as const;
  if (status === "proposed") return "attention" as const;
  return "default" as const;
}

function jsonPreview(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function AgentRunDrawer({ runId, onClose }: Props) {
  const detail = useAgentRun(runId);
  const approveDecision = useApproveAgentDecisionMutation();
  const run = detail.data;

  const approve = async (target: AgentRun, decisionIndex: number) => {
    await approveDecision.mutateAsync({
      runId: target.id,
      decisionIndex,
      note: "approved from console drawer",
    });
  };

  return (
    <Drawer
      open={Boolean(runId)}
      onOpenChange={(open) => !open && onClose()}
      title={run?.id ?? "Agent run"}
      description={
        run
          ? `${run.harness.replaceAll("_", " ")} · ${run.status} · ${run.created_at}`
          : "Loading persisted harness evaluation"
      }
    >
      {detail.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading run detail…
        </div>
      ) : null}
      {detail.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
          Could not load agent run detail.
        </div>
      ) : null}
      {run ? (
        <div className="grid gap-5">
          <dl className="grid grid-cols-[120px_1fr] gap-x-3 gap-y-1.5 text-sm">
            <dt className="text-muted">Harness</dt>
            <dd className="font-bold capitalize text-ink">
              {run.harness.replaceAll("_", " ")}
            </dd>
            <dt className="text-muted">Status</dt>
            <dd>
              <Badge tone={toneForStatus(run.status)}>{run.status}</Badge>
            </dd>
            <dt className="text-muted">Confidence</dt>
            <dd>{run.evaluation.confidence ?? "none"}</dd>
            <dt className="text-muted">Score</dt>
            <dd>{run.evaluation.score ?? 0}</dd>
            <dt className="text-muted">Input hash</dt>
            <dd>
              <code className="text-xs">{run.input_hash}</code>
            </dd>
            <dt className="text-muted">Idempotency</dt>
            <dd>
              <code className="text-xs">{run.idempotency_key ?? "—"}</code>
            </dd>
          </dl>

          {run.errors.length > 0 ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
              {run.errors.join(" ")}
            </div>
          ) : null}

          <div className="grid gap-3">
            <span className="text-xs font-bold uppercase tracking-wide text-muted">
              Evaluation summary
            </span>
            <pre className="max-h-40 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-ink">
              {jsonPreview(run.evaluation)}
            </pre>
          </div>

          {run.state ? (
            <div className="grid gap-3">
              <span className="text-xs font-bold uppercase tracking-wide text-muted">
                Persisted state
              </span>
              <pre className="max-h-48 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-ink">
                {jsonPreview(run.state)}
              </pre>
            </div>
          ) : null}

          <div className="grid gap-3">
            <span className="text-xs font-bold uppercase tracking-wide text-muted">
              Proposed decisions
            </span>
            {run.decisions.length === 0 ? (
              <div className="rounded-lg border border-dashed border-line px-4 py-6 text-sm font-bold text-muted">
                No proposed writes for this run.
              </div>
            ) : (
              run.decisions.map((decision, index) => (
                <div
                  key={`${run.id}-${index}`}
                  className="grid gap-2 rounded-lg border border-line bg-white p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-black text-ink">
                      {decision.action}
                    </span>
                    <Badge tone={toneForStatus(decision.status)}>
                      {decision.status ?? "proposed"}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted">
                    {decision.reason ?? "No reason provided."}
                  </p>
                  <pre className="max-h-32 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-ink">
                    {jsonPreview(decision.payload)}
                  </pre>
                  {decision.status === "proposed" ? (
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-fit"
                      disabled={approveDecision.isPending}
                      onClick={() => approve(run, index)}
                    >
                      {approveDecision.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4" />
                      )}
                      Approve
                    </Button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}
    </Drawer>
  );
}
