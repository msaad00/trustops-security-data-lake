# Product Walkthrough

| First command                                                              | Artifact                                                                                        | App URL                                                                                                        |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `security-lakehouse fixtures load --company fintech --out build/lakehouse` | `build/lakehouse/gold/current_posture.json` plus bronze, silver, gold, snapshot, and mart files | `http://127.0.0.1:8787/console/dashboard/` after `security-lakehouse serve --lake build/lakehouse --port 8787` |

TrustOps is an open-source trust operations workbench for security evidence
lakes. It turns local or lake-backed evidence into posture files, control tests,
owner queues, graph views, snapshots, workflow actions, trust-center shares, and
agent-readable API responses. You can run it locally, self-host in your cloud, or
use managed hosted — see [Deployment](DEPLOYMENT.md).

This walkthrough is intentionally honest about what is shipped versus planned.
TrustOps is not presented as a hosted enterprise GRC replacement. The shipped
product proves the evidence model, self-hosted workbench, auth/RBAC spine,
catalog contracts, source-linked framework coverage, connector runners, public
repo audit, and API surfaces that a buyer or contributor can run today.

## First Run

| Step                                                        | Command                                                                                         | Artifact                                                       | Next step                                       |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------- |
| Install locally                                             | `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,server]"`           | editable `security-lakehouse` CLI                              | load a fixture                                  |
| Build the lake                                              | `security-lakehouse fixtures load --company fintech --out build/lakehouse`                      | `build/lakehouse/bronze`, `silver`, `gold`, and `mart` outputs | inspect posture                                 |
| Check posture                                               | `security-lakehouse assessment status --lake build/lakehouse`                                   | current scores, confidence inputs, and violations              | freeze or serve evidence                        |
| Freeze evidence                                             | `security-lakehouse assessment snapshot --lake build/lakehouse --reason vendor_due_diligence`   | `build/lakehouse/gold/snapshots/assessment-*.json`             | share the immutable snapshot path               |
| Open the workbench (run `make web-install web-build` first) | `security-lakehouse serve --lake build/lakehouse --server --allow-insecure-no-auth --port 8787` | server-mode console and API                                    | open `http://127.0.0.1:8787/console/dashboard/` |

The demo fixture is synthetic and intentionally includes failing controls so the
queues, evidence, and remediation surfaces are visible. The lake output is the
proof point. The UI and APIs read from those generated files instead of asking
users to trust marketing copy.

## Shipped Product Surface

