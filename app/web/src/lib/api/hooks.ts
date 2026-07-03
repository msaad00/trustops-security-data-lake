"use client";

import { useEffect, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api, bootstrapAssessment, type SnapshotSummary } from "./client";
import type {
  AccessReviewCampaign,
  AccessReviewDecision,
  AccessReviewStatus,
  AgentRun,
  Assessment,
  AssetRisk,
  AuthMethods,
  AuthWhoami,
  ComplianceGraph,
  ConfigurePayload,
  ConnectorRun,
  ConnectorView,
  ControlPosture,
  ControlRemediation,
  ControlTest,
  Crosswalk,
  EvidenceFreshness,
  EntityTag,
  FrameworkView,
  FrameworkDetail,
  IngestionStatus,
  NormalizedEvent,
  PocReadiness,
  ProbePayload,
  DiscoverPayload,
  SavedView,
  Tag,
  TrackingEvent,
  TriagePayload,
  VerifyResult,
  Violation,
  RemediationTask,
  EvidenceRequestItem,
  ControlExceptionItem,
  CreateAgentRunPayload,
  Risk,
  PolicyDocument,
  PolicyTemplateSummary,
  VendorAssessment,
  VendorAssessmentStatus,
  VendorQuestionnaireTemplateSummary,
} from "./types";

const STALE = 15_000;
// Poll interval for "continuous" surfaces so posture/violations/connectors
// refresh on their own. Callers can override via `opts.refetchInterval`.
const LIVE = 15_000;

type Opts<T> = Omit<UseQueryOptions<T>, "queryKey" | "queryFn">;

export function useHealth(opts?: Opts<{ ok: boolean }>) {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      try {
        const h = await api.health();
        return { ok: Boolean(h.ok) };
      } catch {
        return { ok: false };
      }
    },
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function usePosture(opts?: Opts<Assessment>) {
  const initialData =
    typeof window !== "undefined"
      ? (bootstrapAssessment() ?? undefined)
      : undefined;
  return useQuery({
    queryKey: ["posture", "current"],
    queryFn: api.posture,
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    initialData,
    ...opts,
  });
}

