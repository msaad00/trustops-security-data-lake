# Visual System

The product should feel like an assessment console, not a report. The visual
language should make current posture, violations, owners, evidence, and
snapshots understandable for both humans and agents.

## Framework visual identity

Neutral **gradient marks** with Lucide icons identify each program (SOC 2, ISO,
FedRAMP, CIS AWS, etc.) without shipping official certification logos. See
`app/web/src/lib/framework-visuals.ts`, `FrameworkMark`, and `FrameworkBadge`.

Shared KPI tiles use `KpiTile` with tone accents (default / ready / attention /
critical / brand). Compliance rings and bar scoreboards mirror managed GRC-style
program dashboards on the trust command center.

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

## Interaction Patterns

- filters for framework, owner, severity, source, status, and environment
- collapsible evidence details
- clickable controls and assets
- snapshot button with explicit reason
- copyable API routes
- tags for `current`, `snapshot`, `stale`, `open`, `owner`, `framework`

## Diagram Inventory

- [Architecture](ARCHITECTURE.md)
- [Data Model](DATA_MODEL.md)
- [Dual Lakehouse](diagrams/dual-lakehouse.md)
- [Evaluation Lifecycle](diagrams/evaluation-lifecycle.md)
- [Hosting](diagrams/hosting.md)
- [SVG Architecture](images/trustops-assessment-architecture.svg)
- [README Product Mosaic](images/trustops-product-mosaic.svg)
- [Snowflake Evidence Lake](images/trustops-snowflake-evidence-lake.svg)
