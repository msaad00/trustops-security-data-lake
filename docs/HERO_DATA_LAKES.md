# Hero Security Data Lakes

This project tells a two-backend security analytics story:

| Backend    | Best fit                             | Security value                                                              |
| ---------- | ------------------------------------ | --------------------------------------------------------------------------- |
| Snowflake  | governed enterprise evidence lake    | auditor sharing, retention, RBAC, data clean rooms, cross-team reporting    |
| ClickHouse | high-volume telemetry analytics lake | fast runtime/security event analytics, detections, dashboards, aggregations |

The local pipeline remains the source of truth for the demo. It writes replayable
bronze/silver/gold artifacts and a SQLite mart so the project can run anywhere.
Snowflake and ClickHouse artifacts show how the same normalized model maps to
production-grade backends.

## Snowflake Story

Snowflake is the governed enterprise evidence lake:

- lands low-latency evidence through row streaming or staged files
- supports governed read roles, row policies, masking policies, and query history
- derives posture with warehouse-native rollups instead of pulling every record
  into the app
- can expose the same tables through an Iceberg/Open Catalog path when the
  customer wants open-format interoperability
- keeps evidence, retention, audit history, and role boundaries in the operator
  account

Use Snowflake when the question is:

- "Can audit and GRC trust this evidence?"
- "Can business leaders slice risk by owner, product, and environment?"
- "Can we share controlled evidence with internal stakeholders?"
- "Can the trust tool evaluate posture where our lake already lives?"

![TrustOps Snowflake evidence lake architecture](images/trustops-snowflake-evidence-lake.svg)

### Which Snowflake Ingestion Lane To Use

| Lane                 | Best fit                                                               | TrustOps behavior                                                     |
| -------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Row streaming        | runtime AI events, identity changes, detections, policy events         | append rows into evidence/event tables with stable IDs                |
| Staged files         | scanner exports, access review bundles, SARIF, vendor evidence packets | load batch files, preserve raw hash, then normalize                   |
| Read-only views      | customer already has a governed Snowflake security lake                | query least-privilege views and rebuild current posture               |
| Iceberg/Open Catalog | customer wants open table access across engines                        | keep tables interoperable for Spark, Trino, DuckDB, and other readers |

The live Snowflake runner is intentionally read-only by default. It expects
TrustOps-shaped evidence views with a least-privilege role, writes collected rows
into managed raw connector evidence, and lets the same pipeline rebuild bronze,
silver, gold, snapshots, and current posture. The runner does not create
Snowflake objects, mutate warehouse state, or require DDL privileges.

Official Snowflake references:

- [Snowpipe Streaming](https://docs.snowflake.com/en/user-guide/snowpipe-streaming/data-load-snowpipe-streaming-overview)
  for low-latency row ingestion and Kafka/application event streams.
- [Dynamic tables](https://docs.snowflake.com/en/user-guide/dynamic-tables/overview)
  for declarative rollups from fresh evidence into posture-ready views.
- [Streams](https://docs.snowflake.com/en/user-guide/streams-intro) and tasks
  for change tracking and scheduled SQL-native workflows.
- [Row access policies](https://docs.snowflake.com/en/user-guide/security-row-intro)
  and masking policies for tenant, role, and sensitive-field controls.
- [Snowflake Open Catalog with Apache Iceberg](https://docs.snowflake.com/en/user-guide/tables-iceberg-open-catalog)
  for open-table interoperability where the operator wants external engines to
  read the same governed table path.

Primary artifacts:

- [Snowflake schema](../deploy/snowflake/schema.sql)
- [Snowflake connector model](CONNECTORS.md#connector-runner)
- [Dual-lakehouse diagram](diagrams/dual-lakehouse.md)

## ClickHouse Story

ClickHouse is the high-throughput security telemetry lake:

- stores normalized events and runtime security telemetry
- optimizes time-window, severity, source, and asset aggregations
- powers low-latency dashboards and investigation queries
- keeps high-cardinality runtime/event data cheap to query

Use ClickHouse when the question is:

- "What happened in the last 15 minutes?"
- "Which runtime policies are blocking risky agent behavior?"
- "Which assets and controls are trending worse at event scale?"

Primary artifacts:

- [ClickHouse schema](../deploy/clickhouse/schema.sql)
- [Local ClickHouse compose file](../deploy/clickhouse/docker-compose.yml)
- [Dual-lakehouse diagram](diagrams/dual-lakehouse.md)

## Portfolio Positioning

This is not just a dashboard. It demonstrates:

- security event modeling
- control mapping
- evidence lineage
- warehouse/lakehouse schema design
- operational analytics
- auditor-facing reporting
- agent-assisted investigation

The same event model can land in both warehouses:

```text
raw JSONL evidence
  -> bronze replay records
  -> silver normalized_events
  -> gold control_posture + asset_risk + metrics
  -> Snowflake governed evidence lake
  -> ClickHouse high-volume telemetry lake
```