export function useIngestionStatus(opts?: Opts<IngestionStatus>) {
  return useQuery({
    queryKey: ["ingestion", "status"],
    queryFn: api.ingestionStatus,
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function usePocReadiness(opts?: Opts<PocReadiness>) {
  return useQuery({
    queryKey: ["platform", "poc-readiness"],
    queryFn: api.pocReadiness,
    staleTime: STALE,
    refetchInterval: LIVE,
    retry: false,
    ...opts,
  });
}

export function useAuthMethods(opts?: Opts<AuthMethods>) {
  return useQuery({
    queryKey: ["auth", "methods"],
    queryFn: api.authMethods,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useAuthWhoami(opts?: Opts<AuthWhoami>) {
  return useQuery({
    queryKey: ["auth", "whoami"],
    queryFn: api.authWhoami,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useControls(opts?: Opts<ControlPosture[]>) {
  return useQuery({
    queryKey: ["controls"],
    queryFn: async () => (await api.controls()).controls ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useControlTests(opts?: Opts<ControlTest[]>) {
  return useQuery({
    queryKey: ["control-tests"],
    queryFn: async () => (await api.controlTests()).control_tests ?? [],
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useViolations(opts?: Opts<Violation[]>) {
  return useQuery({
    queryKey: ["violations"],
    queryFn: async () => (await api.violations()).violations ?? [],
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useEvidence(opts?: Opts<NormalizedEvent[]>) {
  return useQuery({
    queryKey: ["evidence"],
    queryFn: async () => (await api.evidence()).evidence ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useEvidenceFreshness(opts?: Opts<EvidenceFreshness[]>) {
  return useQuery({
    queryKey: ["evidence", "freshness"],
    queryFn: () => api.evidenceFreshness(),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useAssets(opts?: Opts<AssetRisk[]>) {
  return useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await api.assets()).assets ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useSnapshots(opts?: Opts<SnapshotSummary[]>) {
  return useQuery({
    queryKey: ["snapshots"],
    queryFn: async () => (await api.listSnapshots()).snapshots ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useTracking(violationId: string | null) {
  return useQuery({
    queryKey: ["tracking", violationId],
    queryFn: async () => {
      if (!violationId)
        return { events: [] as TrackingEvent[], current_state: "open" };
      const data = await api.getTracking(violationId);
      return { events: data.events, current_state: data.current_state };
    },
    enabled: Boolean(violationId),
    staleTime: 5_000,
  });
}

export function useTriageMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      violationId,
      payload,
    }: {
      violationId: string;
      payload: TriagePayload;
    }) => api.triage(violationId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tracking", vars.violationId] });
    },
  });
}

export function useVerifyMutation() {
  return useMutation({
    mutationFn: (eventId: string) => api.verifyEvidence(eventId),
  });
}

export function useSnapshotMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => api.createSnapshot(reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["snapshots"] });
    },
  });
}

export function useConnectors(opts?: Opts<ConnectorView[]>) {
  return useQuery({
    queryKey: ["connectors"],
    queryFn: async () => (await api.listConnectors()).connectors ?? [],
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useConnectorRuns(id: string | null) {
  return useQuery({
    queryKey: ["connector-runs", id],
    queryFn: async () => {
      if (!id) return [] as ConnectorRun[];
      return (await api.connectorRuns(id)).runs ?? [];
    },
    enabled: Boolean(id),
    staleTime: 5_000,
  });
}

export function useConfigureMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ConfigurePayload }) =>
      api.configureConnector(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

export function useCloudLinkStartMutation() {
  return useMutation({
    mutationFn: ({
      id,
      publicUrl,
      tenantId,
    }: {
      id: string;
      publicUrl?: string;
      tenantId?: string;
    }) =>
      api.startCloudLink(id, {
        public_url: publicUrl,
        tenant_id: tenantId,
      }),
  });
}

export function useCloudLinkCompleteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      sessionId,
      accountId,
      subscriptionId,
      projectId,
    }: {
      id: string;
      sessionId: string;
      accountId?: string;
      subscriptionId?: string;
      projectId?: string;
    }) =>
      api.completeCloudLink(id, {
        session_id: sessionId,
        account_id: accountId,
        subscription_id: subscriptionId,
        project_id: projectId,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

export function useProbeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload = {},
    }: {
      id: string;
      payload?: ProbePayload;
    }) => api.probeConnector(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-runs", id] });
    },
  });
}

export function useSyncMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload = {},
    }: {
      id: string;
      payload?: { actor?: string };
    }) => api.syncConnector(id, payload),
    onSuccess: (_data, { id }) => {
      // A sync lands evidence: refresh the connector, its runs, and the posture
      // surfaces so the UI reflects the new state immediately.
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-runs", id] });
      qc.invalidateQueries({ queryKey: ["posture", "current"] });
      qc.invalidateQueries({ queryKey: ["ingestion", "status"] });
      qc.invalidateQueries({ queryKey: ["violations"] });
    },
  });
}

export function useDiscoverMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload = {},
    }: {
      id: string;
      payload?: DiscoverPayload;
    }) => api.discoverConnector(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-runs", id] });
    },
  });
}

export function useFrameworks(opts?: Opts<FrameworkView[]>) {
  return useQuery({
    queryKey: ["frameworks"],
    queryFn: async () => (await api.listFrameworks()).frameworks ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useFrameworkDetail(id: string | null) {
  return useQuery<FrameworkDetail>({
    queryKey: ["framework-detail", id],
    queryFn: () =>
      id ? api.frameworkDetail(id) : Promise.reject(new Error("no id")),
    enabled: Boolean(id),
    staleTime: STALE,
  });
}

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

export function useTrustShares() {
  return useQuery({
    queryKey: ["trust-shares"],
    queryFn: async () => (await api.listTrustShares()).shares ?? [],
    staleTime: 5_000,
  });
}

export function useCreateTrustShare() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTrustShare,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trust-shares"] }),
  });
}

export function useRevokeTrustShare() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.revokeTrustShare,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trust-shares"] }),
  });
}

export function useComplianceGraph() {
  return useQuery({
    queryKey: ["graph"],
    queryFn: api.graph,
    staleTime: STALE,
  });
}

export function useRepositoryGraph() {
  return useQuery({
    queryKey: ["repo-graph"],
    queryFn: api.repoGraph,
    staleTime: STALE,
  });
}

export function useCrosswalk() {
  return useQuery({
    queryKey: ["crosswalk"],
    queryFn: api.crosswalk,
    staleTime: 60_000,
  });
}

export function useReviewedCrosswalk() {
  return useQuery({
    queryKey: ["crosswalk", "reviewed"],
    queryFn: api.reviewedCrosswalk,
    staleTime: 60_000,
  });
}

export function useMappings() {
  return useQuery({
    queryKey: ["mappings"],
    queryFn: async () => (await api.mappings()).mappings ?? [],
    staleTime: 60_000,
  });
}

export function useReadiness() {
  return useQuery({
    queryKey: ["readiness"],
    queryFn: async () => (await api.readiness()).frameworks ?? [],
    staleTime: 30_000,
  });
}

export function useAuditLog(opts?: {
  category?: string;
  actor?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: [
      "audit-log",
      opts?.category ?? null,
      opts?.actor ?? null,
      opts?.limit ?? null,
    ],
    queryFn: async () => (await api.auditLog(opts ?? {})).entries ?? [],
    staleTime: 5_000,
  });
}

