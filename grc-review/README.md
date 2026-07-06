# GRC Review — Harvey interview demo artifacts

Standalone Snowflake + dbt + Entra ingest pipeline for **post-termination access revocation SLA**.
TrustOps remains the GRC UI/demo shell; this repo holds the data-plane scripts and models.

## Problem

Terminated employees (Workday) who still have active Entra / AWS IAM access after SLA.

## Medallion layers (bronze → silver → gold)

| Layer | Table | Pattern | UI reads? |
|-------|-------|---------|-----------|
| **Bronze** | `RAW_ENTRA_USERS` | Append every pull (`user_id` + `ingest_batch_id`) | No |
| **Silver** | `ENTRA_USERS_LATEST` | **1 row per `user_id`** (current state) | Sometimes |
| **Gold** | `EVAL_CURRENT` | Open violations (`violation_key` MERGE) | **Yes — live dashboard** |
| **Gold** | `EVAL_SNAPSHOT` | Daily auditor artifact (append by `snapshot_date`) | Audit / export |
| **Gold** | `EVAL_DAILY_SUMMARY` | Daily `open_count` (even when 0) | Monitoring |

**You do have silver.** `ENTRA_USERS_LATEST` *is* silver — the diagram label was shortened.
The UI reads **gold** (`EVAL_CURRENT`), not RAW.

## “Incremental” — three different meanings

| Term | Where | Meaning |
|------|-------|---------|
| **Append ingest** | RAW (bronze) | Each pull **adds rows**; same `user_id` appears many times with different `ingest_batch_id` |
| **dbt incremental merge** | Silver build | dbt only **scans new** `ingest_batch_id` partitions (cheap), then **upserts** LATEST |
| **Graph delta** | API | Only **changed** users from `/users/delta` (fewer files) |

**Silver/LATEST is NOT incremental storage** — it is **current state** (Type-1).
“In incremental merge” describes **how dbt runs**, not what the table stores.

## Same 10 violations for days

- `EVAL_CURRENT`: MERGE on `violation_key` — update `last_seen_at`, no duplicate open rows
- `EVAL_SNAPSHOT`: daily insert with `snapshot_date` (auditor point-in-time)
- `EVAL_DAILY_SUMMARY`: log `open_count = 0` so monitors know pipeline is healthy

## Quick start

```bash
# 1. Configure
cp ingest/config.example.env ingest/config.env   # fill Azure + Snowflake

# 2. Pull Entra (delta) → Azure Blob
python ingest/entra_graph_pull.py

# 3. Snowflake (once): run snowflake/*.sql as ACCOUNTADMIN / platform role

# 4. Transform
cd dbt && dbt run && dbt run --select tag:snapshot
```

## TrustOps pairing

| This repo | TrustOps |
|-----------|----------|
| Snowflake gold tables / views | `snowflake-evidence-lake` connector reads views |
| Entra + IAM pipeline | `azure-posture` for subscription RBAC (complementary) |
| Violations | Control tests + audit room |

## Layout

```
grc-review/
  docs/           architecture + interview talking points
  ingest/         Entra Graph → Azure Blob
  snowflake/      stage, pipe, tables
  dbt/            bronze → silver → gold models
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the interview slide diagram.
