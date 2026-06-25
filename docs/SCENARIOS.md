# TrustOps Scenarios

Scenarios are repeatable product proofs. They run shipped TrustOps primitives in
one flow and write a machine-readable report that can be attached to a PR,
demo, audit packet, or buyer proof.

## Live Cloud Posture

`live-cloud-posture` proves the core trust loop across cloud evidence:

```text
connectors -> raw evidence -> bronze/silver/gold -> integrity -> snapshot -> workflow
```

It enables selected connectors, syncs evidence, rebuilds the lake, verifies
evidence integrity and idempotency hashes, freezes a point-in-time snapshot,
runs a workflow DAG, and writes:

```text
<lake>/gold/scenario_reports/live-cloud-posture.json
```

### Fixture Proof

Use this in CI or local demos without cloud credentials:

```bash
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/live-cloud-posture \
  --connector azure-posture \
  --connector aws-posture \
  --connector snowflake-evidence-lake \
  --fixture azure-posture=tests/fixtures/azure \
  --fixture aws-posture=tests/fixtures/aws \
  --fixture snowflake-evidence-lake=tests/fixtures/snowflake \
  --summary
```

Expected proof points:

- sync result per connector
- evidence-by-source counts
- silver evidence count and source mix
- evidence integrity `ok: true`
- snapshot-chain verification `ok: true`
- workflow run `ok`
- artifact paths for raw, bronze, silver, current posture, integrity, and report

### Azure Live Proof

Azure uses `DefaultAzureCredential`, so local `az login`, Cloud Shell, managed
identity, or service-principal environment variables can authenticate without
TrustOps storing credentials.

```bash
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/azure-live \
  --connector azure-posture \
  --summary
```

Set `AZURE_SUBSCRIPTION_ID` for the target subscription. The connector reads
role assignments, resources, and policy assignments when the installed Azure SDK
exposes the policy client. If that policy client is unavailable, RBAC and
resources still ingest and the report remains explicit about the evidence
present.

### AWS Live Proof

AWS uses the standard `boto3` credential chain. Prefer CloudShell, SSO, an
assumed role, or workload identity. Do not create root access keys.

```bash
AWS_ACCOUNT_ID=030225640638 \
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/aws-live \
  --connector aws-posture \
  --summary
```

The current AWS connector reads IAM users, MFA devices, the account summary, and
the account password policy when authorized.

### Snowflake Live Proof

Create the fixed Snowflake POC views from
[`docs/LIVE_CLOUD_POC.md`](LIVE_CLOUD_POC.md). Browser SSO is acceptable for a
human proof only:

```bash
SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER="$SNOWFLAKE_USER" \
SNOWFLAKE_AUTHENTICATOR=externalbrowser \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/snowflake-live \
  --connector snowflake-evidence-lake \
  --summary
```

Continuous jobs should use a non-human Snowflake service user with key-pair
auth. The private key is mounted by the runtime secret manager and only the file
path is passed to TrustOps:

```bash
SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER=TRUSTOPS_INGEST_SVC \
SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT \
SNOWFLAKE_PRIVATE_KEY_FILE="$SNOWFLAKE_PRIVATE_KEY_FILE" \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/snowflake-live \
  --connector snowflake-evidence-lake \
  --summary
```

OAuth is also supported when the customer already has a governed token broker:
set `SNOWFLAKE_AUTHENTICATOR=oauth` with `SNOWFLAKE_OAUTH_TOKEN` injected by the
runtime secret manager. Raw credentials are not persisted in the lake.

### Full Live Proof

After Azure, AWS, and Snowflake are configured, run all three into one lake:

```bash
AZURE_SUBSCRIPTION_ID=8e134453-ac1f-46fb-8047-0af5d5e86427 \
AWS_ACCOUNT_ID=030225640638 \
SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER=TRUSTOPS_INGEST_SVC \
SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT \
SNOWFLAKE_PRIVATE_KEY_FILE="$SNOWFLAKE_PRIVATE_KEY_FILE" \
SNOWFLAKE_ROLE=TRUSTOPS_READER \
SNOWFLAKE_WAREHOUSE=TRUSTOPS_READ_WH \
SNOWFLAKE_DATABASE=TRUSTOPS_SECURITY_LAKE \
SNOWFLAKE_SCHEMA=EVIDENCE \
security-lakehouse scenario run live-cloud-posture \
  --lake build/scenarios/live-cloud-posture \
  --summary
```

`--summary` prints the operator view: connector status, evidence counts by
source, posture score/state, integrity status, snapshot-chain verification,
workflow result, and the durable report path. Omit it when an automation or PR
attachment needs the full JSON report.

This is the default scenario for proving that TrustOps can operate as a
self-hosted, deterministic trust center: evidence comes from real systems, the
core evaluation path stays model-independent, and the workflow layer is a
guarded action path rather than the compliance engine.
