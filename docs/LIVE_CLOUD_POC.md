# Live Cloud POC

TrustOps can use live Azure, AWS, and Snowflake access for a stronger proof, but
the first POC must be read-only and reversible. Do not paste passwords,
human-scoped developer tokens, root keys, or broad cloud credentials into chat,
Git, screenshots, or PR bodies.

For repeatable end-to-end proof, use
[`security-lakehouse scenario run live-cloud-posture`](SCENARIOS.md) after the
provider-specific setup below. The scenario syncs connectors, materializes the
lake, verifies evidence integrity, freezes a snapshot, runs a workflow DAG, and
writes a JSON report.

## Credential Boundary

Preferred order:

1. local SSO or CLI profile, such as `aws sso login` or `az login`
2. short-lived assumed role or service principal scoped to read-only posture
3. OAuth token or secret-manager reference exposed only as an environment
   variable for the local process

TrustOps should store configuration metadata and fingerprints, not raw cloud
secrets. Use fixtures until a live probe proves access.

## AWS Trial Account

The current AWS runner uses the standard `boto3` credential chain and only calls:

- `iam:ListUsers`
- `iam:ListMFADevices`
- `iam:GetAccountPasswordPolicy`
- `iam:GetAccountSummary`

Use an SSO profile or assumed read-only role. Do not create root credentials.

```bash
aws sso login --profile trustops-poc
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id aws-posture \
  --state enabled

AWS_PROFILE=trustops-poc \
AWS_ACCOUNT_ID=<account-id> \
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id aws-posture
```

Expected artifact:

```text
build/lakehouse/raw/connector_events.jsonl
```

## Azure Subscription

The current Azure runner uses `DefaultAzureCredential`, so it can use `az login`,
managed identity, or service-principal environment variables without TrustOps
persisting the credential. The connector reads:

- role assignments
- policy assignments
- subscription resources

For a POC, built-in `Reader` at subscription scope is usually enough for
resources and policy assignments. Add an explicit role-assignment read grant if
the tenant blocks that read.

```bash
az login
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id azure-posture \
  --state enabled

AZURE_SUBSCRIPTION_ID=<subscription-id> security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id azure-posture
```

## Snowflake Evidence Lake

Snowflake is the existing-lake path. TrustOps should read curated evidence views
and never create, update, or delete source objects in the first POC.

Use these fixed POC names:

- database: `TRUSTOPS_SECURITY_LAKE`
- schema: `TRUSTOPS_SECURITY_LAKE.EVIDENCE`
- warehouse: `TRUSTOPS_READ_WH`
- read role: `TRUSTOPS_READER`
- views: `TRUSTOPS_AUDIT_EVENTS`, `TRUSTOPS_CONTROL_POSTURE`, `TRUSTOPS_ASSET_RISK`,
  `TRUSTOPS_EVIDENCE_BUNDLES`

Run [`deploy/snowflake/bootstrap_poc.sql`](../deploy/snowflake/bootstrap_poc.sql)
from a role allowed to create a database, warehouse, and role. It creates only
TrustOps-owned objects and read-only views over
`SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`. It does not create users, passwords,
stages, integrations, or external network access.

Validate counts before connecting TrustOps:

```sql
USE ROLE TRUSTOPS_READER;
USE WAREHOUSE TRUSTOPS_READ_WH;
USE DATABASE TRUSTOPS_SECURITY_LAKE;
USE SCHEMA EVIDENCE;

SELECT COUNT(*) AS audit_events
FROM TRUSTOPS_AUDIT_EVENTS;

SELECT COUNT(*) AS control_posture
FROM TRUSTOPS_CONTROL_POSTURE;

SELECT COUNT(*) AS asset_risk
FROM TRUSTOPS_ASSET_RISK;

SELECT COUNT(*) AS evidence_bundles
FROM TRUSTOPS_EVIDENCE_BUNDLES;
```

For a human POC, use browser SSO. No Snowflake credential needs to be pasted
into chat, Git, or TrustOps config:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"'"$SNOWFLAKE_USER"'","credential_ref":"externalbrowser"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"'"$SNOWFLAKE_USER"'","credential_ref":"externalbrowser"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

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

For headless automation, use OAuth or workload-managed identity materialized
outside the repo and pass only the environment variable into the process:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"'"$SNOWFLAKE_USER"'","credential_ref":"SNOWFLAKE_OAUTH_TOKEN"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"'"$SNOWFLAKE_USER"'","credential_ref":"SNOWFLAKE_OAUTH_TOKEN"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER="$SNOWFLAKE_USER" \
SNOWFLAKE_AUTHENTICATOR=oauth \
SNOWFLAKE_OAUTH_TOKEN="$SNOWFLAKE_OAUTH_TOKEN" \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse connectors sync \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake
```

The default views are:

- `TRUSTOPS_AUDIT_EVENTS`
- `TRUSTOPS_CONTROL_POSTURE`
- `TRUSTOPS_ASSET_RISK`
- `TRUSTOPS_EVIDENCE_BUNDLES`

Override them only when the customer has already standardized different view
names:

```bash
SNOWFLAKE_VIEW_AUDIT_EVENTS=<view_name>
SNOWFLAKE_VIEW_CONTROL_POSTURE=<view_name>
SNOWFLAKE_VIEW_ASSET_RISK=<view_name>
SNOWFLAKE_VIEW_EVIDENCE_BUNDLES=<view_name>
```

## Remediation Boundary

Do not grant write/remediation access in the first live POC. Remediation should
be a separate opt-in executor role with:

- a different identity from read-only ingestion
- explicit human approval
- narrow allowed actions
- full audit logging
- rollback notes for each action

Until that exists, live connectors should only ingest, normalize, tag, evaluate,
snapshot, and create internal remediation tasks.
