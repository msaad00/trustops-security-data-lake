# Connector And Access Model

TrustOps should collect evidence with the smallest viable access boundary.

For ingestion idempotency, unique event IDs, headless/agent vs console surfaces,
and security-finding flow, see
[INGESTION_CONNECTORS_IDEMPOTENCY.md](INGESTION_CONNECTORS_IDEMPOTENCY.md).

## Default path (most teams)

**No customer security data lake required.** Connect read-only to source systems
(GitHub, AWS, Okta, …), sync evidence into TrustOps's assessment store, then run
control evaluation:

```text
discover scope → probe → enable → sync → eval
```

This is the same agentless model as typical GRC SaaS — scoped tokens and
read-only roles, not agents or broad cloud admin. TrustOps keeps the assessment
store in **your** boundary (`/lake` volume or self-hosted storage), not an opaque
vendor database.

Headless setup (curl, CLI, MCP): [playbooks/HEADLESS_CONNECTOR_SETUP.md](playbooks/HEADLESS_CONNECTOR_SETUP.md).

## Access modes (pick one)

| Mode                             | When to use                                           | Boundary                          |
| -------------------------------- | ----------------------------------------------------- | --------------------------------- |
| **Direct tool API read**         | **Default** — no existing evidence lake               | scoped token or app installation  |
| Existing security data lake read | You already have Snowflake/ClickHouse/S3/SIEM exports | read-only role                    |
| Managed evidence objects         | Local proof, starter deployments, demos               | dedicated schema/output directory |

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

Each catalog entry also carries **UX metadata** consumed by the console and demo kit:

| Field         | Purpose                                                                        |
| ------------- | ------------------------------------------------------------------------------ |
| `vendor`      | Short vendor label (AWS, GitHub, Snowflake, …)                                 |
| `description` | What evidence the connector ingests                                            |
| `setup_hint`  | Read-only connection guidance shown in `/connectors` and account-linking cards |

Connection field definitions live in `app/web/src/lib/connector-forms.ts`; vendor
marks use neutral text badges in `app/web/src/lib/connector-visuals.ts` (not
official logos — see [THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md)).

For live Azure, AWS, or Snowflake trials, use the least-privilege runbook in
[`docs/LIVE_CLOUD_POC.md`](LIVE_CLOUD_POC.md). It keeps first-run access
read-only and avoids passwords, human-scoped developer tokens, root keys, and
broad cloud credentials.

For production operation, use
[`docs/CONTINUOUS_INGESTION.md`](CONTINUOUS_INGESTION.md). It describes the
customer-owned identity boundary, probe-gated enablement, scheduler loop,
idempotent raw upserts, API limits, error behavior, and snapshot integrity.

List configured connector contracts:

```bash
security-lakehouse connectors list
```

## Connector Runner

TrustOps currently has **17 connector contracts**. **Fourteen** are executable
runners (eight direct source/API runners plus Snowflake, ClickHouse, S3, SIEM,
and runtime-gateway existing-lake readers and the Okta System Log incremental adapter). The remaining
entries are read-only access contracts or managed evidence boundaries — probes
validate configuration but **sync is not available** until a collection adapter
ships.

| Connector ID                | Source                  | Runner status                 |
| --------------------------- | ----------------------- | ----------------------------- |
| `github-security`           | GitHub repo security    | executable                    |
| `gitlab-security`           | GitLab repo security    | executable                    |
| `aws-posture`               | AWS IAM/posture         | executable                    |
| `okta-identity`             | Okta identity/MFA       | executable                    |
| `google-workspace-identity` | Google Workspace users  | executable                    |
| `gcp-posture`               | GCP IAM/posture         | executable                    |
| `azure-posture`             | Azure IAM/posture       | executable                    |
| `jira-ticketing`            | Jira tickets/workflows  | executable                    |
| `snowflake-evidence-lake`   | governed evidence lake  | executable existing-lake read |
| `clickhouse-telemetry-lake` | telemetry analytics     | executable existing-lake read |
| `object-storage-evidence`   | object evidence store   | executable existing-lake read |
| `okta-system-log`           | Okta System Log API     | **implemented** (incremental) |
| `siem-alerts`               | SIEM/detection exports  | executable existing-lake read |
| `runtime-gateway`           | runtime policy events   | executable existing-lake read |
| `identity-provider`         | generic identity source | **contract only** (no sync)   |
| `ticketing`                 | generic ticketing       | **contract only** (no sync)   |
| `managed-local-evidence`    | local starter evidence  | managed evidence object       |

Every executable runner writes valid raw evidence into:

```text
<lake>/raw/connector_events.jsonl
```

The production lifecycle is intentionally the same for UI, API, CLI, scheduler,
and agents:

