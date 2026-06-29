# Release Readiness

This is the release audit for TrustOps `0.2.0`. It is intentionally factual:
what is implemented, what is safe to demo, and what still blocks a public
commercial SaaS launch.

## Current Product Bar

| Target                 | Status       | Reason                                                                                                                                           |
| ---------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Local OSS demo         | Ready        | Fixtures, pipeline, web console, API, workflows, agent harness, and tests run locally.                                                           |
| Invite-only hosted POC | Mostly ready | Helm, server auth, scheduler, Snowflake/AWS/Azure live paths, trust shares, and first-run readiness exist. Operator bootstrap is still required. |
| Self-hosted team pilot | Close        | Needs customer-specific OIDC, secret manager, backup, scheduler, lake storage, and connector grants.                                             |
| Public self-serve SaaS | Not ready    | Needs signup, tenant lifecycle, SCIM, billing/limits, abuse controls, managed operations, and stronger hosted connector UX.                      |

## What Is Release-Ready

### Deterministic Trust Core

- Raw evidence can be validated, normalized, transformed, and assessed.
- Control verdicts are deterministic and not model-generated.
- Bronze/silver/gold artifacts carry stable IDs, hashes, freshness, posture,
  violations, asset risk, framework readiness, and snapshots.
- Snapshot ledgers are append-only and chainable.
- Evidence and posture can be served through UI, API, CLI, SDK, MCP, and
  workflows.

### Human Console

- Dashboard, connectors, controls, evidence, findings, remediation, workflows,
  trust center, access reviews, risks, graph, crosswalk, insights, audit log,
  launch readiness, and agent runs are available in the web console.
- `/console/poc/` gives a guided launch state: URL, auth, API access, source
  sync, trust share, and agent review.
- Connector drawers show probe/sync status and latest sync proof.
- Snowflake connector setup supports discovery before enablement.

### Headless And Agent Surfaces

- `/api/v1` has a stable envelope for machine clients.
- OpenAPI, SDK, CLI, and MCP expose the same TrustOps read/write boundary.
- Agent harness runs are persisted with input hashes, budgets, model/provider
  config, evaluation, proposed decisions, and approval state.
- LangGraph is optional. The built-in sequential runner works without an LLM.
- Approved agent writes are routed through TrustOps-native actions and audit
  records, not arbitrary model output.

### Connectors And Ingestion

- Live connector paths have been proven for AWS posture, Azure posture, and
  Snowflake existing-lake reads.
- Additional implemented runners cover GitHub governance, Okta, Google
  Workspace, GCP posture, and Jira ticketing.
- The scheduler can fire connector syncs and workflows through the same runner
  contracts used by UI/API/CLI.
- Continuous ingestion docs define incremental reads, retries, backoff,
  watermarks, materialization, and idempotency.

### Deployment

- Docker image serves API and bundled web console from one process.
- Helm chart includes app deployment, service, ingress, PVC, service account,
  and scheduler CronJob.
- AWS + Snowflake POC values and runbooks exist.
- Snowflake bootstrap scripts create a reader role, read warehouse, evidence
  schema, and secure views for a first proof.
- AWS/Azure/GCP bootstrap templates create read-only posture roles or identities.

## 15-Minute Hosted POC Gate

A hosted POC link is ready to share when all gates below pass.

| Gate         | Command or UI check                       | Expected result                                            |
| ------------ | ----------------------------------------- | ---------------------------------------------------------- |
| HTTPS health | `curl -fsS https://HOST/api/healthz`      | `ok` response over TLS                                     |
| Auth         | Open `/console/poc/` in a private browser | Redirects to OIDC/SAML, then lands in console              |
| Tenant state | `/console/poc/`                           | No blocking setup item before external share               |
| Source sync  | Connector drawer                          | One `ok` probe and one `ok` sync with evidence count       |
| Posture      | Dashboard                                 | Non-empty framework portfolio and current score            |
| Integrity    | Evidence drawer                           | Hash verification succeeds for sampled evidence            |
| Workflow     | Workflow run or scheduler tick            | Run is persisted and visible                               |
| Agent review | `/console/agents/`                        | Completed run with budget, input hash, eval, and decisions |
| Trust share  | `/console/trust-center/`                  | Create, open, expire, and revoke a scoped share            |
| Secrets      | Logs/UI/config                            | No raw passwords, PATs, OAuth tokens, or private keys      |

## Release Verification

Run these before tagging a release:

```bash
uv run pre-commit run --all-files
uv run pytest
npm run typecheck --prefix app/web
npm run build --prefix app/web
docker build -t trustops:0.2.0 .
helm lint deploy/helm/trustops
helm template trustops deploy/helm/trustops >/tmp/trustops-rendered.yaml
```

Optional live proof, with customer-owned credentials or cloud shell sessions:

```bash
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/aws-live \
  --connector aws-posture \
  --summary

security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/azure-live \
  --connector azure-posture \
  --summary

security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/snowflake-live-service \
  --connector snowflake-evidence-lake \
  --summary
```

## Public SaaS Delta

The codebase is not yet a public multi-tenant SaaS. These are the remaining
commercial-hosting gaps:

- self-serve org creation, invites, SCIM, and deprovisioning;
- billing, quotas, usage metering, and abuse controls;
- managed secrets, connector consent flows, and secret rotation;
- multi-tenant Postgres, object storage, backup, restore, and retention policy;
- horizontal API/scheduler scaling and queue-backed connector workers;
- WAF/API gateway, tenant-level rate limits, and admin activity alerts;
- hosted support workflows, audit exports, customer admin docs, and incident
  response process;
- deeper framework packs and auditor-reviewed evidence requirements.

## Go / No-Go

| Release decision                                                 | Current answer                 |
| ---------------------------------------------------------------- | ------------------------------ |
| Ship OSS `0.2.0` release                                         | Go                             |
| Share invite-only hosted POC with known evaluators               | Go after deployment gates pass |
| Allow arbitrary public signup                                    | No-go                          |
| Market as certification replacement                              | No-go                          |
| Market as self-hosted TrustOps / compliance data lake foundation | Go                             |