| Surface                        | Shipped today                                                                                                                                                                                                                                                       | Evidence                                                                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Next workbench                 | Static Next.js workbench served by the Python package when the web build is available; routes cover dashboard, controls, evidence, violations, remediation, risk register, connectors, frameworks, workflows, graph, insights, agents, trust center, and audit log. | `app/web/src/app/*/page.tsx`, `src/security_lakehouse/server.py`                                                                                  |
| `/api/v1` envelopes            | Versioned routes return `{data, meta, errors}` envelopes with pagination, sorting, and filters on list resources.                                                                                                                                                   | `docs/api/AGENT_API.md`, `tests/test_api_v1.py`                                                                                                   |
| Local lake outputs             | Pipeline emits bronze raw evidence, silver normalized events, gold posture/control/asset files, snapshots, a SQLite mart, and an optional DuckDB mart.                                                                                                              | `src/security_lakehouse/pipeline.py`, `README.md#evidence-pipeline`                                                                               |
| Evidence lake sinks            | Optional sink adapters project the local medallion into customer-owned Snowflake, ClickHouse, and DuckDB targets without making those sinks the assessment source of truth.                                                                                         | `src/security_lakehouse/sinks/`, `tests/test_snowflake_sink.py`, `tests/test_clickhouse_sink.py`, `tests/test_duckdb_sink.py`                     |
| Public repo audit              | CLI audits public GitHub repositories without credentials and emits normalized raw evidence, including metadata, workflows, manifests, IaC, AI artifacts, and a code graph signal.                                                                                  | `src/security_lakehouse/repo_audit.py`, `docs/REPO_AUDIT.md`, `tests/test_repo_audit.py`                                                          |
| Connector catalog + runners    | Static connector access-boundary catalog plus CLI validation/listing/configure, UI/API state, probe/run history, and executable GitHub, AWS, Okta, Google Workspace, GCP, Azure, and Jira runners that write raw evidence and can materialize the lake.             | `connectors/catalog.json`, `src/security_lakehouse/connectors.py`, `src/security_lakehouse/connector_runner.py`, `tests/test_connector_runner.py` |
| Framework catalog and coverage | Source-linked framework registry, readiness gates, reviewed mappings, crosswalks, and a coverage matrix. Official marks are not shipped without documented permission.                                                                                              | `frameworks/registry.json`, `mappings/control_map.json`, `docs/FRAMEWORK_COVERAGE.md`, `tests/test_mappings.py`                                   |
| Workflow canvas                | Typed workflow graph model with trigger, condition, assignment, snapshot, webhook, Slack, Jira, and trust-share actions; dry-run preview; expression edge routing; UI canvas and API endpoints persist and run workflow versions.                                   | `src/security_lakehouse/workflows.py`, `app/web/src/app/automation/page.tsx`, `tests/test_workflows.py`                                           |
| Compliance graph canvas        | Framework -> control -> evidence type -> asset graph endpoint and visual canvas with filters, path tracing, and exports.                                                                                                                                            | `src/security_lakehouse/graph.py`, `app/web/src/app/graph/page.tsx`, `tests/test_graph_fixtures.py`                                               |
| Snapshots                      | CLI and API freeze point-in-time assessment JSON with reason, assessment hash, posture, frameworks, and violations.                                                                                                                                                 | `src/security_lakehouse/assessment.py`, `tests/test_pipeline.py`, `tests/test_api_v1.py`                                                          |
| Evidence room                  | Evidence view traces normalized events to controls, sources, hashes, and collection time.                                                                                                                                                                           | `app/web/src/app/evidence/page.tsx`, `src/security_lakehouse/server.py`                                                                           |

## Planned Or Incomplete

| Area                              | Planned, not claimed as complete                                                                            | Current honest boundary                                                                                                                                                                                                                                                       |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hosted multi-tenant control plane | Managed accounts, billing, and hosted operations.                                                           | The repo ships local/self-hosted patterns, server-mode auth/RBAC, tenant-scoped lake resolution, and API contracts; it is not a hosted SaaS.                                                                                                                                  |
| Enterprise connector ingestion    | Direct production ingestion for every source system in the catalog.                                         | Seven direct runners are executable with fixtures or scoped credentials: GitHub, AWS, Okta, Google Workspace, GCP, Azure, and Jira. Snowflake, ClickHouse, object storage, SIEM, and runtime-gateway entries remain read-only lake contracts unless a direct runner is added. |
| Full framework coverage           | Exhaustive official-control evaluation for every listed framework.                                          | The repo ships a seeded, source-linked framework/control catalog with reviewed mappings and applicability links. Neutral framework labels show source-linked scope and readiness-gate status; they do not indicate certification.                                             |
| Auditor collaboration room        | External reviewer accounts, comments, requests, approvals, and export workflows.                            | Snapshots and trust-share lifecycle primitives exist; full collaboration workflow is future work.                                                                                                                                                                             |
| Policy enforcement                | Preventive controls across identity, cloud, CI, and runtime systems.                                        | TrustOps currently assesses evidence and drives workflow actions; it does not claim broad enforcement.                                                                                                                                                                        |
| Managed warehouse operations      | Turn-key warehouse administration, retention policy management, cost governance, and hosted run operations. | Snowflake, ClickHouse, and DuckDB sink adapters exist and are tested as optional customer-owned projections. Customers still own warehouse provisioning, grants, secret mounts, retention policy, and scheduler/runtime operation.                                            |

