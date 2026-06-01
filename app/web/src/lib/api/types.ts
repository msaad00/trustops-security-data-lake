// Wire types mirror security_lakehouse/assessment.py and gold/*.jsonl.

export interface FrameworkPosture {
  framework: string;
  score: number;
  state: "ready" | "attention_required";
  control_count: number;
  failing_control_count: number;
  violation_count: number;
  stale_control_count: number;
  critical_violation_count: number;
  high_violation_count: number;
}

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Violation {
  violation_id: string;
  control_id: string;
  event_id: string;
  asset_id: string;
  asset_owner: string;
  environment: string;
  source: string;
  event_type: string;
  severity: Severity;
  severity_score: number;
  state: string;
  evidence_ref: string;
  raw_sha256: string;
  detected_at: string;
}

export interface PostureBlock {
  score: number;
  state: "ready" | "attention_required" | "critical";
  framework_count: number;
  control_count: number;
  asset_count: number;
  open_violation_count: number;
  critical_violation_count: number;
  high_violation_count: number;
  stale_control_count: number;
}

export interface AssetRisk {
  asset_id: string;
  asset_owner: string;
  asset_type: string;
  environment: string;
  risk_score: number;
  critical_open: number;
  high_open: number;
}

export interface Assessment {
  schema_version: string;
  assessment_type: string;
  evaluated_at: string;
  freshness_days: number;
  posture: PostureBlock;
  frameworks: FrameworkPosture[];
  violations: Violation[];
  top_risk_assets: AssetRisk[];
  stale_controls: string[];
  assessment_hash: string;
}

export interface ControlPosture {
  control_id: string;
  framework: string;
  status: "pass" | "fail" | "warn" | string;
  title: string;
  owner: string;
  risk_score: number;
  evidence_count: number;
  event_count: number;
}

export interface ControlTest {
  control_id: string;
  name: string;
  result: "pass" | "fail" | "warn" | string;
  status: string;
  owner: string;
  confidence_score: number;
  agent_skill: string;
  freshness_status: string;
  next_action: string;
}

export interface NormalizedEvent {
  event_id: string;
  event_time: string;
  source: string;
  status: string;
  severity: Severity;
  asset_id: string;
  asset_owner: string;
  evidence_ref: string;
  evidence_id: string;
  control_ids: string[];
  evidence_collected_at: string;
}

export interface Health {
  ok: boolean;
  service: string;
}

export interface AuthMethod {
  id: "oidc" | "saml";
  label: string;
  configured: boolean;
  login_url: string;
}

export interface AuthMethods {
  require_auth: boolean;
  methods: AuthMethod[];
}

export interface SnapshotResponse {
  snapshot_path: string;
  reason: string;
}

export type TrackingState =
  | "open"
  | "triaged"
  | "in_progress"
  | "resolved"
  | "dismissed";

export interface TrackingEvent {
  tracking_id: string;
  violation_id: string;
  actor: string;
  state: TrackingState;
  assignee: string | null;
  due_at: string | null;
  note: string | null;
  occurred_at: string;
}

export interface TriagePayload {
  state: TrackingState;
  actor?: string;
  assignee?: string;
  due_at?: string;
  note?: string;
}

export interface VerifyResult {
  event_id: string;
  verified: boolean;
  expected_sha256: string | null;
  computed_sha256: string | null;
  source_layer: "bronze" | "missing";
  reason: string | null;
}

export type ConnectorState = "enabled" | "disabled";

export interface ConnectorRun {
  connector_id: string;
  kind: "probe" | "sync";
  result: "ok" | "error" | "skipped";
  actor: string;
  duration_ms: number | null;
  evidence_count: number | null;
  error: string | null;
  occurred_at: string;
}

export interface ConnectorView {
  connector_id: string;
  name: string;
  category: string;
  collection_mode: string;
  access_boundary: string;
  credential_type: string;
  minimum_permissions: string[];
  evidence_types: string[];
  default_route: string;
  freshness_slo_minutes: number;
  production_status: "hero_path" | "supported_path" | "starter_path" | string;
  state: ConnectorState;
  configured_at: string | null;
  credential_fingerprint: string | null;
  configured_options: Record<string, unknown>;
  last_probe: ConnectorRun | null;
  last_sync: ConnectorRun | null;
}

export interface ConfigurePayload {
  state: ConnectorState;
  actor?: string;
  credentials?: Record<string, string>;
  options?: Record<string, unknown>;
}

export type FrameworkFreshness = "fresh" | "stale" | "expired" | "never_pulled";

export interface FrameworkView {
  framework_id: string;
  name: string;
  version: string;
  effective_date: string | null;
  superseded_by: string | null;
  official_source_name: string;
  official_source_url: string;
  source_sha256: string | null;
  pulled_at: string | null;
  implementation_status: string;
  copyright_guardrail: string;
  sync_cadence_days: number;
  control_count: number;
  implemented_control_count: number;
  mapping_coverage_pct: number;
  freshness_state: FrameworkFreshness;
  pulled_age_days: number | null;
  next_pull_due: string | null;
}