1. create a scoped source role, app, or service identity,
2. discover the read scope visible to that identity,
3. probe the exact credential reference and scope,
4. enable only after the probe succeeds,
5. sync manually or by schedule.

### AWS multi-account scale

AWS posture uses the same third-party role pattern for one account or hundreds:

| Item          | Scaling rule                                                                                                                            |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Rollout       | Use **CloudFormation StackSets** or **Terraform workspaces** to deploy the same read-only role across target AWS accounts.              |
| Authorization | The deployed role trusts the TrustOps runtime principal and constrains access with External ID.                                         |
| External ID   | Use **one External ID per deployed role**; TrustOps includes that exact value in STS AssumeRole.                                        |
| Confirmation  | Default role names can be confirmed by AWS account ID; custom role names use the Role ARN output.                                       |
| Scale surface | **Bulk account import** is the follow-up console/API surface for registering many deployed roles after rollout.                         |
| Sync          | The scheduled sync assumes each registered role, receives short-lived session credentials, and reads only the granted IAM posture APIs. |
| Evaluation    | Raw evidence keeps the AWS account ID attached; deterministic controls evaluate across the combined evidence set.                       |

<p align="center">
  <img src="images/trustops-readonly-connections.svg" alt="Read-only connector model: AWS IAM role, GitHub App, Okta token, Snowflake SELECT into TrustOps ingestion" width="100%">
</p>

Mermaid diagrams: [connector-ingestion.md](diagrams/connector-ingestion.md)

Do not paste passwords, human-scoped developer tokens, root keys, or private
keys into TrustOps. Use SSO, an assumable role, OAuth, key-pair auth, or a
secret-manager reference. TrustOps records a non-secret fingerprint so a later
enable action must match the probed access payload.

Probe and enable a fixture-backed GitHub connector:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id github-security \
  --credentials-json '{"token":"fixture-read-token"}' \
  --options-json '{"org":"acme"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id github-security \
  --state enabled \
  --credentials-json '{"token":"fixture-read-token"}' \
  --options-json '{"org":"acme"}'

security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id github-security \
  --repo OWNER/REPO \
  --fixture-dir tests/fixtures/github-governance
```

For live GitHub collection, use a GitHub App installation token from the
selected environment variable or secret manager. The configure payload should
store the reference name, not the raw token:

The minimum GitHub App repository permissions are:

| Permission                   | Access unlocked                                                            |
| ---------------------------- | -------------------------------------------------------------------------- |
| Metadata: read               | Repository identity, visibility, and default branch                        |
| Administration: read         | Branch protection, collaborators, teams, and Actions workflow defaults     |
| Code scanning alerts: read   | Aggregate code-scanning counts by state and severity                       |
| Secret scanning alerts: read | Aggregate secret-scanning counts by state; alert details are not persisted |
| Dependabot alerts: read      | Aggregate dependency-alert counts by state and severity                    |

TrustOps follows GitHub list pagination for these alert APIs, capped at 1,000
records per category per sync. It persists aggregate counts only; alert payloads,
secret material, and tokens are not copied into evidence.

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id github-security \
  --credentials-json '{"credential_ref":"TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"}' \
  --options-json '{"repo":"OWNER/REPO"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id github-security \
  --state enabled \
  --credentials-json '{"credential_ref":"TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"}' \
  --options-json '{"repo":"OWNER/REPO"}'

TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN=... security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id github-security \
  --repo OWNER/REPO
```

GitLab governance sync (fixture-backed or live token):

```bash
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id gitlab-security \
  --repo GROUP/PROJECT \
  --fixture-dir tests/fixtures/gitlab-governance

TRUSTOPS_GITLAB_ACCESS_TOKEN=... security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id gitlab-security \
  --repo GROUP/PROJECT
```

Self-managed GitLab: set `TRUSTOPS_GITLAB_API_URL` to your instance API base
(for example `https://gitlab.example.com/api/v4`) before sync.

Snowflake is the read-existing-lake path. The fixture path mirrors the expected
views (`audit_events`, `control_posture`, `asset_risk`, and
`evidence_bundles`) and exercises the same raw-to-gold pipeline:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"fixture","user":"trustops_reader","credential_ref":"fixture-sso"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled \
  --credentials-json '{"account":"fixture","user":"trustops_reader","credential_ref":"fixture-sso"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --fixture-dir tests/fixtures/snowflake