## Walkthrough Paths

### 1. Local Evidence To Workbench

Run:

```bash
security-lakehouse pipeline run \
  --raw data/raw/security_events.jsonl \
  --out build/lakehouse
security-lakehouse serve --lake build/lakehouse --server --allow-insecure-no-auth --port 8787
```

Artifact:

- `build/lakehouse/gold/current_posture.json`
- `build/lakehouse/gold/control_tests.jsonl`
- `build/lakehouse/gold/asset_risk.jsonl`
- `build/lakehouse/mart/security_lakehouse.sqlite`

Next step: open `http://127.0.0.1:8787/console/dashboard/` and use the workbench to inspect
posture, controls, evidence, violations, graph, and snapshots.

### 2. Agent Or API Review

Run:

```bash
curl -s http://127.0.0.1:8787/api/v1/posture/current | jq .
curl -s 'http://127.0.0.1:8787/api/v1/control-tests?result=fail&limit=10' | jq .
curl -s -X POST http://127.0.0.1:8787/api/v1/snapshots \
  -H 'content-type: application/json' \
  --data '{"reason":"vendor_due_diligence"}' | jq .
```

Artifact: JSON envelopes with `data`, `meta`, and `errors`.

Next step: route failed controls to the owner queue or freeze a snapshot for a
review packet.

### 3. Public Repository Audit

Run:

```bash
security-lakehouse repo audit OWNER/REPO --out build/repo-audit.jsonl
```

Artifact: normalized raw evidence for a public repository, including repository
metadata, workflow files, manifests, policy files, infrastructure hints, AI
artifacts, and a code graph summary.

Next step: feed `build/repo-audit.jsonl` into the pipeline or inspect it as
source evidence for supply-chain posture.

### 4. Connector And Framework Catalog Review

Run:

```bash
security-lakehouse connectors validate
security-lakehouse connectors list
security-lakehouse connectors configure --lake build/lakehouse --connector-id github-security --state enabled
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id github-security \
  --repo acme/model-service \
  --fixture-dir tests/fixtures/github-governance
security-lakehouse frameworks readiness
```

Artifact: connector access-boundary JSON, connector raw evidence, materialized
lake outputs, run history, and framework readiness rows.

Next step: choose the smallest viable integration boundary: read-only existing
lake role, scoped source API token, or managed evidence object.

## Screenshots And Visual Assets

Fresh demo screenshots are captured from the server-mode workbench using the
synthetic `fintech` fixture.

| Asset                             | Path                                           |
| --------------------------------- | ---------------------------------------------- |
| Trust Home / dashboard            | `docs/images/trustops-demo-dashboard.png`      |
| Workflow canvas                   | `docs/images/trustops-demo-workflows.png`      |
| Graph workbench                   | `docs/images/trustops-demo-graph.png`          |
| Framework coverage and provenance | `docs/images/trustops-demo-frameworks.png`     |
| Control drawer                    | `docs/images/trustops-demo-control-drawer.png` |
| Evidence room                     | `docs/images/trustops-demo-evidence.png`       |
| Connector workbench               | `docs/images/trustops-demo-connectors.png`     |
| Trust center reviewer shares      | `docs/images/trustops-demo-trust-center.png`   |

## Buyer-Readable Boundary

TrustOps is useful today for proving an evidence model:

- first command -> local lake artifact -> workbench/API
- evidence -> controls -> violations -> owner workflow
- framework registry -> source-linked mapping -> readiness gate
- public repo audit -> normalized evidence -> graph signal
- snapshot -> immutable review artifact -> next action

The current product is strongest as a self-hosted OSS proof-of-value and
developer-facing evidence workbench. Broader enterprise workflows should be
positioned as roadmap unless code, tests, deployment artifacts, and live smoke
evidence prove them in this repository.
