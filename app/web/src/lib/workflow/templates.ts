/**
 * Pre-built workflow templates the user can clone into the canvas with one
 * click. Each template is a `{ nodes, edges }` pair ready to drop into the
 * editor; nothing references the persisted workflow_id so cloning creates a
 * fresh story.
 */

import type { WorkflowEdge, WorkflowNode } from "@/lib/api/types";

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  tags: string[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

const node = (
  id: string,
  node_type: string,
  params: Record<string, unknown>,
  x: number,
  y: number,
): WorkflowNode => ({
  id,
  node_type,
  params,
  position: { x, y },
});

const edge = (
  source: string,
  target: string,
  condition: "always" | "passed" | "failed" = "always",
): WorkflowEdge => ({
  source,
  target,
  condition,
});

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "freeze-snapshot-on-critical",
    name: "Freeze snapshot on critical violation",
    description:
      "When evidence lands and any control's latest test is failing, freeze a point-in-time snapshot for the audit trail.",
    tags: ["audit", "snapshot"],
    nodes: [
      node("t", "trigger.evidence_changed", {}, 120, 140),
      node("c", "check.control_pass", { control_id: "SOC2-CC6.1" }, 340, 140),
      node(
        "s",
        "action.snapshot",
        { reason: "auto: control failed after evidence change" },
        560,
        140,
      ),
    ],
    edges: [edge("t", "c"), edge("c", "s", "failed")],
  },
  {
    id: "auto-assign-new-violation",
    name: "Auto-assign a new high-severity violation",
    description:
      "Triage every new violation by assigning it to the asset owner and flipping its state to triaged.",
    tags: ["triage"],
    nodes: [
      node("t", "trigger.evidence_changed", {}, 120, 140),
      node(
        "a",
        "action.assign_owner",
        {
          violation_id: "{{t.output.matched ? 'auto' : ''}}",
          assignee: "appsec",
          state: "triaged",
          note: "auto-assigned by workflow",
        },
        380,
        140,
      ),
    ],
    edges: [edge("t", "a", "passed")],
  },
  {
    id: "weekly-trust-digest",
    name: "Weekly trust digest",
    description:
      "Cron every week, freeze a snapshot for the audit log so the trust digest has a stable reference.",
    tags: ["scheduled", "snapshot"],
    nodes: [
      node("t", "trigger.cron", { schedule: "@weekly" }, 120, 140),
      node("s", "action.snapshot", { reason: "weekly_trust_digest" }, 380, 140),
    ],
    edges: [edge("t", "s")],
  },
  {
    id: "evidence-missing-alert",
    name: "Evidence missing alert",
    description: "SOC 2 CC6.1 evidence check; snapshot if missing.",
    tags: ["scheduled", "alert"],
    nodes: [
      node("t", "trigger.cron", { schedule: "@hourly" }, 90, 220),
      node(
        "c",
        "check.evidence_exists",
        { control_id: "SOC2-CC6.1", minimum: 3 },
        350,
        220,
      ),
      node(
        "a",
        "action.assign_owner",
        {
          violation_id: "SOC2-CC6.1:evidence_gap",
          assignee: "compliance-owner",
          state: "triaged",
          note: "Evidence gap from {{c.output.matched_count}} records; minimum {{c.output.minimum}} required.",
        },
        640,
        120,
      ),
      node(
        "s",
        "action.snapshot",
        { reason: "soc2_cc6_1_evidence_gap" },
        640,
        310,
      ),
    ],
    edges: [edge("t", "c"), edge("c", "a", "failed"), edge("c", "s", "failed")],
  },
  {
    id: "framework-readiness-drift",
    name: "Framework readiness drift",
    description:
      "Daily cron checks the headline control test; if it fails, freeze a snapshot and assign the asset owner.",
    tags: ["scheduled", "framework"],
    nodes: [
      node("t", "trigger.cron", { schedule: "@daily" }, 120, 140),
      node(
        "c",
        "check.control_pass",
        { control_id: "NIST-AI-RMF-MEASURE-2.7" },
        340,
        140,
      ),
      node("s", "action.snapshot", { reason: "framework_drift" }, 560, 80),
      node(
        "a",
        "action.assign_owner",
        {
          violation_id: "NIST-AI-RMF-MEASURE-2.7:framework_drift",
          assignee: "ai-security",
          state: "in_progress",
          note: "framework drift — owner review required",
        },
        560,
        220,
      ),
    ],
    edges: [edge("t", "c"), edge("c", "s", "failed"), edge("c", "a", "failed")],
  },
];
