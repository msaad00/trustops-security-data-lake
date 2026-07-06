# Daily eval + revocation audit — operating model

How to handle: **0 rows, same rows, new rows, mixed remediation**, file dedupe,
and **who revoked what when** (cloud audit logs).

## Four table families (do not mix them)

| Family | Example tables | Pattern | Answers |
|--------|----------------|---------|---------|
| **Bronze** | `RAW_ENTRA_USERS` | Append per `ingest_batch_id` | "What did API return at 10:00?" |
| **Silver** | `ENTRA_USERS_LATEST`, `WORKDAY_TERMINATIONS_LATEST` | MERGE 1 row/entity | "Current IAM + HR state" |
| **Gold state** | `EVAL_CURRENT` | MERGE on `violation_key` | "Who is failing **right now**?" (UI) |
| **Gold events** | `REVOCATION_AUDIT_LOG`, `VIOLATION_LIFECYCLE_LOG` | Append-only | "Who revoked what, when?" |

The **daily table with HR + cloud + termination** that powers the UI is **`EVAL_CURRENT`**
(not a new append each day). Daily **snapshots** are separate (`EVAL_SNAPSHOT`).

---

## Layer 1 — Files & Snowpipe (avoid duplicate loads)

### Decision tree each ingest run

```text
Graph delta / IAM API pull
        │
        ├─ 0 changes, 0 deletes?
        │     └─► SKIP blob write. Log heartbeat. Stop.
        │
        ├─ Changes but content_hash == previous_batch_hash?
        │     └─► OPTIONAL skip (cost save). Or write anyway for strict audit.
        │
        └─ Else
              └─► Write ONE file:
                    entra/ingest_batch_id=20260706T1000Z/part-000.json
                  Snowpipe → RAW (PK: user_id + ingest_batch_id)
```

| Risk | Fix |
|------|-----|
| Same file loaded twice | `ingest_batch_id` unique in path; RAW PK `(entity_id, ingest_batch_id)`; Snowpipe `overwrite=false` |
| Re-run same batch id | Never reuse batch id — always UTC timestamp |
| Snowpipe reload | `COPY_HISTORY` monitor; dedupe RAW on PK |
| Empty pull | **No file** = no pipe work |

Store batch metadata:

```sql
-- INGEST_BATCH_REGISTRY (append one row per real file written)
ingest_batch_id, source, record_count, content_hash, blob_path, written_at
```

---

## Layer 2 — Daily eval table (`EVAL_CURRENT`) — all scenarios

Your eval runs daily (or every 6h). Each run **MERGEs** into `EVAL_CURRENT`.

### Scenario matrix

| Today vs yesterday | `EVAL_CURRENT` action | Row count (open) |
|--------------------|----------------------|------------------|
| Same 10 violations | UPDATE `last_seen_at` only | 10 |
| 10 → 12 (2 new) | INSERT 2 new `violation_key` | 12 |
| 12 → 8 (4 revoked) | UPDATE 4 to `status=resolved` | 8 |
| 8 → 0 (all fixed) | UPDATE all to `resolved` | **0 open** |
| 0 → 0 | No open rows change; update summary | 0 |

**No duplicate open rows** — key is `violation_key = hash(employee_id, platform, principal_id)`.

### What the UI shows

```sql
SELECT * FROM GOLD.V_TERMINATION_SLA_VIOLATIONS
WHERE status = 'open';
-- 0 rows = green. 10 rows = action needed.
```

### Daily snapshot (audit, not live state)

```sql
-- Runs once per day after MERGE
INSERT INTO EVAL_SNAPSHOT (snapshot_date, ...)
SELECT CURRENT_DATE(), ... FROM EVAL_CURRENT WHERE status = 'open';
```

Same 10 people Mon–Fri → **10 snapshot rows per day** (different `snapshot_date`). That is correct for auditors.

### Daily summary (always run, even 0)

```sql
INSERT INTO EVAL_DAILY_SUMMARY (snapshot_date, open_violation_count, ...)
VALUES (CURRENT_DATE(), 0, ...);  -- proves pipeline ran
```

---

## Layer 3 — Revocation audit logs (who / what / when)

**Do not put audit narrative only in `EVAL_CURRENT`.** When access is revoked, cloud platforms emit **events**.

### Two sources of "revocation proof"

| Source | Table | Example |
|--------|-------|---------|
| **Cloud native audit** | `RAW_ENTRA_AUDIT_LOG` (bronze, append) | Entra: `Disable account`, `Remove member from group` |
| **Pipeline detected** | `VIOLATION_LIFECYCLE_LOG` (gold, append) | Eval saw `open` → `resolved` at 2026-07-06 14:00 |

### `REVOCATION_AUDIT_LOG` (append-only, gold)

One row per revocation **event** (never update):

| Column | Example |
|--------|---------|
| `event_id` | CloudTrail `eventID` or Graph audit `id` |
| `event_time` | When revocation happened in source |
| `detected_at` | When we ingested / detected |
| `employee_id` | E001 |
| `principal_id` | entra user guid |
| `platform` | entra \| aws |
| `action` | `DISABLE_ACCOUNT`, `REMOVE_ROLE_ASSIGNMENT` |
| `actor` | admin@company.com |
| `violation_key` | link to violation episode |
| `source` | `entra_audit` \| `eval_detection` |

### How rows get there

```text
Path A — Cloud audit (preferred for auditors)
  Entra Audit Logs / AWS CloudTrail
    → append RAW audit events (event_id PK)
    → silver: parse revocation actions
    → INSERT REVOCATION_AUDIT_LOG

Path B — Eval detection (backstop)
  Daily MERGE sees violation_key: open → resolved
    → INSERT VIOLATION_LIFECYCLE_LOG (detected_resolved)
    → INSERT REVOCATION_AUDIT_LOG (source='eval_detection')
      until cloud audit event arrives to enrich row
```

Auditors want **Path A**. Path B proves your control **detected** remediation even if audit ingest lags.

---

## End-to-end daily job order

```text
06:00  Ingest HR (Workday view → WORKDAY_TERMINATIONS_LATEST merge)
06:15  Ingest Entra delta → blob → Snowpipe → RAW → dbt → LATEST
06:30  Ingest Entra audit logs (append) / CloudTrail
07:00  MERGE EVAL_CURRENT (violations)
07:05  INSERT VIOLATION_LIFECYCLE_LOG (state transitions)
07:10  INSERT EVAL_SNAPSHOT + EVAL_DAILY_SUMMARY
```

---

## Example week

| Day | Open violations | Revocation audit log | Notes |
|-----|-----------------|----------------------|-------|
| Mon | 10 | 0 new revocations | Same 10, `last_seen_at` updates |
| Tue | 10 | 2 events (admin disabled 2 accounts) | Audit log has actor + timestamp |
| Wed | 8 | 2 more revocations | EVAL_CURRENT: 2 resolved |
| Thu | 3 | 5 revocations | Mixed old + new remediations |
| Fri | 0 | 3 revocations | All clear; summary `open_count=0` |

**EVAL_CURRENT**: live scoreboard.  
**EVAL_SNAPSHOT**: daily score history.  
**REVOCATION_AUDIT_LOG**: evidence of **actions taken** (who fixed it).

---

## Interview one-liner

> "Ingest is append with batch ids and skip-empty-files. Violations are MERGE state —
> same rows don't duplicate, zero rows means pass. Revocations are a separate append-only
> audit log from Entra/CloudTrail plus lifecycle events when eval detects resolution."

See `snowflake/04_revocation_audit_log.sql` for DDL.