```

ClickHouse is the high-velocity telemetry lake reader. The fixture path mirrors
`security.normalized_events` from `deploy/clickhouse/schema.sql` and uses
append-mode ingestion with a high-water cursor:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id clickhouse-telemetry-lake \
  --credentials-json '{"host":"https://cluster.example.clickhouse.cloud:8443","user":"trustops_reader","credential_ref":"TRUSTOPS_CLICKHOUSE_TOKEN"}' \
  --options-json '{"database":"security","table":"normalized_events"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id clickhouse-telemetry-lake \
  --state enabled \
  --credentials-json '{"host":"https://cluster.example.clickhouse.cloud:8443","user":"trustops_reader","credential_ref":"TRUSTOPS_CLICKHOUSE_TOKEN"}' \
  --options-json '{"database":"security","table":"normalized_events"}'

security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id clickhouse-telemetry-lake \
  --fixture-dir tests/fixtures/clickhouse-telemetry-lake
```

For live ClickHouse collection, point the connector at your cluster HTTP endpoint
and mount the read-only token via `TRUSTOPS_CLICKHOUSE_TOKEN` (or the
`credential_ref` you configured). TrustOps only issues `SELECT` reads against
the discovered table, keyset-paginated on the composite `(event_time, event_id)`
cursor with `LIMIT` so a large table streams in bounded pages instead of one
unbounded response; rows sharing an `event_time` across a page boundary are never
dropped, and the append-mode merge dedups by `event_id` as a second safety net.

### Alert- and event-export pagination (SIEM, runtime-gateway)

The `siem-alerts` and `runtime-gateway` readers pull an incremental window with a
watermark cursor (`?since=`) and follow server-side pagination within that window:
when a response is a JSON object carrying a `next_cursor` string, TrustOps requests
the next page with `?cursor=<token>` and repeats until `next_cursor` is absent. An
export that returns a bare JSON array (or an object without `next_cursor`) is read
as a single page, so a non-paginating endpoint still works unchanged.

For live Snowflake collection, install the cloud connector extra and use the
fixed POC objects from [`docs/LIVE_CLOUD_POC.md`](LIVE_CLOUD_POC.md):
`TRUSTOPS_SECURITY_LAKE.EVIDENCE`, `TRUSTOPS_READ_WH`, and `TRUSTOPS_READER`.
For a human POC, use browser SSO. This is not the scheduled-ingestion path.
TrustOps only issues `SELECT * FROM <view>` reads:

```bash
uv pip install -e ".[cloud]"

SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER="$SNOWFLAKE_USER" \
SNOWFLAKE_AUTHENTICATOR=externalbrowser \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake
```

Headless jobs should use a non-human service user such as
`TRUSTOPS_INGEST_SVC`, with only `TRUSTOPS_READER` and warehouse `USAGE`.
Snowflake key-pair auth uses a mounted private-key file path, not raw key
contents in connector config:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"TRUSTOPS_INGEST_SVC","private_key_ref":"SNOWFLAKE_PRIVATE_KEY_FILE"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","role":"TRUSTOPS_READER","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER=TRUSTOPS_INGEST_SVC \
SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT \
SNOWFLAKE_PRIVATE_KEY_FILE="$SNOWFLAKE_PRIVATE_KEY_FILE" \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake
```

OAuth is also supported when the customer's runtime has a governed token broker:
set `SNOWFLAKE_AUTHENTICATOR=oauth` and inject `SNOWFLAKE_OAUTH_TOKEN` from the
secret manager at process start. The raw value is not written into the lake.

Object storage evidence uses read-only LIST against an S3 prefix and syncs in
**snapshot** mode so removed objects disappear from the lake on the next pull:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id object-storage-evidence \
  --credentials-json '{"role_arn":"arn:aws:iam::123456789012:role/TrustOpsEvidenceRead"}' \
  --options-json '{"bucket":"trustops-evidence","prefix":"bundles/"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id object-storage-evidence \
  --state enabled \
  --credentials-json '{"role_arn":"arn:aws:iam::123456789012:role/TrustOpsEvidenceRead"}' \
  --options-json '{"bucket":"trustops-evidence","prefix":"bundles/"}'

security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id object-storage-evidence \
  --fixture-dir tests/fixtures/object-storage-evidence
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
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id github-security \
  --credentials-json '{"credential_ref":"TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"}' \
  --options-json '{"repo":"OWNER/REPO"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id github-security \
  --state enabled \
  --credentials-json '{"credential_ref":"TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN"}' \
  --options-json '{"repo":"OWNER/REPO"}' \
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
TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN=... security-lakehouse repo governance-sync OWNER/REPO --out build/repo-governance.jsonl
```

The public audit path requires no credentials. The governance sync path uses a
GitHub App installation token or fixture bundle for private branch rules,
collaborators, teams, workflow permissions, and security-setting summaries.

The validator rejects:

