"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import {
  useControlExceptions,
  useCreateControlExceptionMutation,
  useCreateEvidenceRequestMutation,
  useCreateTaskMutation,
  useEvidenceRequests,
  useRemediationTasks,
  useRevokeControlExceptionMutation,
  useSetEvidenceRequestStatusMutation,
  useUpdateTaskMutation,
} from "@/lib/api/hooks";
import type {
  ControlExceptionItem,
  EvidenceRequestItem,
  RemediationTask,
} from "@/lib/api/types";

const inputClass =
  "rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand";

const STATUS_TONE: Record<
  string,
  "default" | "info" | "attention" | "ready" | "critical"
> = {
  open: "info",
  in_progress: "info",
  blocked: "attention",
  resolved: "ready",
  dismissed: "default",
  fulfilled: "ready",
  cancelled: "default",
  active: "ready",
  revoked: "default",
  expired: "attention",
};

const PRIORITY_TONE: Record<
  string,
  "default" | "info" | "attention" | "critical"
> = {
  low: "default",
  medium: "info",
  high: "attention",
  critical: "critical",
};

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function TasksSection() {
  const tasks = useRemediationTasks();
  const create = useCreateTaskMutation();
  const update = useUpdateTaskMutation();
  const [title, setTitle] = useState("");
  const [controlId, setControlId] = useState("");
  const [owner, setOwner] = useState("");
  const [priority, setPriority] = useState("medium");
  const [dueAt, setDueAt] = useState("");

  const submit = () => {
    if (!title.trim()) return;
    create.mutate(
      {
        title,
        control_id: controlId || null,
        owner,
        priority: priority as RemediationTask["priority"],
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      },
      {
        onSuccess: () => {
          setTitle("");
          setControlId("");
          setOwner("");
          setDueAt("");
        },
      },
    );
  };

  const rows = tasks.data ?? [];
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Remediation tasks</CardTitle>
        <CardDescription>
          Owned work with SLA due dates. Overdue is derived live.
        </CardDescription>
      </CardHeader>
      <div className="flex flex-wrap items-center gap-2 px-5 pb-4">
        <input
          className={`${inputClass} min-w-[220px] flex-1`}
          placeholder="Task title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          className={`${inputClass} w-40`}
          placeholder="control id"
          value={controlId}
          onChange={(e) => setControlId(e.target.value)}
        />
        <input
          className={`${inputClass} w-36`}
          placeholder="owner"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
        <select
          className={inputClass}
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          {["low", "medium", "high", "critical"].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          className={inputClass}
          type="date"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
        />
        <Button
          variant="primary"
          size="sm"
          onClick={submit}
          disabled={create.isPending || !title.trim()}
        >
          Add task
        </Button>
      </div>
      <QueryState queries={tasks} label="remediation tasks">
        <div className="divide-y divide-line border-t border-line">
          {rows.length === 0 && (
            <div className="px-5 py-6 text-sm text-muted">No tasks yet.</div>
          )}
          {rows.map((task: RemediationTask) => (
            <div
              key={task.id}
              className="flex flex-wrap items-center gap-3 px-5 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-black text-ink">
                  {task.title}
                </div>
                <div className="text-[11px] text-muted">
                  {task.control_id ?? "no control"} ·{" "}
                  {task.owner || "unassigned"} · due {fmtDate(task.due_at)}
                </div>
              </div>
              <Badge tone={PRIORITY_TONE[task.priority]}>{task.priority}</Badge>
              <Badge tone={STATUS_TONE[task.status]}>{task.status}</Badge>
              {task.overdue && <Badge tone="critical">overdue</Badge>}
              {task.status !== "resolved" && task.status !== "dismissed" && (
                <div className="flex gap-1.5">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      update.mutate({
                        id: task.id,
                        payload: { status: "resolved" },
                      })
                    }
                  >
                    Resolve
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      update.mutate({
                        id: task.id,
                        payload: { status: "dismissed" },
                      })
                    }
                  >
                    Dismiss
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </QueryState>
    </Card>
  );
}

function EvidenceRequestsSection() {
  const requests = useEvidenceRequests();
  const create = useCreateEvidenceRequestMutation();
  const setStatus = useSetEvidenceRequestStatusMutation();
  const [controlId, setControlId] = useState("");
  const [from, setFrom] = useState("");

  const submit = () => {
    if (!controlId.trim()) return;
    create.mutate(
      { control_id: controlId, requested_from: from },
      {
        onSuccess: () => {
          setControlId("");
          setFrom("");
        },
      },
    );
  };

  const rows = requests.data ?? [];
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Evidence requests</CardTitle>
        <CardDescription>
          Ask a control owner for fresh evidence and track fulfillment.
        </CardDescription>
      </CardHeader>
      <div className="flex flex-wrap items-center gap-2 px-5 pb-4">
        <input
          className={`${inputClass} w-44`}
          placeholder="control id"
          value={controlId}
          onChange={(e) => setControlId(e.target.value)}
        />
        <input
          className={`${inputClass} min-w-[200px] flex-1`}
          placeholder="requested from"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <Button
          variant="primary"
          size="sm"
          onClick={submit}
          disabled={create.isPending || !controlId.trim()}
        >
          Request evidence
        </Button>
      </div>
      <QueryState queries={requests} label="evidence requests">
        <div className="divide-y divide-line border-t border-line">
          {rows.length === 0 && (
            <div className="px-5 py-6 text-sm text-muted">
              No evidence requests.
            </div>
          )}
          {rows.map((req: EvidenceRequestItem) => (
            <div
              key={req.id}
              className="flex flex-wrap items-center gap-3 px-5 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-black text-ink">
                  {req.control_id}
                </div>
                <div className="text-[11px] text-muted">
                  from {req.requested_from || "—"} · created{" "}
                  {fmtDate(req.created_at)}
                </div>
              </div>
              <Badge tone={STATUS_TONE[req.status]}>{req.status}</Badge>
              {req.status === "open" && (
                <div className="flex gap-1.5">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setStatus.mutate({ id: req.id, status: "fulfilled" })
                    }
                  >
                    Fulfill
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setStatus.mutate({ id: req.id, status: "cancelled" })
                    }
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </QueryState>
    </Card>
  );
}

function ExceptionsSection() {
  const exceptions = useControlExceptions();
  const create = useCreateControlExceptionMutation();
  const revoke = useRevokeControlExceptionMutation();
  const [controlId, setControlId] = useState("");
  const [reason, setReason] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  const submit = () => {
    if (!controlId.trim()) return;
    create.mutate(
      {
        control_id: controlId,
        reason,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      },
      {
        onSuccess: () => {
          setControlId("");
          setReason("");
          setExpiresAt("");
        },
      },
    );
  };

  const rows = exceptions.data ?? [];
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>Control exceptions</CardTitle>
        <CardDescription>
          Time-boxed, approved exceptions. Requires the control-manage role.
        </CardDescription>
      </CardHeader>
      <div className="flex flex-wrap items-center gap-2 px-5 pb-4">
        <input
          className={`${inputClass} w-44`}
          placeholder="control id"
          value={controlId}
          onChange={(e) => setControlId(e.target.value)}
        />
        <input
          className={`${inputClass} min-w-[200px] flex-1`}
          placeholder="reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <input
          className={inputClass}
          type="date"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
        />
        <Button
          variant="primary"
          size="sm"
          onClick={submit}
          disabled={create.isPending || !controlId.trim()}
        >
          Add exception
        </Button>
      </div>
      <QueryState queries={exceptions} label="control exceptions">
        <div className="divide-y divide-line border-t border-line">
          {rows.length === 0 && (
            <div className="px-5 py-6 text-sm text-muted">No exceptions.</div>
          )}
          {rows.map((exc: ControlExceptionItem) => (
            <div
              key={exc.id}
              className="flex flex-wrap items-center gap-3 px-5 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-black text-ink">
                  {exc.control_id}
                </div>
                <div className="text-[11px] text-muted">
                  {exc.reason || "no reason"} · by {exc.approved_by || "—"} ·
                  expires {fmtDate(exc.expires_at)}
                </div>
              </div>
              <Badge tone={exc.active ? "ready" : STATUS_TONE[exc.status]}>
                {exc.active ? "active" : exc.status}
              </Badge>
              {exc.active && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => revoke.mutate(exc.id)}
                >
                  Revoke
                </Button>
              )}
            </div>
          ))}
        </div>
      </QueryState>
    </Card>
  );
}

export default function RemediationPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operate"
        title="Remediation"
        description="Assign and track remediation work, request evidence from owners, and manage time-boxed control exceptions."
      />
      <TasksSection />
      <EvidenceRequestsSection />
      <ExceptionsSection />
    </div>
  );
}
