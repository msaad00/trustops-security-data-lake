# Harvey Trust Engineer onsite — talking points

## 20-minute demo arc

1. **Problem** (2 min): Post-termination access revocation within 24h SLA — SOC 2 CC6, ISO A.5.11
2. **Data plane** (5 min): Show diagram — Graph delta → Blob → Snowpipe → bronze → silver → gold
3. **TrustOps** (8 min): Dashboard, failing control, connector sync, audit snapshot
4. **Ops** (3 min): `EVAL_DAILY_SUMMARY` with `open_count=0` = healthy; stale watermark = alert
5. **Next week** (2 min): AWS IAM same pattern, native HRIS connector, auto-remediation tickets

## If they ask: bronze to gold with no silver?

**No.** Silver is `ENTRA_USERS_LATEST` — one row per user. UI reads **gold** (`EVAL_CURRENT` / view).
Eval joins small silver tables; it does not scan raw history.

## If they ask: why "incremental merge" on silver?

Clarify three words:

| Word | Meaning |
|------|---------|
| **Append** (bronze) | New rows per pull; same user_id repeats |
| **Incremental** (dbt run) | Only process new `ingest_batch_id` batches |
| **Merge** (silver result) | Upsert to 1 row per `user_id` |

Silver is **not** incremental storage — it's **current state**.

## If they ask: same 10 violations all week?

`EVAL_CURRENT` MERGE updates `last_seen_at`. Snapshot gets 10 rows/day with different `snapshot_date`.
Not a bug — auditors ask "how many on Tuesday?" not "how many unique rows ever?".

## If they ask: why poll if nothing changed?

Entra delta returns empty → skip blob → skip pipe. LATEST unchanged. Eval still cheap on silver.
You cannot prove "still compliant" without checking.

## Scripting interview

Practice `ingest/entra_graph_pull.py` patterns: pagination, 429, watermark file, idempotent batch paths.

**No LLM in that room** — this script is the template.

## Cross-functional

Engineering wants to skip access review → offer phased: detect + alert first, automate revoke with change ticket.

## Scoped out (say proudly)

- Full Snowpipe infra in 3 hours
- Live Harvey tenant wiring
- TrustOps native Graph connector (use grc-review ingest + Snowflake views)
