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
and never create, update, or delete Snowflake objects in the first POC.

Minimum role grants:

```sql
CREATE ROLE IF NOT EXISTS TRUSTOPS_READER;
CREATE WAREHOUSE IF NOT EXISTS TRUSTOPS_READ_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60;

GRANT USAGE ON WAREHOUSE TRUSTOPS_READ_WH TO ROLE TRUSTOPS_READER;
GRANT USAGE ON DATABASE <EVIDENCE_DATABASE> TO ROLE TRUSTOPS_READER;
GRANT USAGE ON SCHEMA <EVIDENCE_DATABASE>.<EVIDENCE_SCHEMA> TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW <EVIDENCE_DATABASE>.<EVIDENCE_SCHEMA>.TRUSTOPS_AUDIT_EVENTS TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW <EVIDENCE_DATABASE>.<EVIDENCE_SCHEMA>.TRUSTOPS_CONTROL_POSTURE TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW <EVIDENCE_DATABASE>.<EVIDENCE_SCHEMA>.TRUSTOPS_ASSET_RISK TO ROLE TRUSTOPS_READER;
GRANT SELECT ON VIEW <EVIDENCE_DATABASE>.<EVIDENCE_SCHEMA>.TRUSTOPS_EVIDENCE_BUNDLES TO ROLE TRUSTOPS_READER;
```

Use OAuth or key-pair auth managed outside the repo. The local process can read
the OAuth token from an environment variable:

```bash
security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled

SNOWFLAKE_ACCOUNT=<org-account> \
SNOWFLAKE_USER=<user_with_trustops_reader_role> \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=<EVIDENCE_DATABASE> \
SNOWFLAKE_SCHEMA=<EVIDENCE_SCHEMA> \
SNOWFLAKE_OAUTH_TOKEN="$SNOWFLAKE_OAUTH_TOKEN" \
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
