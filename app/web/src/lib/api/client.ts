import { isAuditorMode } from "@/lib/state/auditor";
import type {
  AccessReviewCampaign,
  AccessReviewCoverage,
  AccessReviewDecision,
  AccessReviewItem,
  AccessReviewSeedResult,
  AccessReviewStatus,
  ActionSpec,
  AgentRun,
  Assessment,
  AssetRisk,
  AuthMethods,
  AuthApiKey,
  AuthUser,
  AuthWhoami,
  CreatedAuthApiKey,
  CreateAuthKeyPayload,
  CreateInvitePayload,
  TenantInvite,
  UpdateAuthUserPayload,
  ControlExceptionItem,
  EvidenceRequestItem,
  PostureMetricPoint,
  PlatformPricing,
  PlatformUsage,
  PoamItem,
  PoamSyncResult,
  ProbePayload,
  RemediationInsights,
  RemediationTask,
  Risk,
  AuditLogEntry,
  ComplianceGraph,
  ConfigurePayload,
  ConnectorRun,
  ConnectorView,
  ControlPosture,
  ControlRemediation,
  ControlTest,
  ControlArticleMapping,
  DiscoverPayload,
  Crosswalk,
  CreateAgentRunPayload,
  EvidenceFreshness,
  EvidenceFreshnessSummary,
  EscalateFreshnessResult,
  EntityTag,
  FrameworkReadiness,
  FrameworkReadinessTrends,
  FrameworkDetail,
  FrameworkEquivalence,
  FrameworkView,
  ReviewedCrosswalk,
  Health,
  IngestionStatus,
  LakeEvalRun,
  NormalizedEvent,
  PocReadiness,
  PlatformJobsFeed,
  AuditReadiness,
  AiGovernance,
  AiInventoryItem,
  PolicyDocument,
  PolicyAcknowledgment,
  PolicyAttestationSummary,
  PolicyTemplate,
  PolicyTemplateSummary,
  PolicyCoverage,
  SavedView,
  SlaHeatmap,
  SnapshotResponse,
  SnapshotSummary,
  SnapshotDetail,
  CloudLinkSession,
  CloudLinkCompleteResult,
  Tag,
  SprsReport,
  TrackingEvent,
  TriagePayload,
  TrustShare,
  VerifyResult,
  VendorAssessment,
  VendorAssessmentStatus,
  VendorQuestionnaireTemplate,
  VendorQuestionnaireTemplateSummary,
  Violation,
  Workflow,
  WorkflowEdge,
  WorkflowNode,
  WorkflowRun,
} from "./types";

const BASE = "/api";
const LOGIN_PATH = "/console/login";

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const pathname = window.location.pathname.replace(/\/$/, "");
  if (pathname === LOGIN_PATH) return;
  const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  window.location.assign(
    `${LOGIN_PATH}?return_to=${encodeURIComponent(returnTo)}`,
  );
}

function headers(): Record<string, string> {
  const out: Record<string, string> = { "content-type": "application/json" };
  if (isAuditorMode()) out["X-Trust-Role"] = "auditor";
  return out;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    credentials: "same-origin",
    headers: headers(),
  });
  if (res.status === 401) redirectToLogin();
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: headers(),
    body: JSON.stringify(body ?? {}),
  });
  if (res.status === 401) redirectToLogin();
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const reason =
      (payload as { reason?: string }).reason ??
      (payload as { errors?: Array<{ detail?: string }> }).errors?.[0]
        ?.detail ??
      `${res.status}`;
    throw new Error(`${path} -> ${reason}`);
  }
  return (await res.json()) as T;
}