export type { VerifyResult, TrackingEvent };

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

export function useCreateAgentRunMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAgentRunPayload) => api.createAgentRun(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-runs"] }),
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
      qc.invalidateQueries({ queryKey: ["remediation", "evidence-requests"] });
      qc.invalidateQueries({ queryKey: ["remediation", "tasks"] });
      qc.invalidateQueries({ queryKey: ["snapshots"] });
    },
  });
}

// --- remediation workflow ---

export function useRemediationTasks(
  query = "",
  opts?: Opts<RemediationTask[]>,
) {
  return useQuery({
    queryKey: ["remediation", "tasks", query],
    queryFn: () => api.remediationTasks(query),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useCreateTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<RemediationTask> & { title: string }) =>
      api.createRemediationTask(payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "tasks"] }),
  });
}

export function useUpdateTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Record<string, unknown>;
    }) => api.updateRemediationTask(id, payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "tasks"] }),
  });
}

export function useEvidenceRequests(opts?: Opts<EvidenceRequestItem[]>) {
  return useQuery({
    queryKey: ["remediation", "evidence-requests"],
    queryFn: api.evidenceRequests,
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateEvidenceRequestMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      control_id: string;
      requested_from?: string;
      note?: string;
    }) => api.createEvidenceRequest(payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "evidence-requests"] }),
  });
}

export function useSetEvidenceRequestStatusMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.setEvidenceRequestStatus(id, status),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "evidence-requests"] }),
  });
}

export function useControlExceptions(opts?: Opts<ControlExceptionItem[]>) {
  return useQuery({
    queryKey: ["remediation", "exceptions"],
    queryFn: api.controlExceptions,
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateControlExceptionMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      control_id: string;
      reason?: string;
      expires_at?: string | null;
    }) => api.createControlException(payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "exceptions"] }),
  });
}

export function useRevokeControlExceptionMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.revokeControlException(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["remediation", "exceptions"] }),
  });
}

// --- risk register ---

