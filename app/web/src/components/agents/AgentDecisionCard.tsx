"use client";

import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApproveAgentDecisionMutation } from "@/lib/api/hooks";
import type { AgentDecision, AgentRun } from "@/lib/api/types";
import { notify } from "@/lib/toast";

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

function executionLink(result: Record<string, unknown> | undefined) {
  const kind = String(result?.type ?? result?.resource ?? "");
  const id = String(result?.id ?? result?.task_id ?? result?.request_id ?? "");
  if (!id) return null;
  if (kind.includes("remediation") || kind.includes("task")) {
    return { href: "/remediation", label: "View remediation" };
  }
  if (kind.includes("evidence")) {
    return { href: "/remediation", label: "View evidence request" };
  }
  if (kind.includes("snapshot")) {
    return { href: "/audit-room", label: "View snapshot" };
  }
  return null;
}

interface Props {
  run: AgentRun;
  decision: AgentDecision;
  decisionIndex: number;
  compact?: boolean;
}

export function AgentDecisionCard({
  run,
  decision,
  decisionIndex,
  compact = false,
}: Props) {
  const approveDecision = useApproveAgentDecisionMutation();
  const [note, setNote] = useState("");

  const approve = async () => {
    try {
      await approveDecision.mutateAsync({
        runId: run.id,
        decisionIndex,
        note: note.trim() || "approved from console",
      });
      notify.success("Decision approved and executed.");
    } catch (err) {
      notify.error(String((err as Error).message));
    }
  };

  const link = executionLink(decision.execution_result);

  return (
    <div
      className={[
        "grid min-w-0 gap-3 rounded-lg border border-line bg-white p-3",
        compact ? "" : "lg:grid-cols-[minmax(0,1fr)_auto]",
      ].join(" ")}
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
        {decision.execution_result ? (
          <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
            <div className="font-black">Execution result</div>
            <pre className="mt-1 overflow-auto">
              {jsonPreview(decision.execution_result)}
            </pre>
            {link ? (
              <Link
                href={link.href}
                className="mt-2 inline-flex text-xs font-black text-brand hover:underline"
              >
                {link.label}
              </Link>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="flex min-w-0 flex-col items-stretch gap-2 lg:items-end">
        {decision.status === "proposed" ? (
          <>
            <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
              Approver note
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={2}
                placeholder="Optional context for audit trail"
                className="min-w-[220px] rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </label>
            <Button
              variant="primary"
              size="sm"
              className="w-fit self-end"
              disabled={approveDecision.isPending}
              onClick={approve}
            >
              {approveDecision.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Approve
            </Button>
          </>
        ) : (
          <Badge tone={toneForStatus(decision.status)}>
            {decision.status ?? "done"}
          </Badge>
        )}
      </div>
    </div>
  );
}

export function modeLabel(mode: string | undefined) {
  if (mode === "rules_only") return "fixture";
  if (mode === "model_assisted") return "model";
  if (mode === "langgraph") return "langgraph";
  return mode ?? "unknown";
}

export function modeTone(mode: string | undefined) {
  if (mode === "rules_only") return "ready" as const;
  if (mode === "model_assisted") return "info" as const;
  return "default" as const;
}
