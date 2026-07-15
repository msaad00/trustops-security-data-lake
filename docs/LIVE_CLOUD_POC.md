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
3. service-user key-pair auth or OAuth exposed only as an environment variable
   or mounted secret for the local process

TrustOps should store configuration metadata and fingerprints, not raw cloud
secrets. Use fixtures until a live probe proves access.

## AWS Trial Account

The current AWS runner uses the standard `boto3` credential chain and only calls:

- `iam:ListUsers`
- `iam:ListMFADevices`
- `iam:ListAccessKeys`
- `iam:GetLoginProfile`
- `iam:GetAccountPasswordPolicy`
- `iam:GetAccountSummary`

Use an SSO profile or assumed read-only role. Do not create root credentials.

To create the exact read-only role TrustOps needs, deploy the CloudFormation
template in the target AWS account:

```bash
aws cloudformation deploy \
  --stack-name trustops-posture-readonly \
  --template-file deploy/aws/trustops-posture-readonly-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    TrustedPrincipalArn=arn:aws:iam::<trustops-runtime-account-id>:role/<trustops-runtime-role> \
    ExternalId=<customer-generated-external-id>
```

### AWS STS lifecycle

| Phase        | Boundary                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| Authorize    | The CloudFormation template creates the customer-owned role and trust policy with TrustOps principal + External ID. |
| Authenticate | At probe, manual sync, or scheduled sync, TrustOps calls STS AssumeRole with the Role ARN and External ID.          |
| Read         | AWS returns short-lived session credentials. TrustOps uses them only for read-only IAM posture APIs.                |
| Expire       | The temporary credentials expire after the AWS session window. The next run repeats STS AssumeRole.                 |
| Persist      | TrustOps stores connector metadata, fingerprints, and run results, not long-lived AWS access keys.                  |

The role grants only IAM read actions needed to classify users, console access,
MFA enrollment, access-key hygiene, password policy, and account summary. Use
SSO, an assumed role, or workload identity to run the connector; do not generate
long-lived access keys.

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

To provision a service principal or managed identity with the expected built-in
read roles:

```bash
az deployment sub create \
  --location eastus \
  --template-file deploy/azure/trustops-posture-reader.bicep \
  --parameters principalId=<service-principal-or-managed-identity-object-id> \
               principalType=ServicePrincipal
```

The module assigns `Reader` for resource and policy inventory. If the tenant
blocks role-assignment reads for that identity, grant a customer-owned read role
that includes `Microsoft.Authorization/roleAssignments/read`. TrustOps then
uses `DefaultAzureCredential` from Cloud Shell, managed identity, or service
principal environment variables.

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

If any validation query returns `Object does not exist, or operation cannot be
performed`, the bootstrap SQL did not run under a create-capable role, the
active user was not granted `TRUSTOPS_READER`, or one of the view grants is
missing. Rerun the bootstrap from `ACCOUNTADMIN` or an existing governed GRC
admin role that can create the database, warehouse, role, secure views, and
grants.

For a human POC, use browser SSO. No Snowflake credential needs to be pasted
into chat, Git, or TrustOps config. Do not use this path for scheduled
ingestion:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"'"$SNOWFLAKE_USER"'","credential_ref":"externalbrowser"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'
```

The probe performs lightweight `SELECT COUNT(*)` checks against every configured
view and returns sanitized per-view diagnostics. Do not enable the connector
until the probe result is `ok`.

```bash
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

For headless automation, create a non-human service user and use Snowflake
key-pair auth. The service user should have only `TRUSTOPS_READER` and
`USAGE` on `TRUSTOPS_READ_WH`.

Run [`deploy/snowflake/bootstrap_service_user.sql`](../deploy/snowflake/bootstrap_service_user.sql)
after setting `TRUSTOPS_SERVICE_RSA_PUBLIC_KEY` in the Snowflake worksheet. The
matching private key stays in your secret manager or mounted runtime secret,
not in Snowflake, Git, chat, screenshots, or TrustOps connector config.

Probe and enable the connector with a key-file reference:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"TRUSTOPS_INGEST_SVC","private_key_ref":"SNOWFLAKE_PRIVATE_KEY_FILE"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","role":"TRUSTOPS_READER","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"TRUSTOPS_INGEST_SVC","private_key_ref":"SNOWFLAKE_PRIVATE_KEY_FILE"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","role":"TRUSTOPS_READER","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}' \
  --sync-schedule "every 15m"

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

OAuth is also supported when the customer already has a governed token broker.
The token must be injected by the runtime secret manager:

```bash
security-lakehouse connectors probe \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"TRUSTOPS_INGEST_SVC","credential_ref":"SNOWFLAKE_OAUTH_TOKEN"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

security-lakehouse connectors configure \
  --lake build/lakehouse \
  --connector-id snowflake-evidence-lake \
  --state enabled \
  --credentials-json '{"account":"'"$SNOWFLAKE_ACCOUNT"'","user":"TRUSTOPS_INGEST_SVC","credential_ref":"SNOWFLAKE_OAUTH_TOKEN"}' \
  --options-json '{"warehouse":"TRUSTOPS_READ_WH","database":"TRUSTOPS_SECURITY_LAKE","schema":"EVIDENCE","audit_events":"TRUSTOPS_AUDIT_EVENTS","control_posture":"TRUSTOPS_CONTROL_POSTURE","asset_risk":"TRUSTOPS_ASSET_RISK","evidence_bundles":"TRUSTOPS_EVIDENCE_BUNDLES"}'

SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER=TRUSTOPS_INGEST_SVC \
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
