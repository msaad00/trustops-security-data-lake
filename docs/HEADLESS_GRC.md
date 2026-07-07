# Headless GRC Architecture

TrustOps is **headless-first**: compliance posture, evidence, controls, and audit
artifacts are produced and consumed through **APIs, CLI, MCP, and CI** — the same
deterministic lake and `/api/v1` contract everywhere. The web console is a **peer
surface** for human reviewers, auditors, and operators — not the source of truth.

This mirrors how modern security platforms moved to agent-driven, API-native
operations: automation runs continuously; humans inspect, approve, and sign off.

## Surfaces (one core)

| Surface          | Primary caller               | Role                                       |
| ---------------- | ---------------------------- | ------------------------------------------ |
| **REST API**     | CI, scripts, integrations    | Read posture, write gated mutations        |
| **CLI**          | Operators, runbooks          | Lake rebuild, connector sync, snapshots    |
| **MCP / agents** | SOC, GRC, remediation agents | Tool calls with same RBAC as API keys      |
| **Scheduler**    | CronJob / K8s                | Connector sync, workflow ticks             |
| **Console**      | GRC leads, auditors          | Visual drill-down, approvals, trust shares |

All surfaces read the **same JSON** from the customer lake. Agents must not bypass
approval gates for remediation, trust shares, or workflow side effects.

## Headless workflows

### Continuous ingestion

Connectors probe → sync → upsert raw evidence. The pipeline materializes gold
posture without console interaction. See [CONTINUOUS_INGESTION.md](CONTINUOUS_INGESTION.md).

### Posture gates in CI

Use API keys and correlation IDs to fail builds or deployments when control tests
fail or violations exceed thresholds. See [api/AGENT_API.md](api/AGENT_API.md).

### Agent remediation (approval-gated)

SOC agents propose triage and remediation via MCP; human or policy approval applies
changes. Audit rows carry stable `event_id` and UTC `occurred_at`.

### Audit export

`GET /api/v1/audit-log` returns a unified activity envelope for SIEM export,
compliance archives, and auditor packages — no UI scrape required.

MCP tools wrap the same surface: lake-backed reads (`get_posture`, `get_framework_detail`,
`list_audit_log`, …) and authenticated server APIs (`get_audit_readiness`,
`get_evidence_freshness_summary`, `get_insights_remediation`, `list_vendor_assessments`,
`list_vendor_questionnaires`, `get_poc_readiness`, `list_policies`, `list_policy_templates`,
`get_policies_coverage`, `list_connector_runs`, `list_access_reviews`,
`get_access_reviews_coverage`, `list_evidence_requests`, `list_risks`,
`list_remediation_exceptions`, `list_trust_shares`, agent harness operations). Use
`describe_api` to enumerate paths.

### Point-in-time snapshots

Assessment snapshots with hash chain support auditor sign-off and drift detection
via API or CLI.

## Human console (when you need it)

The console exists for:

- Executive and audit-room dashboards
- Framework drill-down (control → rule → evidence → datasource)
- Access review campaigns and evidence requests
- Trust-center shares for external auditors
- Workflow canvas inspection and approvals

Console actions hit the **same API** as headless callers and appear in request audit.

## Idempotency and traceability

| Concern          | Mechanism                                |
| ---------------- | ---------------------------------------- |
| Duplicate writes | `Idempotency-Key` on mutating APIs       |
| Evidence dedupe  | `event_id` on raw connector events       |
| Request tracing  | `X-Correlation-ID` (one attempt per row) |
| Audit integrity  | Chained triage log + UUID request audit  |

See [INGESTION_CONNECTORS_IDEMPOTENCY.md](INGESTION_CONNECTORS_IDEMPOTENCY.md).

## Related

- [AUDIT_READINESS.md](AUDIT_READINESS.md) — audit-room score and workflow checklist
- [AUDIT_SCALE.md](AUDIT_SCALE.md) — large-finding workloads
- [CONNECTORS.md](CONNECTORS.md) — connector catalog and registry model
