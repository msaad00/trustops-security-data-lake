-- Append-only revocation and violation lifecycle evidence.
-- Cloud audit events (Path A) + eval detection (Path B).

CREATE TABLE IF NOT EXISTS GRC_REVIEW.GOLD.REVOCATION_AUDIT_LOG (
  event_id              VARCHAR NOT NULL PRIMARY KEY,
  event_time            TIMESTAMP_NTZ NOT NULL,
  detected_at           TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  employee_id           VARCHAR,
  email                 VARCHAR,
  platform              VARCHAR NOT NULL,
  principal_id          VARCHAR,
  violation_key         VARCHAR,
  action                VARCHAR NOT NULL,
  actor                 VARCHAR,
  source                VARCHAR NOT NULL,  -- entra_audit | aws_cloudtrail | eval_detection
  raw_payload           VARIANT,
  ingest_batch_id       VARCHAR
)
COMMENT = 'Append-only: who revoked what, when — auditor evidence';

CREATE TABLE IF NOT EXISTS GRC_REVIEW.GOLD.VIOLATION_LIFECYCLE_LOG (
  lifecycle_id          VARCHAR NOT NULL PRIMARY KEY,
  violation_key         VARCHAR NOT NULL,
  event_type            VARCHAR NOT NULL,  -- detected_open | detected_resolved | sla_breached
  event_time            TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  employee_id           VARCHAR,
  platform              VARCHAR,
  principal_id          VARCHAR,
  open_violation_count  NUMBER,
  details               VARIANT
)
COMMENT = 'Append-only: violation state transitions from eval MERGE';

CREATE TABLE IF NOT EXISTS GRC_REVIEW.BRONZE.INGEST_BATCH_REGISTRY (
  ingest_batch_id       VARCHAR NOT NULL PRIMARY KEY,
  source_name           VARCHAR NOT NULL,
  record_count          NUMBER,
  content_hash          VARCHAR,
  blob_path             VARCHAR,
  written_at            TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  skipped               BOOLEAN DEFAULT FALSE,
  skip_reason           VARCHAR
)
COMMENT = 'One row per ingest run — dedupe and ops visibility';

-- Example: log eval-detected resolution after MERGE (run from task post-hook)
/*
INSERT INTO GRC_REVIEW.GOLD.VIOLATION_LIFECYCLE_LOG (
  lifecycle_id, violation_key, event_type, employee_id, platform, principal_id, details
)
SELECT
  UUID_STRING(),
  violation_key,
  'detected_resolved',
  employee_id,
  platform,
  principal_id,
  OBJECT_CONSTRUCT('resolved_at', resolved_at)
FROM GRC_REVIEW.GOLD.EVAL_CURRENT
WHERE status = 'resolved'
  AND resolved_at >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
  AND NOT EXISTS (
    SELECT 1 FROM GRC_REVIEW.GOLD.VIOLATION_LIFECYCLE_LOG l
    WHERE l.violation_key = EVAL_CURRENT.violation_key
      AND l.event_type = 'detected_resolved'
      AND l.event_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
  );
*/

GRANT SELECT ON TABLE GRC_REVIEW.GOLD.REVOCATION_AUDIT_LOG TO ROLE GRC_AUDIT_READER;
GRANT SELECT ON TABLE GRC_REVIEW.GOLD.VIOLATION_LIFECYCLE_LOG TO ROLE GRC_AUDIT_READER;