export function useRisks(query = "", opts?: Opts<Risk[]>) {
  return useQuery({
    queryKey: ["risks", query],
    queryFn: () => api.risks(query),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useCreateRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Risk> & { title: string }) =>
      api.createRisk(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

export function useUpdateRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Record<string, unknown>;
    }) => api.updateRisk(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

export function useDeleteRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteRisk(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

// --- tags + saved views ---

export function useTags(opts?: Opts<Tag[]>) {
  return useQuery({
    queryKey: ["tags"],
    queryFn: api.listTags,
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; color?: string }) =>
      api.createTag(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useDeleteTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) => api.deleteTag(tagId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useAttachTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      tag_id: string;
      entity_type: string;
      entity_id: string;
    }) => api.attachTag(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tags"] });
      qc.invalidateQueries({
        queryKey: ["tags-for", vars.entity_type, vars.entity_id],
      });
    },
  });
}

export function useDetachTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      tag_id: string;
      entity_type: string;
      entity_id: string;
    }) => api.detachTag(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tags"] });
      qc.invalidateQueries({
        queryKey: ["tags-for", vars.entity_type, vars.entity_id],
      });
    },
  });
}

export function useTagsForEntity(
  entityType: string | null,
  entityId: string | null,
  opts?: Opts<Tag[]>,
) {
  return useQuery({
    queryKey: ["tags-for", entityType, entityId],
    queryFn: async () => {
      if (!entityType || !entityId) return [] as Tag[];
      return api.tagsForEntity(entityType, entityId);
    },
    enabled: Boolean(entityType && entityId),
    staleTime: STALE,
    ...opts,
  });
}

export function useSavedViews(surface?: string, opts?: Opts<SavedView[]>) {
  return useQuery({
    queryKey: ["saved-views", surface ?? null],
    queryFn: () => api.listSavedViews(surface),
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useCreateSavedViewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      surface: string;
      name: string;
      filters: Record<string, unknown>;
    }) => api.createSavedView(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["saved-views", vars.surface] });
      qc.invalidateQueries({ queryKey: ["saved-views", null] });
    },
  });
}

export function useDeleteSavedViewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ viewId, surface }: { viewId: string; surface: string }) =>
      api.deleteSavedView(viewId).then((r) => ({ ...r, surface })),
    onSuccess: (_data) => {
      qc.invalidateQueries({ queryKey: ["saved-views"] });
    },
  });
}

export type { Tag, EntityTag, SavedView };

// --- metrics & insights ---

export function useInsightsTimeseries(limit = 90) {
  return useQuery({
    queryKey: ["insights", "timeseries", limit],
    queryFn: () => api.insightsTimeseries(limit),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useInsightsRemediation() {
  return useQuery({
    queryKey: ["insights", "remediation"],
    queryFn: api.insightsRemediation,
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useCaptureMetricMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.insightsCapture,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["insights", "timeseries"] }),
  });
}

// Continuous-eval: push posture updates via SSE into the query cache so the
// console is live (poll stays as the fallback when EventSource is unavailable).
export function usePostureStream(): { connected: boolean } {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined")
      return;
    const es = new EventSource("/api/v1/stream", { withCredentials: true });
    es.addEventListener("posture", (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Assessment;
        qc.setQueryData(["posture", "current"], data);
      } catch {
        /* ignore malformed frame */
      }
    });
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, [qc]);
  return { connected };
}

export function useAccessReviews(query = "") {
  return useQuery({
    queryKey: ["access-reviews", query],
    queryFn: () => api.accessReviews(query),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useAccessReview(id: string | null) {
  return useQuery({
    queryKey: ["access-review", id],
    queryFn: () => api.accessReview(id as string),
    enabled: Boolean(id),
    staleTime: STALE,
  });
}

export function useAccessReviewItems(id: string | null, query = "") {
  return useQuery({
    queryKey: ["access-review-items", id, query],
    queryFn: () => api.accessReviewItems(id as string, query),
    enabled: Boolean(id),
    staleTime: STALE,
  });
}

export function useAccessReviewCoverage() {
  return useQuery({
    queryKey: ["access-review-coverage"],
    queryFn: () => api.accessReviewCoverage(),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useCreateAccessReviewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string } & Partial<AccessReviewCampaign>) =>
      api.createAccessReview(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["access-reviews"] }),
  });
}

export function useSetAccessReviewStatusMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; status: AccessReviewStatus }) =>
      api.setAccessReviewStatus(vars.id, vars.status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["access-reviews"] });
      qc.invalidateQueries({ queryKey: ["access-review-coverage"] });
    },
  });
}

export function useSeedAccessReviewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.seedAccessReview(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["access-review-items", id] });
      qc.invalidateQueries({ queryKey: ["access-review", id] });
    },
  });
}

export function useDecideAccessReviewItemMutation(campaignId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      itemId: string;
      decision: AccessReviewDecision;
      note?: string;
    }) => api.decideAccessReviewItem(vars.itemId, vars.decision, vars.note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["access-review-items", campaignId] });
      qc.invalidateQueries({ queryKey: ["access-review", campaignId] });
      qc.invalidateQueries({ queryKey: ["access-review-coverage"] });
    },
  });
}

export function useControlRemediation(controlId: string | null) {
  return useQuery<ControlRemediation>({
    queryKey: ["control-remediation", controlId],
    queryFn: () => api.controlRemediation(controlId as string),
    enabled: Boolean(controlId),
    staleTime: 60_000,
  });
}

export function usePolicyTemplates() {
  return useQuery({
    queryKey: ["policy-templates"],
    queryFn: () => api.policyTemplates(),
    staleTime: STALE,
  });
}

export function useVendorQuestionnaires() {
  return useQuery({
    queryKey: ["vendor-questionnaires"],
    queryFn: () => api.vendorQuestionnaires(),
    staleTime: STALE,
  });
}

export function usePolicies(query = "") {
  return useQuery({
    queryKey: ["policies", query],
    queryFn: () => api.policies(query),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useVendorAssessments(query = "") {
  return useQuery({
    queryKey: ["vendor-assessments", query],
    queryFn: () => api.vendorAssessments(query),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function usePolicy(id: string | null) {
  return useQuery({
    queryKey: ["policy", id],
    queryFn: () => api.policy(id as string),
    enabled: Boolean(id),
    staleTime: STALE,
  });
}

export function useVendorAssessment(id: string | null) {
  return useQuery({
    queryKey: ["vendor-assessment", id],
    queryFn: () => api.vendorAssessment(id as string),
    enabled: Boolean(id),
    staleTime: STALE,
  });
}

export function usePolicyCoverage() {
  return useQuery({
    queryKey: ["policy-coverage"],
    queryFn: () => api.policyCoverage(),
    staleTime: STALE,
  });
}

export function useAdoptPolicyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      template_id: string;
      variables?: Record<string, string>;
      owner?: string;
    }) => api.adoptPolicy(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["policies"] });
      qc.invalidateQueries({ queryKey: ["policy-coverage"] });
    },
  });
}

export function useCreateVendorAssessmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      vendor_name: string;
      template_id: string;
      owner?: string;
      control_id?: string | null;
    }) => api.createVendorAssessment(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vendor-assessments"] }),
  });
}

export function useUpdatePolicyMutation(policyId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.updatePolicy>[1]) =>
      api.updatePolicy(policyId as string, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["policies"] });
      qc.invalidateQueries({ queryKey: ["policy", policyId] });
    },
  });
}

export function useUpdateVendorAssessmentMutation(assessmentId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.updateVendorAssessment>[1]) =>
      api.updateVendorAssessment(assessmentId as string, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vendor-assessments"] });
      qc.invalidateQueries({ queryKey: ["vendor-assessment", assessmentId] });
    },
  });
}

export function usePublishPolicyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.publishPolicy(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["policies"] });
      qc.invalidateQueries({ queryKey: ["policy", id] });
      qc.invalidateQueries({ queryKey: ["policy-coverage"] });
    },
  });
}

export function useSubmitVendorAssessmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.submitVendorAssessment(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["vendor-assessments"] });
      qc.invalidateQueries({ queryKey: ["vendor-assessment", id] });
    },
  });
}