async function mutate<T>(
  path: string,
  method: "PATCH" | "DELETE",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) redirectToLogin();
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const reason =
      (payload as { reason?: string }).reason ??
      (payload as { errors?: Array<{ detail?: string }> }).errors?.[0]
        ?.detail ??
      `${res.status}`;
    throw new Error(`${path} -> ${reason}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => get<Health>("/healthz"),
  authMethods: () =>
    get<{ data: AuthMethods }>("/v1/auth/methods").then((body) => body.data),
  authWhoami: () =>
    get<{ data: AuthWhoami }>("/v1/auth/whoami").then((body) => body.data),
  authKeys: () =>
    get<{ data: AuthApiKey[]; meta?: { count?: number } }>(
      "/v1/auth/keys",
    ).then((body) => body.data),
  createAuthKey: (payload: CreateAuthKeyPayload) =>
    post<{ data: CreatedAuthApiKey }>("/v1/auth/keys", payload).then(
      (body) => body.data,
    ),
  revokeAuthKey: (keyId: string) =>
    mutate<{ data: { id: string; revoked: boolean } }>(
      `/v1/auth/keys/${encodeURIComponent(keyId)}`,
      "DELETE",
    ).then((body) => body.data),
  authUsers: () =>
    get<{ data: AuthUser[]; meta?: { count?: number } }>("/v1/auth/users").then(
      (body) => body.data,
    ),
  updateAuthUser: (userId: string, payload: UpdateAuthUserPayload) =>
    mutate<{ data: AuthUser }>(
      `/v1/auth/users/${encodeURIComponent(userId)}`,
      "PATCH",
      payload,
    ).then((body) => body.data),
  sessionFromKey: (apiKey: string) =>
    post<{ data: AuthWhoami }>("/v1/auth/session-from-key", {
      api_key: apiKey,
    }).then((body) => body.data),
  invites: () =>
    get<{ data: TenantInvite[]; meta?: { count?: number } }>(
      "/v1/invites",
    ).then((body) => body.data),
  createInvite: (payload: CreateInvitePayload) =>
    post<{ data: TenantInvite }>("/v1/invites", payload).then(
      (body) => body.data,
    ),
  acceptInvite: (payload: { token: string; display_name?: string }) =>
    post<{ data: { email?: string; tenant_slug?: string } }>(
      "/v1/invites/accept",
      payload,
    ).then((body) => body.data),
  signup: (payload: {
    org_slug: string;
    org_name: string;
    admin_email: string;
    admin_name?: string;
    plan_tier?: string;
  }) =>
    post<{ data: Record<string, unknown> }>("/v1/signup", payload).then(
      (body) => body.data,
    ),
  authLogout: () =>
    post<{ data: { ok: boolean } }>("/v1/auth/logout", {}).then(
      (body) => body.data,
    ),
  authFreshnessSummary: () =>
    get<{ data: EvidenceFreshnessSummary }>(
      "/v1/evidence/freshness/summary",
    ).then((body) => body.data),
  escalateStaleEvidence: (limit = 10) =>
    post<{ data: EscalateFreshnessResult }>("/v1/evidence/freshness/escalate", {
      limit,
      statuses: ["stale", "expired", "missing"],
    }).then((body) => body.data),
  pocReadiness: () =>
    get<{ data: PocReadiness }>("/v1/platform/poc-readiness").then(
      (body) => body.data,
    ),
  auditReadiness: () =>
    get<{ data: AuditReadiness }>("/v1/platform/audit-readiness").then(
      (body) => body.data,
    ),
  aiGovernance: () =>
    get<{ data: AiGovernance }>("/v1/platform/ai-governance").then(
      (body) => body.data,
    ),
  aiInventory: (query = "") =>
    get<{ data: AiInventoryItem[] }>(
      `/v1/platform/ai-governance/inventory${query}`,
    ).then((body) => body.data),
  remediationTasks: (query = "") =>
    get<{ data: RemediationTask[] }>(`/v1/remediation/tasks${query}`).then(
      (b) => b.data,
    ),
  createRemediationTask: (
    payload: Partial<RemediationTask> & { title: string },
  ) =>
    post<{ data: RemediationTask }>("/v1/remediation/tasks", payload).then(
      (b) => b.data,
    ),
  updateRemediationTask: (id: string, payload: Record<string, unknown>) =>
    mutate<{ data: RemediationTask }>(
      `/v1/remediation/tasks/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ).then((b) => b.data),
  evidenceRequests: () =>
    get<{ data: EvidenceRequestItem[] }>(
      "/v1/remediation/evidence-requests",
    ).then((b) => b.data),
  createEvidenceRequest: (payload: {
    control_id: string;
    requested_from?: string;
    note?: string;
  }) =>
    post<{ data: EvidenceRequestItem }>(
      "/v1/remediation/evidence-requests",
      payload,
    ).then((b) => b.data),
  setEvidenceRequestStatus: (id: string, status: string) =>
    mutate<{ data: EvidenceRequestItem }>(
      `/v1/remediation/evidence-requests/${encodeURIComponent(id)}`,
      "PATCH",
      { status },
    ).then((b) => b.data),
  controlExceptions: () =>
    get<{ data: ControlExceptionItem[] }>("/v1/remediation/exceptions").then(
      (b) => b.data,
    ),
  createControlException: (payload: {
    control_id: string;
    reason?: string;
    expires_at?: string | null;
  }) =>
    post<{ data: ControlExceptionItem }>(
      "/v1/remediation/exceptions",
      payload,
    ).then((b) => b.data),
  revokeControlException: (id: string) =>
    mutate<{ data: ControlExceptionItem }>(
      `/v1/remediation/exceptions/${encodeURIComponent(id)}`,
      "DELETE",
    ).then((b) => b.data),
  risks: (query = "") =>
    get<{ data: Risk[] }>(`/v1/risks${query}`).then((b) => b.data),
  createRisk: (payload: Partial<Risk> & { title: string }) =>
    post<{ data: Risk }>("/v1/risks", payload).then((b) => b.data),
  updateRisk: (id: string, payload: Record<string, unknown>) =>
    mutate<{ data: Risk }>(
      `/v1/risks/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ).then((b) => b.data),
  deleteRisk: (id: string) =>
    mutate<{ data: { id: string; deleted: boolean } }>(
      `/v1/risks/${encodeURIComponent(id)}`,
      "DELETE",
    ).then((b) => b.data),
  posture: () => get<Assessment>("/posture/current"),
  ingestionStatus: () =>
    get<{ data: IngestionStatus }>("/v1/ingestion/status").then(
      (body) => body.data,
    ),
  platformJobs: (query = "") =>
    get<{ data: PlatformJobsFeed }>(`/v1/platform/jobs${query}`).then(
      (body) => body.data,
    ),
  controls: () => get<{ controls: ControlPosture[] }>("/controls"),
  controlTests: () =>
    get<{ count: number; control_tests: ControlTest[] }>("/control-tests"),
  violations: () =>
    get<{ count: number; violations: Violation[] }>("/violations"),
  evidence: () =>
    get<{ count: number; evidence: NormalizedEvent[] }>("/evidence"),
  evidenceFreshness: (query = "") =>
    get<{ data: EvidenceFreshness[] }>(`/v1/evidence/freshness${query}`).then(
      (b) => b.data,
    ),
  assets: () => get<{ assets: AssetRisk[] }>("/assets"),
  createSnapshot: (reason: string) =>
    post<SnapshotResponse>("/snapshots", { reason }),
  listSnapshots: () =>
    get<{ count: number; snapshots: SnapshotSummary[] }>("/snapshots"),
  getSnapshotDetail: (snapshotId: string) =>
    get<{ data: SnapshotDetail }>(
      `/v1/snapshots/${encodeURIComponent(snapshotId)}`,
    ).then((b) => b.data),
  getTracking: (violationId: string) =>
    get<{
      violation_id: string;
      current_state: string;
      events: TrackingEvent[];
    }>(`/violations/${encodeURIComponent(violationId)}/tracking`),
  triage: (violationId: string, payload: TriagePayload) =>
    post<{ event: TrackingEvent }>(
      `/violations/${encodeURIComponent(violationId)}/triage`,
      payload,
    ),
  verifyEvidence: (eventId: string) =>
    post<VerifyResult>(`/evidence/${encodeURIComponent(eventId)}/verify`, {}),
  listConnectors: () =>
    get<{ data: ConnectorView[]; meta: { count: number } }>(
      "/v1/connectors",
    ).then((body) => ({
      count: body.meta.count,
      connectors: body.data,
    })),
  configureConnector: (id: string, payload: ConfigurePayload) =>
    post<{ data: Record<string, unknown> }>(
      `/v1/connectors/${encodeURIComponent(id)}/configure`,
      payload,
    ).then((body) => ({ event: body.data })),
  probeConnector: (id: string, payload: ProbePayload = {}) =>
    post<{ data: ConnectorRun }>(
      `/v1/connectors/${encodeURIComponent(id)}/probe`,
      payload,
    ).then((body) => ({ run: body.data })),
  syncConnector: (
    id: string,
    payload: { actor?: string; materialize?: boolean } = {},
  ) =>
    post<{
      data: {
        connector_id: string;
        result: string;
        evidence_count: number | null;
        materialized: boolean;
        run: ConnectorRun;
      };
    }>(`/v1/connectors/${encodeURIComponent(id)}/sync`, payload).then(
      (body) => body.data,
    ),
  runLakeEval: (payload: { actor?: string } = {}) =>
    post<{
      data: {
        result: string;
        mode: string;
        duration_ms: number;
        error: string | null;
        strategy: Record<string, unknown>;
      };
    }>("/v1/ingestion/eval", payload).then((body) => body.data),
  listEvalRuns: (limit = 10) =>
    get<{ data: LakeEvalRun[] }>(
      `/v1/ingestion/eval/runs?limit=${encodeURIComponent(String(limit))}`,
    ).then((body) => body.data),
  runSchedulerTick: () =>
    post<{
      data: {
        fired: Array<Record<string, unknown>>;
        count: number;
      };
    }>("/v1/scheduler/tick", {}).then((body) => body.data),
  discoverConnector: (id: string, payload: DiscoverPayload = {}) =>
    post<{ data: ConnectorRun }>(
      `/v1/connectors/${encodeURIComponent(id)}/discover`,
      payload,
    ).then((body) => ({ run: body.data })),
  startCloudLink: (
    id: string,
    payload: { public_url?: string; tenant_id?: string } = {},
  ) =>
    post<{ data: CloudLinkSession }>(
      `/v1/connectors/${encodeURIComponent(id)}/link/start`,
      payload,
    ).then((body) => body.data),
  completeCloudLink: (
    id: string,
    payload: {
      session_id: string;
      account_id?: string;
      subscription_id?: string;
      project_id?: string;
    },
  ) =>
    post<{ data: CloudLinkCompleteResult }>(
      `/v1/connectors/${encodeURIComponent(id)}/link/complete`,
      payload,
    ).then((body) => body.data),
  connectorRuns: (id: string) =>
    get<{ data: ConnectorRun[]; meta: { connector_id: string } }>(
      `/v1/connectors/${encodeURIComponent(id)}/runs`,
    ).then((body) => ({
      connector_id: body.meta.connector_id,
      runs: body.data,
    })),
  listFrameworks: () =>
    get<{ count: number; frameworks: FrameworkView[] }>("/frameworks"),
  frameworkDetail: (id: string) =>
    get<FrameworkDetail>(`/frameworks/${encodeURIComponent(id)}/detail`),
  listWorkflows: () =>
    get<{ count: number; workflows: Workflow[] }>("/workflows"),
  getWorkflow: (id: string) =>
    get<Workflow>(`/workflows/${encodeURIComponent(id)}`),
  workflowRuns: (id: string) =>
    get<{ workflow_id: string; runs: WorkflowRun[] }>(
      `/workflows/${encodeURIComponent(id)}/runs`,
    ),
  workflowRun: (runId: string) =>
    get<{ run: WorkflowRun }>(`/workflows/runs/${encodeURIComponent(runId)}`),
  actionCatalog: () => get<{ actions: ActionSpec[] }>("/workflows/actions"),
  saveWorkflow: (payload: {
    workflow_id?: string;
    name: string;
    description?: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  }) => post<{ workflow: Workflow }>("/workflows", payload),
  runWorkflow: (id: string, payload: { dry_run?: boolean } = {}) =>
    post<{ run: WorkflowRun }>(
      `/workflows/${encodeURIComponent(id)}/run`,
      payload,
    ),
  retryWorkflowRun: (runId: string) =>
    post<{ run: WorkflowRun }>(
      `/workflows/runs/${encodeURIComponent(runId)}/retry`,
      {},
    ),
  approveWorkflowRun: (runId: string, note = "") =>
    post<{ run: WorkflowRun }>(
      `/workflows/runs/${encodeURIComponent(runId)}/approve`,
      { note },
    ),
  rejectWorkflowRun: (runId: string, note = "") =>
    post<{ run: WorkflowRun }>(
      `/workflows/runs/${encodeURIComponent(runId)}/reject`,
      { note },
    ),
  testAction: (node_type: string, params: Record<string, unknown>) =>
    post<{ output: Record<string, unknown> }>("/workflows/actions/run", {
      node_type,
      params,
    }),
  listTrustShares: () =>
    get<{ count: number; shares: TrustShare[] }>("/trust-shares"),
  createTrustShare: (payload: {
    role: "auditor";
    scope?: "posture_full" | "posture_framework";
    framework_id?: string | null;
    sensitivity_ceiling?: string;
    expires_in_hours: number;
  }) => post<{ share: TrustShare }>("/trust-shares", payload),
  revokeTrustShare: (share_id: string) =>
    post<{ share: TrustShare }>(
      `/trust-shares/${encodeURIComponent(share_id)}/revoke`,
      {},
    ),
  graph: () => get<ComplianceGraph>("/graph"),
  repoGraph: () => get<ComplianceGraph>("/repo-graph"),
  readiness: () =>
    get<{ count: number; frameworks: FrameworkReadiness[] }>("/readiness"),
  crosswalk: () => get<Crosswalk>("/crosswalk"),
  reviewedCrosswalk: () => get<ReviewedCrosswalk>("/crosswalk/reviewed"),
  frameworkEquivalence: () =>
    get<FrameworkEquivalence>("/mappings/equivalence"),
  mappings: () =>
    get<{ count: number; mappings: ControlArticleMapping[] }>("/mappings"),
  auditLog: (
    opts: {
      category?: string;
      actor?: string;
      include_requests?: boolean;
      limit?: number;
    } = {},
  ): Promise<{ count: number; entries: AuditLogEntry[] }> => {
    const qs = new URLSearchParams();
    if (opts.category) qs.set("category", opts.category);
    if (opts.actor) qs.set("actor", opts.actor);
    if (opts.include_requests !== undefined)
      qs.set("include_requests", String(opts.include_requests));
    if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
    const tail = qs.toString();
    return get<{ data: AuditLogEntry[]; meta?: { count?: number } }>(
      `/v1/audit-log${tail ? `?${tail}` : ""}`,
    ).then((body) => ({
      count: body.meta?.count ?? body.data.length,
      entries: body.data,
    }));
  },

  // --- Tags + saved views ---
  listTags: () => get<{ data: Tag[] }>("/v1/tags").then((b) => b.data),
  createTag: (payload: { name: string; color?: string }) =>
    post<{ data: Tag }>("/v1/tags", payload).then((b) => b.data),
  deleteTag: (tagId: string) =>
    mutate<{ data: { id: string; deleted: boolean } }>(
      `/v1/tags/${encodeURIComponent(tagId)}`,
      "DELETE",
    ).then((b) => b.data),
  attachTag: (payload: {
    tag_id: string;
    entity_type: string;
    entity_id: string;
  }) =>
    post<{ data: EntityTag }>("/v1/tags/attach", payload).then((b) => b.data),
  detachTag: (payload: {
    tag_id: string;
    entity_type: string;
    entity_id: string;
  }) =>
    post<{ data: { detached: boolean } }>("/v1/tags/detach", payload).then(
      (b) => b.data,
    ),
  tagsForEntity: (entityType: string, entityId: string) =>
    get<{ data: Tag[] }>(
      `/v1/tags/for?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}`,
    ).then((b) => b.data),
  tagEntities: (tagId: string, entityType?: string) => {
    const params = new URLSearchParams({ tag_id: tagId });
    if (entityType) params.set("entity_type", entityType);
    return get<{ data: string[] }>(
      `/v1/tags/entities?${params.toString()}`,
    ).then((b) => b.data);
  },
  listSavedViews: (surface?: string) => {
    const qs = surface ? `?surface=${encodeURIComponent(surface)}` : "";
    return get<{ data: SavedView[] }>(`/v1/saved-views${qs}`).then(
      (b) => b.data,
    );
  },
  createSavedView: (payload: {
    surface: string;
    name: string;
    filters: Record<string, unknown>;
  }) =>
    post<{ data: SavedView }>("/v1/saved-views", payload).then((b) => b.data),
  deleteSavedView: (viewId: string) =>
    mutate<{ data: { id: string; deleted: boolean } }>(
      `/v1/saved-views/${encodeURIComponent(viewId)}`,
      "DELETE",
    ).then((b) => b.data),
  insightsTimeseries: (limit = 90) =>
    get<{ data: PostureMetricPoint[] }>(
      `/v1/insights/timeseries?limit=${limit}`,
    ).then((b) => b.data),
  insightsRemediation: () =>
    get<{ data: RemediationInsights }>("/v1/insights/remediation").then(
      (b) => b.data,
    ),
  insightsCapture: () =>
    post<{ data: PostureMetricPoint }>("/v1/insights/capture", {}).then(
      (b) => b.data,
    ),
  insightsFrameworkTrends: (limit = 90) =>
    get<{ data: FrameworkReadinessTrends }>(
      `/v1/insights/framework-trends?limit=${limit}`,
    ).then((b) => b.data),
  insightsSlaHeatmap: () =>
    get<{ data: SlaHeatmap }>("/v1/insights/sla-heatmap").then((b) => b.data),
  agentRuns: (query = "") =>
    get<{ data: AgentRun[] }>(`/v1/agent-runs${query}`).then((b) => b.data),
  agentRun: (runId: string) =>
    get<{ data: AgentRun }>(`/v1/agent-runs/${encodeURIComponent(runId)}`).then(
      (b) => b.data,
    ),
  createAgentRun: (payload: CreateAgentRunPayload) =>
    post<{ data: AgentRun }>("/v1/agent-runs", payload).then((b) => b.data),
  approveAgentDecision: (runId: string, decisionIndex: number, note = "") =>
    post<{ data: AgentRun }>(
      `/v1/agent-runs/${encodeURIComponent(runId)}/decisions/${decisionIndex}/approve`,
      { note },
    ).then((b) => b.data),
  accessReviews: (query = "") =>
    get<{ data: AccessReviewCampaign[] }>(`/v1/access-reviews${query}`).then(
      (b) => b.data,
    ),
  createAccessReview: (
    payload: { name: string } & Partial<AccessReviewCampaign>,
  ) =>
    post<{ data: AccessReviewCampaign }>("/v1/access-reviews", payload).then(
      (b) => b.data,
    ),
  accessReview: (id: string) =>
    get<{ data: AccessReviewCampaign }>(
      `/v1/access-reviews/${encodeURIComponent(id)}`,
    ).then((b) => b.data),
  setAccessReviewStatus: (id: string, status: AccessReviewStatus) =>
    mutate<{ data: AccessReviewCampaign }>(
      `/v1/access-reviews/${encodeURIComponent(id)}`,
      "PATCH",
      { status },
    ).then((b) => b.data),
  accessReviewItems: (id: string, query = "") =>
    get<{ data: AccessReviewItem[] }>(
      `/v1/access-reviews/${encodeURIComponent(id)}/items${query}`,
    ).then((b) => b.data),
  seedAccessReview: (id: string) =>
    post<{ data: AccessReviewSeedResult }>(
      `/v1/access-reviews/${encodeURIComponent(id)}/seed`,
      {},
    ).then((b) => b.data),
  decideAccessReviewItem: (
    itemId: string,
    decision: AccessReviewDecision,
    note = "",
  ) =>
    post<{ data: AccessReviewItem }>(
      `/v1/access-reviews/items/${encodeURIComponent(itemId)}/decision`,
      { decision, note },
    ).then((b) => b.data),
  accessReviewCoverage: () =>
    get<{ data: AccessReviewCoverage[] }>("/v1/access-reviews/coverage").then(
      (b) => b.data,
    ),
  policyTemplates: () =>
    get<{ data: PolicyTemplateSummary[] }>("/v1/policy-templates").then(
      (b) => b.data,
    ),
  policyTemplate: (templateId: string) =>
    get<{ data: PolicyTemplate }>(
      `/v1/policy-templates/${encodeURIComponent(templateId)}`,
    ).then((b) => b.data),
  policies: (query = "") =>
    get<{ data: PolicyDocument[] }>(`/v1/policies${query}`).then((b) => b.data),
  adoptPolicy: (payload: {
    template_id: string;
    variables?: Record<string, string>;
    owner?: string;
  }) =>
    post<{ data: PolicyDocument }>("/v1/policies", payload).then((b) => b.data),
  policy: (id: string) =>
    get<{ data: PolicyDocument }>(
      `/v1/policies/${encodeURIComponent(id)}`,
    ).then((b) => b.data),
  updatePolicy: (
    id: string,
    payload: Partial<{
      title: string;
      content: string;
      owner: string;
      variables: Record<string, string>;
      status: string;
    }>,
  ) =>
    mutate<{ data: PolicyDocument }>(
      `/v1/policies/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ).then((b) => b.data),
  publishPolicy: (id: string) =>
    post<{ data: PolicyDocument }>(
      `/v1/policies/${encodeURIComponent(id)}/publish`,
      {},
    ).then((b) => b.data),
  policyAcknowledgments: (id: string) =>
    get<{ data: PolicyAcknowledgment[] }>(
      `/v1/policies/${encodeURIComponent(id)}/acknowledgments`,
    ).then((b) => b.data),
  recordPolicyAcknowledgment: (
    id: string,
    payload: { user_email?: string; display_name?: string } = {},
  ) =>
    post<{ data: PolicyAcknowledgment }>(
      `/v1/policies/${encodeURIComponent(id)}/acknowledgments`,
      payload,
    ).then((b) => b.data),
  policyAttestationSummary: () =>
    get<{ data: PolicyAttestationSummary }>(
      "/v1/policies/attestation-summary",
    ).then((b) => b.data),
  policyCoverage: () =>
    get<{ data: PolicyCoverage[] }>("/v1/policies/coverage").then(
      (b) => b.data,
    ),
  vendorQuestionnaires: () =>
    get<{ data: VendorQuestionnaireTemplateSummary[] }>(
      "/v1/vendor-questionnaires",
    ).then((b) => b.data),
  vendorQuestionnaire: (templateId: string) =>
    get<{ data: VendorQuestionnaireTemplate }>(
      `/v1/vendor-questionnaires/${encodeURIComponent(templateId)}`,
    ).then((b) => b.data),
  vendorAssessments: (query = "") =>
    get<{ data: VendorAssessment[] }>(`/v1/vendor-assessments${query}`).then(
      (b) => b.data,
    ),
  createVendorAssessment: (payload: {
    vendor_name: string;
    template_id: string;
    owner?: string;
    control_id?: string | null;
    due_at?: string | null;
  }) =>
    post<{ data: VendorAssessment }>("/v1/vendor-assessments", payload).then(
      (b) => b.data,
    ),
  vendorAssessment: (id: string) =>
    get<{ data: VendorAssessment }>(
      `/v1/vendor-assessments/${encodeURIComponent(id)}`,
    ).then((b) => b.data),
  updateVendorAssessment: (
    id: string,
    payload: Partial<{
      vendor_name: string;
      owner: string;
      control_id: string | null;
      due_at: string | null;
      responses: Record<string, { answer: string }>;
      status: VendorAssessmentStatus;
    }>,
  ) =>
    mutate<{ data: VendorAssessment }>(
      `/v1/vendor-assessments/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ).then((b) => b.data),
  submitVendorAssessment: (id: string) =>
    post<{ data: VendorAssessment }>(
      `/v1/vendor-assessments/${encodeURIComponent(id)}/submit`,
      {},
    ).then((b) => b.data),
  controlRemediation: (controlId: string) =>
    get<{ data: ControlRemediation }>(
      `/v1/controls/${encodeURIComponent(controlId)}/remediation`,
    ).then((b) => b.data),
  sprsScore: () =>
    get<{ data: SprsReport }>("/v1/gov-compliance/sprs").then((b) => b.data),
  poamItems: (params?: { framework_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.framework_id) qs.set("framework_id", params.framework_id);
    if (params?.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs}` : "";
    return get<{ data: PoamItem[] }>(`/v1/gov-compliance/poam${suffix}`).then(
      (b) => b.data,
    );
  },
  syncPoam: () =>
    post<{ data: PoamSyncResult }>("/v1/gov-compliance/poam/sync", {}).then(
      (b) => b.data,
    ),
  updatePoamItem: (id: string, payload: Record<string, unknown>) =>
    mutate<{ data: PoamItem }>(
      `/v1/gov-compliance/poam/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ).then((b) => b.data),
  platformPricing: () =>
    get<{ data: PlatformPricing }>("/v1/platform/pricing").then((b) => b.data),
  platformUsage: () =>
    get<{ data: PlatformUsage }>("/v1/platform/usage").then((b) => b.data),
};

export function bootstrapAssessment(): Assessment | null {
  if (typeof document === "undefined") return null;
  const tag = document.getElementById("app-data");
  if (!tag?.textContent) return null;
  try {
    const data = JSON.parse(tag.textContent);
    if (data && typeof data === "object" && "posture" in data) {
      return data as Assessment;
    }
  } catch {
    return null;
  }
  return null;
}
