# TrustOps Security Data Lake

<p align="center">
  <img src="docs/images/trustops-logo.svg" alt="TrustOps — open-source trust operations" width="280">
</p>

**Open-source trust operations** — turn cloud, identity, code, runtime, and AI evidence into live posture, framework readiness, findings, workflows, snapshots, and shareable proof. Evidence stays in **your** lake, VPC, or laptop.

> **Naming:** **TrustOps** is the product. **TrustOps Console** is the web UI.
> The repo/package name `trustops-security-data-lake` and CLI `security-lakehouse`
> are operator surfaces — see [Brand guide](docs/BRAND.md).

<p align="center">
  <img src="docs/images/trustops-readme-banner.svg" alt="Collect evidence, evaluate controls, route risk, automate follow-up, share proof" width="100%">
</p>

<p align="center">
  <a href="docs/PRODUCT_WALKTHROUGH.md"><strong>Walkthrough</strong></a> ·
  <a href="docs/PRODUCT_SHAPE.md"><strong>Product shape</strong></a> ·
  <a href="docs/SHAREABLE_DEMO.md"><strong>Demo</strong></a> ·
  <a href="docs/ARCHITECTURE.md"><strong>Architecture</strong></a> ·
  <a href="docs/CONNECTORS.md"><strong>Connectors</strong></a> ·
  <a href="docs/DEPLOYMENT_AND_PRICING.md"><strong>Deploy</strong></a> ·
  <a href="docs/diagrams/README.md"><strong>Diagrams</strong></a> ·
  <a href="CHANGELOG.md"><strong>Changelog</strong></a>
</p>

## At a glance

|                |                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------- |
| **Release**    | `0.2.x` — OSS demos, self-hosted pilots, hosted scaffold ([readiness](docs/RELEASE_READINESS.md))  |
| **Catalog**    | 10 framework families · **635** controls · 18 asset types ([coverage](docs/FRAMEWORK_COVERAGE.md)) |
| **Console**    | **28 routes** — dashboard, audit room, controls, evidence, connectors, access, agents, deploy, …   |
| **Deployment** | Local $0 · self-hosted Helm · managed hosted ([pricing](docs/DEPLOYMENT_AND_PRICING.md))           |
| **Surfaces**   | Console · `/api/v1` · SDK · MCP · optional agents ([API](docs/api/AGENT_API.md))                   |

One loop: **connect → sync → evaluate → remediate → review → share → prove** — deterministic control verdicts, approval-gated writes, signed session cookies, and hash-chained snapshots.

## Shipped highlights

| Area               | What you get today                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------ |
| **Audit workflow** | Audit room, readiness API, trust shares, auditor redaction, access reviews, executive PDF        |
| **Evidence**       | Bronze/silver/gold lake, freshness SLA summary + escalate-to-tasks, evidence room                |
| **Frameworks**     | SOC 2, NIST AI RMF, FedRAMP foundation, CIS AWS, ISO 27001/42001 packs                           |
| **Identity**       | OIDC/SAML, API keys, user/role admin, API-key → browser session, IdP group → role, SCIM scaffold |
| **Automation**     | Workflow canvas, agent harness, MCP tools, GitHub Action posture gate                            |
| **Deploy**         | Helm + EKS terraform, `/console/deploy`, customer-owned evidence boundary                        |

Gap map vs mature managed GRC SaaS (UX polish, HRIS/devices, billing): [PRODUCT_SHAPE.md](docs/PRODUCT_SHAPE.md).

## Console

<p align="center">
  <img src="docs/images/trustops-product-mosaic.svg" alt="Trust command center, audit room, evidence, workflows, graph, trust center, connectors, access" width="100%">
</p>

|                                                         Trust command center                                                         |                                                        Audit room                                                         |
| :----------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------: |
| <img src="docs/images/trustops-demo-dashboard.png" alt="Dashboard — posture score, framework readiness, fix-next queue" width="420"> | <img src="docs/images/trustops-demo-audit-room.png" alt="Audit room — score, gaps, freshness SLA, checklist" width="420"> |

|                                                    Evidence room                                                     |                                              Access & identity                                               |
| :------------------------------------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------------------: |
| <img src="docs/images/trustops-demo-evidence.png" alt="Evidence — hashes, freshness, sources, controls" width="420"> | <img src="docs/images/trustops-demo-auth.png" alt="Access — API keys, users and roles, invites" width="420"> |

|                                                        Automation                                                        |                                                  Trust center                                                  |
| :----------------------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------: |
| <img src="docs/images/trustops-demo-workflows.png" alt="Workflow canvas — triggers, checks, approval gates" width="420"> | <img src="docs/images/trustops-demo-trust-center.png" alt="Trust center — scoped reviewer shares" width="420"> |

More screens: [connectors](docs/images/trustops-demo-connectors.png) · [frameworks](docs/images/trustops-demo-frameworks.png) · [graph](docs/images/trustops-demo-graph.png) · [controls](docs/images/trustops-demo-control-drawer.png) — see [Product Walkthrough](docs/PRODUCT_WALKTHROUGH.md).

## How it works

