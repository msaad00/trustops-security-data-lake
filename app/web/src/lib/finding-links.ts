import type { RemediationTask, Violation } from "@/lib/api/types";

const PRIORITY_BY_SEVERITY: Record<string, RemediationTask["priority"]> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "low",
};

export function priorityForSeverity(
  severity: string | null | undefined,
): RemediationTask["priority"] {
  return PRIORITY_BY_SEVERITY[severity ?? ""] ?? "medium";
}

export function controlGraphFocusHref(controlId: string): string {
  return `/graph/?focus=${encodeURIComponent(`control:${controlId}`)}`;
}

export function findingHref(violationId: string): string {
  return `/violations/?id=${encodeURIComponent(violationId)}`;
}

export function taskFromFindingHref(finding: Violation, title: string): string {
  const params = new URLSearchParams({
    tab: "tasks",
    control: finding.control_id,
    finding: finding.violation_id,
    title,
    priority: priorityForSeverity(finding.severity),
  });
  const owner = finding.asset_owner?.trim();
  if (owner) params.set("assignee", owner);
  return `/remediation/?${params}`;
}

// Only http(s) links are rendered as anchors; anything else stays plain text
// so a stored note can never become a javascript: or data: link.
export function safeHttpUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    return url.protocol === "http:" || url.protocol === "https:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}