- missing collection mode, access boundary, route, permissions, or freshness SLO
- existing-lake connectors that are not read-only
- direct API connectors that are not scoped-token based
- managed evidence mode without a dedicated schema/boundary
- secret-like field names or token-shaped values in the catalog
- broad permission words such as admin, delete, drop, modify, owner, or root

## Ingestion strategy (velocity + cost)

A compliance data layer that claims _real-time control health_ must justify
**how** each source is ingested, because streaming is not free. Every connector
declares three attributes that drive an auditable ingestion decision (encoded in
`src/security_lakehouse/ingestion/strategy.py`, not prose):

- `velocity`: `high_event_stream` · `medium_api` · `low_current_state`
- `native_connector`: whether a managed/native ingestion connector exists for the source
- `data_shape`: `event_log` · `current_state`

| Velocity            | Native? | Method                                       | Why                                                                                                                                                                                                       |
| ------------------- | ------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `high_event_stream` | any     | **Snowpipe Streaming**                       | Seconds-fresh, serverless, no warehouse COPY; ~50% cheaper than file Snowpipe at high throughput (unified ~0.0037 credits/GB). INSERT-only — upserts handled downstream via Streams/Tasks/Dynamic Tables. |
| `medium_api`        | true    | **Managed/native connector** (e.g. Openflow) | Managed runtime, less code, vendor-managed auth, built-in observability.                                                                                                                                  |
| `medium_api`        | false   | **Committed custom pull**                    | No native connector: watermark + cursor pagination + 429 backoff + idempotent merge.                                                                                                                      |
| `low_current_state` | any     | **Scheduled pull** (hourly/daily)            | Slow churn; streaming would add producer cost + ops for zero freshness benefit the control needs.                                                                                                         |

**Cost discipline:** streaming bills per client-runtime-hour + per-GB and you own
the producer. The strategy makes `high_event_stream` the _only_ path to streaming,
so it is chosen only when a control's `freshness_slo` actually requires sub-minute
data — never claimed where a native connector does not exist.

Inspect the resolved plan per source (a live demo command):

```bash
security-lakehouse ingestion plan        # table: velocity → method → SLO + cost note
security-lakehouse ingestion plan --json  # machine-readable
```

## Okta: two velocities, not one

A common misread is "Okta is high-volume, so stream it." Okta actually exposes
**two sources at very different velocities**, and most access _controls_ read the
slow one:

| Source            | data_shape      | velocity            | freshness | ingestion                                                              | feeds                                              |
| ----------------- | --------------- | ------------------- | --------- | ---------------------------------------------------------------------- | -------------------------------------------------- |
| `okta-identity`   | `current_state` | `low_current_state` | 1h        | scheduled pull                                                         | MFA-coverage, orphaned/terminated-account controls |
| `okta-system-log` | `event_log`     | `medium_api`        | 15m       | **implemented** — incremental pull with watermark cursor + 429 backoff | failed-login / auth-anomaly controls (e.g. AC-7)   |

The current-state source (users, factors, policies) changes slowly, so an hourly
scheduled pull is correct and cheapest. The System Log is event-shaped and needs
~15-minute freshness for failed-login controls; it is pulled incrementally with a
high-water cursor (`gold/watermarks.jsonl`) rather than streamed, because the
Okta System Log is a polled API. Modeling them separately keeps each control on
the right freshness/cost path instead of over-provisioning the whole connector to
the strictest SLO.

## Google Workspace: two credential shapes

`google-workspace-identity` accepts either an already-minted access token or the
OAuth material to mint tokens itself. Pick one:

| Shape               | Credentials                                             | When                                                                     |
| ------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------ |
| Static access token | `credential_ref`                                        | Your secret manager already rotates a short-lived Directory access token |
| Unattended refresh  | `refresh_token_ref` + `client_id` + `client_secret_ref` | Scheduled sync with nothing external minting tokens                      |

Both need `customer_id`. The `*_ref` fields name environment variables, never raw
secrets; a `<NAME>_FILE` variant is preferred over the inline value when both are
present. With the refresh shape, TrustOps exchanges the refresh token at
`oauth2.googleapis.com/token` on first use, near expiry (300s skew), or once on a
401, and the resolved access token stays in memory only.

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id google-workspace-identity \
  --credentials-json '{"customer_id":"C01234567","refresh_token_ref":"GOOGLE_WORKSPACE_REFRESH_TOKEN","client_id":"123-abc.apps.googleusercontent.com","client_secret_ref":"GOOGLE_WORKSPACE_OAUTH_CLIENT_SECRET"}'
```

Supplying part of the refresh triple is rejected at probe and enable time with the
specific missing fields, because a partial triple silently falls back to the
static-token path at sync time.
