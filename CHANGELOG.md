# Changelog

All notable TrustOps changes are summarized here. Versions follow semver for the
Python package, Helm chart, and bundled web console.

## 0.2.0 - 2026-06-29

Release theme: **invite-only hosted POC readiness**. This release turns the repo
from a local/security-lake proof into a more coherent self-hosted TrustOps
platform: deployable by URL, usable by humans, and callable by headless agents.

### Product

- Added a first-run launch surface at `/console/poc/` that checks public URL,
  human auth, headless access, source sync, trust shares, and agent review state.
- Streamlined connector onboarding so Snowflake setup starts with identity,
  discovers granted scope, then lets the operator select read objects before
  testing/enabling.
- Added connector sync proof in the drawer so operators can see latest sync
  result, evidence count, fingerprint, and timing without opening raw logs.
- Added a governed agent harness launcher in the console with sequential vs.
  LangGraph orchestration, model toggle, budget profiles, persisted runs,
  decision review, and approval-gated writes.
- Added agent review readiness to the launch flow so the hosted POC path can go:
  connect source -> sync -> assess -> run governed review -> share trust.

### Evidence, Connectors, And Ingestion

- Proved live AWS, Azure, and Snowflake ingestion paths through the same
  scenario contract used by fixtures and CI.
- Added Snowflake read-scope discovery for warehouses, databases, schemas, and
  granted views.
- Hardened continuous ingestion docs around incremental reads, idempotency,
  retry safety, scheduler operation, and customer-owned lake boundaries.
- Added pluggable sink and lake-adapter guidance for Snowflake, ClickHouse,
  DuckDB, local files, and existing evidence-lake reads.

### Agent And Workflow Runtime

- Added persisted `agent_runs` with input hashes, budget metadata, evaluation
  results, proposed decisions, approval state, and API/MCP access.
- Added optional LangGraph orchestration while keeping the deterministic
  assessment engine model-independent and usable with zero LLM configured.
- Added model budget controls for context size, fact count, and output tokens.
- Kept writes behind RBAC, allow-listed action types, idempotency, and approval.

### Security And Operations

- Hardened API error handling and CodeQL findings around path use and exception
  exposure.
- Added API pagination/rate-limit robustness and safer connector error surfaces.
- Added hosted POC, AWS + Snowflake, live cloud, and continuous ingestion
  runbooks.
- Added OIDC/SAML/API-key server-mode docs, tenant lake boundaries, redaction,
  hashes, append-only audit records, and trust-share guidance.

### Known Gaps Before Public SaaS

- No public self-serve signup, billing, SCIM lifecycle, or multi-customer
  account marketplace.
- Connector auth is POC-capable but still needs more OAuth/service-role wizards,
  secret-manager integrations, and provider-specific hosted UX polish.
- Framework packs are seeded and source-linked, but not full certification-grade
  coverage for every framework.
- Workflow automation has a usable DAG/canvas, templates, and runs, but still
  needs deeper run inspection, retries, approvals, and action logs.
- Production operations need backup/restore drills, external secret sync,
  multi-replica guidance, alerting, WAF/API gateway guidance, and hosted
  observability before a broad public launch.
