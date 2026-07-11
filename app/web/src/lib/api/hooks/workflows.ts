"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import { STALE } from "./shared";

export function useWorkflows() {
  return useQuery({
    queryKey: ["workflows"],
    queryFn: async () => (await api.listWorkflows()).workflows ?? [],
    staleTime: STALE,
  });
}

export function useWorkflow(id: string | null) {
  return useQuery({
    queryKey: ["workflow", id],
    queryFn: () =>
      id ? api.getWorkflow(id) : Promise.reject(new Error("no id")),
    enabled: Boolean(id),
    staleTime: 5_000,
  });
}

export function useWorkflowRuns(id: string | null) {
  return useQuery({
    queryKey: ["workflow-runs", id],
    queryFn: async () => (id ? ((await api.workflowRuns(id)).runs ?? []) : []),
    enabled: Boolean(id),
    staleTime: 5_000,
  });
}

export function useActionCatalog() {
  return useQuery({
    queryKey: ["action-catalog"],
    queryFn: async () => (await api.actionCatalog()).actions ?? [],
    staleTime: 60_000,
  });
}

export function useSaveWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.saveWorkflow,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
    },
  });
}

export function useRunWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dry_run }: { id: string; dry_run?: boolean }) =>
      api.runWorkflow(id, { dry_run }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["workflow-runs", vars.id] });
    },
  });
}

export function useRetryWorkflowRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.retryWorkflowRun,
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ["workflow-runs", data.run.workflow_id],
      });
    },
  });
}

export function useApproveWorkflowRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, note }: { runId: string; note?: string }) =>
      api.approveWorkflowRun(runId, note),
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ["workflow-runs", data.run.workflow_id],
      });
    },
  });
}

export function useRejectWorkflowRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, note }: { runId: string; note?: string }) =>
      api.rejectWorkflowRun(runId, note),
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ["workflow-runs", data.run.workflow_id],
      });
    },
  });
}

export function useTestAction() {
  return useMutation({
    mutationFn: ({
      node_type,
      params,
    }: {
      node_type: string;
      params: Record<string, unknown>;
    }) => api.testAction(node_type, params),
  });
}
