/** Human-facing console copy — agentless read-only connect path. */

export const CONNECT_FLOW = {
  cycle: "Connect → test → enable → sync → evaluate",
  agentless: "Read-only API access — no customer evidence lake build required.",
  test: "Test connection",
  enable: "Enable source",
  sync: "Sync evidence",
  emptySources:
    "No sources connected yet. Start with a read-only cloud or IdP link.",
  emptyEvidence:
    "Connect and sync a source, or point at an existing evidence lake.",
  emptyActivity:
    "No activity yet. Connect a source, sync evidence, or triage a finding.",
} as const;
