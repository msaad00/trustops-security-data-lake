# Connector And Access Model

TrustOps should collect evidence with the smallest viable access boundary.

## Access Priority

| Priority | Mode                             | Best for                                              | Boundary                          |
| -------- | -------------------------------- | ----------------------------------------------------- | --------------------------------- |
| 1        | Existing security data lake read | Snowflake, ClickHouse, object storage, SIEM exports   | read-only role                    |
| 2        | Managed evidence objects         | one-company rollout, local proof, starter deployments | dedicated schema/output directory |
| 3        | Direct tool API read             | source systems that are the evidence authority        | scoped token or app installation  |

Avoid broad cloud permissions. Connectors should not need admin, delete, owner,
or unrestricted write access to evaluate posture.

## Production Hero Paths

| Store      | Role                                                | Connector                   |
| ---------- | --------------------------------------------------- | --------------------------- |
| Snowflake  | governed evidence, audit views, retention, RBAC     | `snowflake-evidence-lake`   |
| ClickHouse | telemetry, runtime events, trends, fast aggregation | `clickhouse-telemetry-lake` |

## Catalog

The connector catalog is versioned in:

```text
connectors/catalog.json
```

Validate it with:

```bash
security-lakehouse connectors validate
```

List configured connector contracts:

```bash
security-lakehouse connectors list
```

## Connector Runner

TrustOps currently has 15 connector contracts. Seven are executable source
runners; the remaining entries describe read-only lake contracts or managed
evidence boundaries.

| Connector ID                | Source                  | Runner status              |
| --------------------------- | ----------------------- | -------------------------- |
| `github-security`           | GitHub repo security    | executable                 |
| `aws-posture`               | AWS IAM/posture         | executable                 |
| `okta-identity`             | Okta identity/MFA       | executable                 |
| `google-workspace-identity` | Google Workspace users  | executable                 |
| `gcp-posture`               | GCP IAM/posture         | executable                 |
| `azure-posture`             | Azure IAM/posture       | executable                 |
| `jira-ticketing`            | Jira tickets/workflows  | executable                 |
| `snowflake-evidence-lake`   | governed evidence lake  | read-only lake contract    |
| `clickhouse-telemetry-lake` | telemetry analytics     | read-only lake contract    |
| `object-storage-evidence`   | object evidence store   | read-only lake contract    |
| `siem-alerts`               | SIEM/detection exports  | read-only lake contract    |
| `runtime-gateway`           | runtime policy events   | read-only lake contract    |
| `identity-provider`         | generic identity source | contract, no direct runner |
| `ticketing`                 | generic ticketing       | contract, no direct runner |
| `managed-local-evidence`    | local starter evidence  | managed evidence object    |

Every executable runner writes valid raw evidence into:

```text
<lake>/raw/connector_events.jsonl
```

Enable the connector, then sync it:

```bash
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id github-security \
  --state enabled

security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id github-security \
  --repo OWNER/REPO \
  --fixture-dir tests/fixtures/github-governance
```

For live collection, omit `--fixture-dir` and provide a read-only token through
the selected token environment variable:

```bash
GITHUB_TOKEN=... security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id github-security \
  --repo OWNER/REPO
```

By default the runner rebuilds bronze, silver, gold, marts, and current posture
from the managed raw connector file. Use `--no-materialize` when you only want
to collect raw evidence. Every sync attempt is recorded in
`gold/connector_runs.jsonl`.

## Scheduled Sync

Manual sync proves the connector. Scheduled sync makes the connector part of
continuous posture.

Persist scheduler options on the connector configuration:

```bash
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id github-security \
  --state enabled \
  --sync-schedule "every 15m" \
  --repo OWNER/REPO
```

Run the scheduler from cron, Kubernetes `CronJob`, or the local daemon:

```bash
security-lakehouse scheduler tick --lake build/lakehouse
security-lakehouse scheduler run --lake build/lakehouse --tick-seconds 60
```

Supported schedule expressions are intentionally small and portable:
`@hourly`, `@daily`, `every Nm`, and `every Nh`. The scheduler records last
fire time in `gold/scheduler_state.jsonl`, writes sync history to
`gold/connector_runs.jsonl`, and uses the same connector runner as
`connectors sync`; it does not use a separate evidence path.

Repository evidence has two concrete collection paths:

```bash
security-lakehouse repo audit https://github.com/OWNER/REPO --out build/repo-audit.jsonl
GITHUB_TOKEN=... security-lakehouse repo governance-sync OWNER/REPO --out build/repo-governance.jsonl
```

The public audit path requires no credentials. The governance sync path uses a
read-only token or fixture bundle for private branch rules, collaborators,
teams, workflow permissions, and security-setting summaries.

The validator rejects:

- missing collection mode, access boundary, route, permissions, or freshness SLO
- existing-lake connectors that are not read-only
- direct API connectors that are not scoped-token based
- managed evidence mode without a dedicated schema/boundary
- secret-like field names or token-shaped values in the catalog
- broad permission words such as admin, delete, drop, modify, owner, or root
