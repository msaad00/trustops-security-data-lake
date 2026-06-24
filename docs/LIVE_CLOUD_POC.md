# Live Cloud POC

TrustOps can use live Azure, AWS, and Snowflake access for a stronger proof, but
the first POC must be read-only and reversible. Do not paste passwords,
human-scoped developer tokens, root keys, or broad cloud credentials into chat,
Git, screenshots, or PR bodies.

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

Run this Snowflake bootstrap from a role allowed to create a database,
warehouse, and role. It creates only TrustOps-owned objects and read-only views
over `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`.

```sql
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS TRUSTOPS_READER;
CREATE WAREHOUSE IF NOT EXISTS TRUSTOPS_READ_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;
CREATE DATABASE IF NOT EXISTS TRUSTOPS_SECURITY_LAKE;
CREATE SCHEMA IF NOT EXISTS TRUSTOPS_SECURITY_LAKE.EVIDENCE;

SET TRUSTOPS_POC_USER = CURRENT_USER();

GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE TRUSTOPS_READER;
GRANT USAGE ON WAREHOUSE TRUSTOPS_READ_WH TO ROLE TRUSTOPS_READER;
GRANT USAGE ON DATABASE TRUSTOPS_SECURITY_LAKE TO ROLE TRUSTOPS_READER;
GRANT USAGE ON SCHEMA TRUSTOPS_SECURITY_LAKE.EVIDENCE TO ROLE TRUSTOPS_READER;
GRANT ROLE TRUSTOPS_READER TO USER IDENTIFIER($TRUSTOPS_POC_USER);

CREATE OR REPLACE SECURE VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_AUDIT_EVENTS AS
SELECT
  QUERY_ID AS audit_id,
  USER_NAME AS actor,
  COALESCE(DATABASE_NAME || '.' || SCHEMA_NAME, DATABASE_NAME, WAREHOUSE_NAME, 'snowflake') AS object_name,
  CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 'observed' ELSE 'open' END AS status,
  CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 'info' ELSE 'medium' END AS severity,
  QUERY_ID AS evidence_ref,
  QUERY_ID AS query_id,
  QUERY_TYPE AS event_action
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP());

CREATE OR REPLACE SECURE VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_CONTROL_POSTURE AS
SELECT
  'SNOWFLAKE-AUDIT-QUERY-LOGGING' AS control_id,
  CASE WHEN COUNT(*) > 0 THEN 'passed' ELSE 'open' END AS status,
  CASE WHEN COUNT(*) > 0 THEN 10 ELSE 70 END AS risk_score,
  CASE WHEN COUNT(*) > 0 THEN 'low' ELSE 'high' END AS severity,
  'snowflake-query-history' AS evidence_ref,
  'SOC2' AS framework_id,
  0.95 AS confidence
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
UNION ALL
SELECT
  'SNOWFLAKE-FAILED-QUERY-REVIEW' AS control_id,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') = 0 THEN 'passed' ELSE 'open' END AS status,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') = 0 THEN 10 ELSE 60 END AS risk_score,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') = 0 THEN 'low' ELSE 'medium' END AS severity,
  'snowflake-query-failures' AS evidence_ref,
  'SOC2' AS framework_id,
  0.85 AS confidence
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP());

CREATE OR REPLACE SECURE VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_ASSET_RISK AS
SELECT
  'snowflake:warehouse:' || LOWER(COALESCE(WAREHOUSE_NAME, 'unknown')) AS asset_id,
  'warehouse' AS asset_type,
  'snowflake' AS owner,
  'prod' AS environment,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') > 0 THEN 60 ELSE 10 END AS risk_score,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') > 0 THEN 'open' ELSE 'observed' END AS status,
  CASE WHEN COUNT_IF(EXECUTION_STATUS <> 'SUCCESS') > 0 THEN 'medium' ELSE 'low' END AS severity,
  'snowflake-warehouse-' || LOWER(COALESCE(WAREHOUSE_NAME, 'unknown')) AS evidence_ref
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY COALESCE(WAREHOUSE_NAME, 'unknown');

CREATE OR REPLACE SECURE VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_EVIDENCE_BUNDLES AS
SELECT
  QUERY_ID AS bundle_id,
  QUERY_ID AS evidence_ref,
  CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 'observed' ELSE 'open' END AS status,
  CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 'info' ELSE 'medium' END AS severity,
  SHA2(QUERY_ID || ':' || COALESCE(QUERY_TEXT, ''), 256) AS hash_sha256,
  'snowflake://account_usage/query_history/' || QUERY_ID AS object_uri
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP());

GRANT SELECT ON VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_AUDIT_EVENTS TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_CONTROL_POSTURE TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_ASSET_RISK TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW TRUSTOPS_SECURITY_LAKE.EVIDENCE.TRUSTOPS_EVIDENCE_BUNDLES TO ROLE TRUSTOPS_READER;
```

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
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled

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
