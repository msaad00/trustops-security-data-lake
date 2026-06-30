# Visual System

The product should feel like an assessment console, not a report. The visual
language should make current posture, violations, owners, evidence, and
snapshots understandable for both humans and agents.

## Out-Of-Box Views

| View              | Purpose                                                       |
| ----------------- | ------------------------------------------------------------- |
| Executive posture | score, state, open violations, stale evidence, trend          |
| Control workbench | framework, control, owner, status, evidence coverage          |
| Violation queue   | severity, asset, owner, source, evidence, raw hash            |
| Evidence room     | evidence refs, source systems, collection time, snapshot hash |
| Data model        | assets, evidence, controls, tests, violations, snapshots      |
| Lake routing      | Snowflake governed evidence, ClickHouse telemetry analytics   |
| Agent console     | API routes, skills, allowed actions, snapshot controls        |
| Connectors        | vendor marks, ingestion pipeline, managed GRC compare strip   |
| Access / auth     | IdP marks, identity flow, session + RBAC                      |
| Deploy            | OSS / self-hosted / hosted models + go-live flow              |

## Marks (not official logos)

| Family | Component | Policy |
| ------ | --------- | ------ |
| Frameworks | `FrameworkBadge` | Neutral text marks — SOC, ISO, PCI, … |
| Connectors | `ConnectorMark` | Vendor-colored abbreviations — AWS, GH, OKTA, … |
| Identity | `AuthMark` | IdP-colored abbreviations — Okta, Entra, SAML, KEY |

See [THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md).

## Interaction Patterns

- filters for framework, owner, severity, source, status, and environment
- collapsible evidence details
- clickable controls and assets
- snapshot button with explicit reason
- copyable API routes
- tags for `current`, `snapshot`, `stale`, `open`, `owner`, `framework`
- horizontal **flow strips** for ingestion, auth, and deployment paths

## Diagram Inventory

Full index: [diagrams/README.md](diagrams/README.md)

### Architecture & data

- [Architecture](ARCHITECTURE.md)
- [Data Model](DATA_MODEL.md)
- [Dual Lakehouse](diagrams/dual-lakehouse.md)
- [Evaluation Lifecycle](diagrams/evaluation-lifecycle.md)
- [Hosting](diagrams/hosting.md)

### Connectors & ingestion

- [Connector ingestion (mermaid)](diagrams/connector-ingestion.md)
- [Read-only connections (SVG)](images/trustops-readonly-connections.svg)
- [Continuous ingestion](CONTINUOUS_INGESTION.md)

### Identity & deployment

- [Auth identity (mermaid)](diagrams/auth-identity.md)
- [Identity boundary (SVG)](images/trustops-identity-boundary.svg)
- [Deployment models (mermaid)](diagrams/deployment-models.md)
- [Deployment & pricing](DEPLOYMENT_AND_PRICING.md)

### Hero SVGs

- [Assessment architecture](images/trustops-assessment-architecture.svg)
- [Product mosaic](images/trustops-product-mosaic.svg)
- [Snowflake evidence lake](images/trustops-snowflake-evidence-lake.svg)