Connectors read evidence **read-only**. A bronze → silver → gold pipeline normalizes facts; controls-as-code produces posture, violations, freshness signals, and snapshots. The console, API, workflows, and agents sit on top — models may summarize or propose actions, but **never own the verdict**.

<p align="center">
  <img src="docs/images/trustops-assessment-architecture.svg" alt="Sources, lake, assessment core, API, UI, workflows, snapshots, trust shares" width="92%">
</p>

```mermaid
flowchart LR
  S[Read-only sources] --> I[Ingest]
  I --> L[Bronze / Silver / Gold]
  L --> A[Deterministic assessment]
  A --> U[Console & API]
  A --> R[Audit room & readiness]
  A --> W[Workflows & agents]
  W -->|approval| X[Audited writes]
  R --> T[Trust shares & snapshots]
```

| Layer       | Role                                                                 |
| ----------- | -------------------------------------------------------------------- |
| **Ingest**  | Idempotent connector sync into customer-owned storage                |
| **Assess**  | Pass / fail / stale / missing, freshness SLA, hashes, snapshot chain |
| **Review**  | Audit room score, gaps checklist, access reviews, auditor shares     |
| **Operate** | Dashboards, remediation, automation, trust-center links              |
| **Agents**  | Optional MCP + harness; writes stay approval-gated                   |

Details: [Architecture](docs/ARCHITECTURE.md) · [Audit readiness](docs/AUDIT_READINESS.md) · [Continuous ingestion](docs/CONTINUOUS_INGESTION.md) · [Agent harness](docs/AGENT_HARNESS.md) · [Visual system](docs/VISUAL_SYSTEM.md)

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"

security-lakehouse fixtures load --company golden --out build/lakehouse
security-lakehouse db upgrade --lake build/lakehouse
security-lakehouse serve --lake build/lakehouse --server --allow-insecure-no-auth --port 8787
```

Open **http://127.0.0.1:8787/console/dashboard/** — the golden fixture ships 37 controls with intentional gaps so the workbench has real posture to triage. Try **Audit room** at `/console/audit-room/`.

Production auth requires signed session cookies:

```bash
export TRUSTOPS_COOKIE_SIGNING_KEY="$(openssl rand -hex 32)"
security-lakehouse serve --lake build/lakehouse --server --port 8787
```

See [SERVER_AUTH.md](docs/SERVER_AUTH.md) for OIDC/SAML, API keys, and user admin.

```bash
curl -s http://127.0.0.1:8787/api/v1/posture/current | jq .
curl -s http://127.0.0.1:8787/api/v1/platform/audit-readiness | jq .
security-lakehouse assessment snapshot --lake build/lakehouse --reason demo
```

Regenerate README screenshots after UI changes: `make demo-screenshots` (server on `:8787`).

## Documentation

| Topic                    | Doc                                                                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| Product shape & parity   | [PRODUCT_SHAPE.md](docs/PRODUCT_SHAPE.md)                                                                                               |
| Product tour & UX        | [PRODUCT_WALKTHROUGH.md](docs/PRODUCT_WALKTHROUGH.md)                                                                                   |
| Audit readiness          | [AUDIT_READINESS.md](docs/AUDIT_READINESS.md)                                                                                           |
| Framework packs          | [FRAMEWORK_PACKS.md](docs/FRAMEWORK_PACKS.md)                                                                                           |
| Connectors & access      | [CONNECTORS.md](docs/CONNECTORS.md)                                                                                                     |
| Auth & tenancy           | [SERVER_AUTH.md](docs/SERVER_AUTH.md)                                                                                                   |
| Shareable POC            | [SHAREABLE_DEMO.md](docs/SHAREABLE_DEMO.md) · [SHAREABLE_POC_HOSTING.md](docs/SHAREABLE_POC_HOSTING.md)                                 |
| MCP evidence + approvals | [cookbook/MCP_EVIDENCE_AND_APPROVALS.md](docs/cookbook/MCP_EVIDENCE_AND_APPROVALS.md)                                                   |
| Ops runbooks             | [BACKUP_RESTORE.md](docs/runbooks/BACKUP_RESTORE.md) · [OBSERVABILITY_CONNECTOR_SYNC.md](docs/runbooks/OBSERVABILITY_CONNECTOR_SYNC.md) |
| Snowflake / ClickHouse   | [HERO_DATA_LAKES.md](docs/HERO_DATA_LAKES.md)                                                                                           |
| 85% self-hosted bar      | [TRUSTOPS_85_PLAN.md](docs/TRUSTOPS_85_PLAN.md)                                                                                         |
| Roadmap                  | [ROADMAP.md](ROADMAP.md)                                                                                                                |

## Verify

```bash
make smoke          # validate, pipeline, dashboard, pytest
make demo-screenshots   # optional: refresh docs/images/trustops-demo-*.png
```

## Repo layout

```text
src/security_lakehouse/   pipeline, assessment, API, auth, MCP
app/web/                  Next.js console (28 routes)
controls/ frameworks/     catalogs and mappings
deploy/                   Helm, Docker, Snowflake, ClickHouse, EKS
docs/                     architecture, walkthrough, diagrams, product shape
```

Framework labels in the UI are **neutral text marks** — not official certification logos. See [THIRD_PARTY_ASSETS.md](docs/THIRD_PARTY_ASSETS.md).