export interface FrameworkControlArticle {
  article_id: string;
  title: string;
  official_source_url: string;
  reviewed_by: string;
  reviewed_at: string;
  rationale: string;
}

export interface FrameworkSourceRollup {
  source: string;
  event_count: number;
  fresh_count: number;
  stale_count: number;
  expired_count: number;
  latest_evidence_at: string | null;
}

export interface FrameworkControlDetail {
  control_id: string;
  title: string;
  owner: string;
  risk_domain: string;
  frequency: string;
  implementation_status: string;
  evidence_requirement: string;
  evaluation_rule: string;
  official_source_ref: string;
  articles: FrameworkControlArticle[];
  posture: {
    status: "pass" | "fail" | "not_evaluated";
    risk_score: number | null;
    evidence_coverage: number | null;
    open_event_count: number;
    rule_reasons: string[];
  };
  test: {
    result: "pass" | "fail" | "not_run";
    confidence_score: number | null;
    freshness_status: string | null;
    required_evidence_types: string[];
    observed_evidence_types: string[];
    next_action: string | null;
  };
  evidence: {
    count: number;
    latest_evidence_at: string | null;
    freshness: {
      fresh: number;
      stale: number;
      expired: number;
    };
    sources: FrameworkSourceRollup[];
  };
}

export interface FrameworkDetail {
  framework: FrameworkView;
  summary: {
    control_count: number;
    mapped_control_count: number;
    passing_control_count: number;
    failing_control_count: number;
    evidence_count: number;
    source_count: number;
  };
  controls: FrameworkControlDetail[];
  sources: FrameworkSourceRollup[];
}

// --- Workflows --------------------------------------------------------------

export type ActionKind = "trigger" | "check" | "action";

export interface ActionSchemaField {
  type: "string" | "number" | "boolean";
  label: string;
  required?: boolean;
  optional?: boolean;
  default?: string | number | boolean;
}

export interface ActionSpec {
  node_type: string;
  kind: ActionKind;
  label: string;
  description: string;
  input_schema: Record<string, ActionSchemaField>;
  output_schema: Record<string, string>;
}

export interface WorkflowNode {
  id: string;
  node_type: string;
  params: Record<string, unknown>;
  position?: { x: number; y: number };
}

export interface WorkflowEdge {
  source: string;
  target: string;
  /**
   * Edge condition. `always` (default) fires the target whenever the source
   * runs; `passed`/`failed` only fire when the source's output includes a
   * truthy/falsy `passed` field. Used by the backend's topological runner
   * to gate downstream actions on check results.
   */
  condition?: "always" | "passed" | "failed";
}

export interface Workflow {
  workflow_id: string;
  version: number;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  actor: string;
  occurred_at: string;
  hash: string;
}

export interface WorkflowRunNode {
  node_id: string;
  node_type: string;
  params: Record<string, unknown>;
  result: "ok" | "error";
  output?: Record<string, unknown>;
  error?: string;
}

export interface WorkflowRun {
  workflow_id: string;
  workflow_version: number;
  actor: string;
  result: "ok" | "error";
  started_at: string;
  finished_at: string;
  node_results: WorkflowRunNode[];
}

// --- Trust shares -----------------------------------------------------------

export interface TrustShare {
  share_id: string;
  role: "auditor";
  scope: "posture_full" | "posture_framework";
  framework_id: string | null;
  expires_at: string;
  created_at: string;
  created_by: string;
  revoked_at: string | null;
  token_sha256: string;
  token?: string; // returned only at create time
  expired: boolean;
}

// --- Audit log --------------------------------------------------------------

export interface AuditLogEntry {
  category: "triage" | "connector" | "snapshot" | "workflow" | "trust_share";
  actor: string;
  occurred_at: string;
  summary: string;
  subject: string;
  result: string | null;
  payload: Record<string, unknown>;
}

// --- Compliance graph -------------------------------------------------------

export type GraphNodeKind =
  | "framework"
  | "control"
  | "evidence_type"
  | "asset"
  | "repository"
  | "directory"
  | "language"
  | "evidence_signal"
  | "governance_signal"
  | "signal_gap"
  | "workflow"
  | "dependency_manifest"
  | "ownership_file"
  | "security_file"
  | "file"
  | "principal"
  | "team"
  | "review_rule"
  | "status_check"
  | "workflow_permission"
  | "evidence";

export type GraphEdgeKind =
  | "framework_has_control"
  | "control_requires_evidence"
  | "evidence_covers_asset";

