"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import { LIVE, STALE, type Opts } from "./shared";
import type { AgentRun, CreateAgentRunPayload } from "../types";

export function useAgentRuns(opts?: Opts<AgentRun[]>) {
  return useQuery({
    queryKey: ["agent-runs"],
    queryFn: () => api.agentRuns("?limit=25"),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useAgentRun(runId: string | null, opts?: Opts<AgentRun>) {
  return useQuery({
    queryKey: ["agent-run", runId],
    queryFn: () => api.agentRun(runId as string),
    enabled: Boolean(runId),
    staleTime: STALE,
    ...opts,
  });
}

export function useCreateAgentRunMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAgentRunPayload) => api.createAgentRun(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent-runs"] });
      qc.invalidateQueries({ queryKey: ["agent-run"] });
    },
  });
}

export function useApproveAgentDecisionMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      runId,
      decisionIndex,
      note = "",
    }: {
      runId: string;
      decisionIndex: number;
      note?: string;
    }) => api.approveAgentDecision(runId, decisionIndex, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent-runs"] });
      qc.invalidateQueries({ queryKey: ["agent-run"] });
      qc.invalidateQueries({ queryKey: ["remediation", "evidence-requests"] });
      qc.invalidateQueries({ queryKey: ["remediation", "tasks"] });
      qc.invalidateQueries({ queryKey: ["snapshots"] });
    },
  });
}
