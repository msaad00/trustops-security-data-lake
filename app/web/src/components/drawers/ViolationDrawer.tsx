"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, History, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { EntityTagsEditor } from "@/components/EntityTagsEditor";
import { useTracking, useTriageMutation } from "@/lib/api/hooks";
import { useAuditorMode } from "@/lib/state/auditor";
import type { TrackingState, Violation } from "@/lib/api/types";

interface Props {
  violation: Violation | null;
  onClose: () => void;
  onToast: (msg: string) => void;
}

const STATE_TONE: Record<
  TrackingState,
  "default" | "info" | "ready" | "attention" | "critical"
> = {
  open: "critical",
  triaged: "info",
  in_progress: "attention",
  resolved: "ready",
  dismissed: "default",
};

const STATES: TrackingState[] = [
  "triaged",
  "in_progress",
  "resolved",
  "dismissed",
];

export function ViolationDrawer({ violation, onClose, onToast }: Props) {
  const auditor = useAuditorMode();
  const tracking = useTracking(violation?.violation_id ?? null);
  const triage = useTriageMutation();
  const [state, setState] = useState<TrackingState>("triaged");
  const [actor, setActor] = useState("trust-admin");
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");
  const [dueAt, setDueAt] = useState("");

  useEffect(() => {
    if (!violation) return;
    setState("triaged");
    setActor("trust-admin");
    setAssignee(violation.asset_owner ?? "");
    setNote("");
    setDueAt("");
  }, [violation]);

  const history = tracking.data?.events ?? [];
  const currentState =
    tracking.data?.current_state ??
    (violation?.state as TrackingState | undefined) ??
    "open";

  const submit = async () => {
    if (!violation) return;
    try {
      await triage.mutateAsync({
        violationId: violation.violation_id,
        payload: {
          state,
          actor,
          assignee: assignee || undefined,
          note: note || undefined,
          due_at: dueAt || undefined,
        },
      });
      onToast(`Triage recorded: ${violation.violation_id} → ${state}`);
    } catch (err) {
      onToast(`Triage failed: ${(err as Error).message}`);
    }
  };

  const stateOptions = useMemo(
    () =>
      STATES.map((s) => (
        <option key={s} value={s}>
          {s.replace("_", " ")}
        </option>
      )),
    [],
  );

  return (
    <Drawer
      open={Boolean(violation)}
      onOpenChange={(o) => !o && onClose()}
      title={violation?.violation_id ?? "Violation"}
      description={
        violation
          ? `${violation.event_type} · ${violation.control_id}`
          : undefined
      }
      width="lg"
      footer={
        !auditor && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted">
              Persisted to gold/violation_tracking.jsonl — auditable +
              append-only.
            </span>
            <Button
              variant="primary"
              onClick={submit}
              disabled={triage.isPending}
            >
              {triage.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}{" "}
              Record triage event
            </Button>
          </div>
        )
      }
    >
      {violation && (
        <div className="grid gap-5">
          <div className="rounded-xl border border-line bg-slate-50/60 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge
                tone={
                  violation.severity === "critical" ? "critical" : "attention"
                }
              >
                {violation.severity} · {violation.severity_score}
              </Badge>
              <Badge
                tone={STATE_TONE[currentState as TrackingState] ?? "default"}
              >
                {currentState}
              </Badge>
            </div>
            <dl className="mt-3 grid grid-cols-[120px_1fr] gap-x-3 gap-y-1.5 text-xs">
              <dt className="text-muted">Asset</dt>
              <dd>
                <code className="text-ink">{violation.asset_id}</code>
              </dd>
              <dt className="text-muted">Owner</dt>
              <dd className="font-extrabold">{violation.asset_owner}</dd>
              <dt className="text-muted">Source</dt>
              <dd className="font-extrabold">{violation.source}</dd>
              <dt className="text-muted">Detected</dt>
              <dd className="font-extrabold">{violation.detected_at}</dd>
              <dt className="text-muted">Evidence ref</dt>
              <dd>
                <code className="text-ink">{violation.evidence_ref}</code>
              </dd>
              <dt className="text-muted">Raw hash</dt>
              <dd>
                <code className="text-ink">
                  {violation.raw_sha256.slice(0, 24)}…
                </code>
              </dd>
            </dl>
          </div>

          {!auditor && (
            <fieldset className="grid gap-3">
              <legend className="text-xs font-black uppercase tracking-wide text-muted">
                Triage action
              </legend>
              <div className="grid grid-cols-2 gap-3">
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  State
                  <select
                    value={state}
                    onChange={(e) => setState(e.target.value as TrackingState)}
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  >
                    {stateOptions}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Actor
                  <input
                    value={actor}
                    onChange={(e) => setActor(e.target.value)}
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Assignee
                  <input
                    value={assignee}
                    onChange={(e) => setAssignee(e.target.value)}
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Due (ISO 8601)
                  <input
                    value={dueAt}
                    onChange={(e) => setDueAt(e.target.value)}
                    placeholder="2026-06-01T00:00:00Z"
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
              </div>
              <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                Note
                <textarea
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
                />
              </label>
            </fieldset>
          )}

          <EntityTagsEditor
            entityType="violation"
            entityId={violation.violation_id}
          />

          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-wide text-muted">
              <History className="h-3 w-3" /> Triage history · {history.length}{" "}
              events
            </div>
            <div className="grid gap-2">
              {history.length === 0 && (
                <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
                  No triage events recorded yet.
                </div>
              )}
              {history.map((event) => (
                <div
                  key={event.tracking_id}
                  className="rounded-lg border border-line p-3 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Badge tone={STATE_TONE[event.state] ?? "default"}>
                      {event.state}
                    </Badge>
                    <span className="text-muted">{event.occurred_at}</span>
                  </div>
                  <div className="mt-1 text-muted">
                    actor <b className="text-ink">{event.actor}</b>
                    {event.assignee && (
                      <>
                        {" "}
                        · assignee <b className="text-ink">{event.assignee}</b>
                      </>
                    )}
                    {event.due_at && (
                      <>
                        {" "}
                        · due <b className="text-ink">{event.due_at}</b>
                      </>
                    )}
                  </div>
                  {event.note && (
                    <div className="mt-1 text-ink">{event.note}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}