export interface GraphNode {
  id: string;
  kind: GraphNodeKind;
  label: string;
  subtitle?: string;
  framework_id?: string;
  owner?: string;
  environment?: string;
  risk_score?: number;
  event_count?: number;
  path_count?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: GraphEdgeKind;
}

export interface ComplianceGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  counts: Record<GraphNodeKind, number>;
}

export interface CrosswalkCell {
  framework_id: string;
  shared_risk_domains: string[];
  shared_owners: string[];
  is_self: boolean;
}

export interface CrosswalkRow {
  framework_id: string;
  cells: CrosswalkCell[];
}

export interface Crosswalk {
  frameworks: string[];
  matrix: CrosswalkRow[];
}

export interface ReviewedArticle {
  article_id: string;
  title: string;
  official_source_url: string;
  reviewed_by: string;
  reviewed_at: string;
  rationale: string;
}

export interface ControlArticleMapping {
  control_id: string;
  framework_id: string;
  articles: ReviewedArticle[];
}

export interface ReviewedCrosswalkCell {
  framework_id: string;
  is_self: boolean;
  shared_articles: string[];
  shared_controls: string[];
}

export interface ReviewedCrosswalkRow {
  framework_id: string;
  mapping_count: number;
  article_count: number;
  cells: ReviewedCrosswalkCell[];
}

export interface ReviewedCrosswalk {
  frameworks: string[];
  matrix: ReviewedCrosswalkRow[];
}

export type ReadinessStage =
  | "source_pulled"
  | "mapped"
  | "evidence_defined"
  | "rule_versioned"
  | "coverage_verified";

export interface FrameworkReadiness {
  framework_id: string;
  name: string;
  version: string;
  control_count: number;
  mapped_control_count: number;
  coverage_pct: number;
  gates: Record<ReadinessStage, boolean>;
  stage: ReadinessStage;
  is_ready: boolean;
}

export interface RemediationTask {
  id: string;
  title: string;
  description: string;
  control_id: string | null;
  violation_id: string | null;
  owner: string;
  status: "open" | "in_progress" | "blocked" | "resolved" | "dismissed";
  priority: "low" | "medium" | "high" | "critical";
  due_at: string | null;
  overdue: boolean;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
  resolved_at: string | null;
}

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RiskStatus = "open" | "mitigating" | "accepted" | "closed";

export interface Risk {
  id: string;
  tenant_id?: string;
  title: string;
  description: string;
  category: string;
  severity: RiskLevel;
  likelihood: RiskLevel;
  impact: RiskLevel;
  status: RiskStatus;
  treatment: string;
  owner: string;
  control_id: string | null;
  asset_id: string | null;
  due_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EvidenceRequestItem {
  id: string;
  control_id: string;
  requested_from: string;
  status: "open" | "fulfilled" | "cancelled";
  note: string;
  due_at: string | null;
  created_by: string;
  created_at: string | null;
  fulfilled_at: string | null;
}

export interface ControlExceptionItem {
  id: string;
  control_id: string;
  reason: string;
  approved_by: string;
  status: "active" | "revoked" | "expired";
  active: boolean;
  expires_at: string | null;
  created_by: string;
  created_at: string | null;
  revoked_at: string | null;
}

// --- Tags + saved views -----------------------------------------------------

export interface Tag {
  id: string;
  tenant_id: string;
  name: string;
  color: string;
  created_at: string | null;
}

export interface EntityTag {
  id: string;
  tenant_id: string;
  tag_id: string;
  entity_type: string;
  entity_id: string;
  created_at: string | null;
}

export interface SavedView {
  id: string;
  tenant_id: string;
  surface: string;
  name: string;
  filters: Record<string, unknown>;
  created_by: string;
  created_at: string | null;
}

export interface PostureMetricPoint {
  id: string;
  tenant_id: string;
  captured_at: string;
  posture_score: number;
  control_pass_rate: number;
  open_violations: number;
  critical_violations: number;
  stale_controls: number;
  evidence_fresh_pct: number;
  remediation_open: number;
  remediation_overdue: number;
}

export interface RemediationInsights {
  open: number;
  overdue: number;
  mttr_hours: number | null;
  sla_attainment_pct: number | null;
  resolved_count: number;
  sla_eligible_count: number;
}

// --- Metrics & insights (populated by migration 0006_metrics) ---------------

export interface PostureMetricPoint {
  id: string;
  tenant_id: string;
  captured_at: string;
  posture_score: number;
  control_pass_rate: number;
  open_violations: number;
  critical_violations: number;
  stale_controls: number;
  evidence_fresh_pct: number;
  remediation_open: number;
  remediation_overdue: number;
}

export interface RemediationInsights {
  open: number;
  overdue: number;
  mttr_hours: number | null;
  sla_attainment_pct: number | null;
  resolved_count: number;
  sla_eligible_count: number;
}
