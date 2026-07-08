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

Connectors **discover → probe → enable → sync** on schedule; lake eval runs on a
separate `eval_schedule`. Raw evidence upserts by `event_id`; gold posture
materializes without console interaction. See [CONTINUOUS_INGESTION.md](CONTINUOUS_INGESTION.md).

### Posture gates in CI

Use API keys and correlation IDs to fail builds or deployments when control tests
fail or violations exceed thresholds. See [api/AGENT_API.md](api/AGENT_API.md).

### Agent remediation (approval-gated)

SOC agents propose triage and remediation via MCP; human or policy approval applies
changes. Audit rows carry stable `event_id` and UTC `occurred_at`.

### Audit export

`GET /api/v1/audit-log` returns a unified activity envelope for SIEM export,
compliance archives, and auditor packages — no UI scrape required.

MCP tools wrap the same surface:

| Cluster        | Tools                                                                                                                                                                                                                                                                                                            |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ingestion loop | `get_ingestion_status`, `list_eval_runs`, `run_lake_eval`, `run_scheduler_tick`, `sync_connector`, `list_connector_runs`                                                                                                                                                                                         |
| Posture / lake | `get_posture`, `posture_as_of`, `list_controls`, `list_evidence`, `list_violations`, `get_framework_detail`, `get_snapshots_integrity`, `get_snapshot_detail`, `get_tracking_integrity`, `describe_api`                                                                                                          |
| Audit / export | `list_audit_log`, `create_snapshot`, `list_snapshots`, `create_trust_share`, `list_trust_shares`, `get_audit_readiness`, `get_evidence_freshness_summary`, `capture_insights_point`                                                                                                                              |
| GRC programs   | `adopt_policy`, `publish_policy`, `acknowledge_policy`, `create_risk`, `list_risks`, `create_vendor_assessment`, `submit_vendor_assessment`, `create_access_review`, `seed_access_review`, `record_access_review_decision`, `get_policy_template`, `get_policy`, `get_access_review`, `get_vendor_assessment`, … |
| Agent harness  | `list_agent_runs`, `create_agent_run`, `approve_agent_decision`                                                                                                                                                                                                                                                  |

Use `describe_api` to enumerate the full `/api/v1` catalog.

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
