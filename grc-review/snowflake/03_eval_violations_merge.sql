-- Violation MERGE: same 10 rows for days → update last_seen_at only.
-- Resolved when access revoked → status = resolved, not deleted.

MERGE INTO GRC_REVIEW.GOLD.EVAL_CURRENT AS t
USING (
  SELECT
    SHA2(CONCAT_WS('|', w.employee_id, 'entra', e.user_id)) AS violation_key,
    w.employee_id,
    COALESCE(w.email, e.mail, e.user_principal_name) AS email,
    'entra' AS platform,
    e.user_id AS principal_id,
    w.termination_date,
    DATEDIFF('hour', w.termination_ts, CURRENT_TIMESTAMP()) AS hours_since_term,
    24 AS sla_hours,
    e.account_enabled = TRUE
      AND e.is_deleted = FALSE
      AND w.termination_date IS NOT NULL
      AND DATEDIFF('hour', w.termination_ts, CURRENT_TIMESTAMP()) > 24 AS is_violation,
    OBJECT_CONSTRUCT(
      'upn', e.user_principal_name,
      'account_enabled', e.account_enabled
    ) AS details
  FROM GRC_REVIEW.SILVER.WORKDAY_TERMINATIONS_LATEST w
  INNER JOIN GRC_REVIEW.SILVER.ENTRA_USERS_LATEST e
    ON LOWER(TRIM(w.email)) = LOWER(TRIM(COALESCE(e.mail, e.user_principal_name)))
  WHERE w.status = 'terminated'
) AS s
ON t.violation_key = s.violation_key
WHEN MATCHED AND s.is_violation THEN UPDATE SET
  hours_since_term = s.hours_since_term,
  last_seen_at = CURRENT_TIMESTAMP(),
  status = 'open',
  resolved_at = NULL,
  details = s.details
WHEN MATCHED AND NOT s.is_violation THEN UPDATE SET
  status = 'resolved',
  resolved_at = COALESCE(t.resolved_at, CURRENT_TIMESTAMP()),
  last_seen_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND s.is_violation THEN INSERT (
  violation_key, employee_id, email, platform, principal_id,
  termination_date, hours_since_term, sla_hours, status,
  first_detected_at, last_seen_at, details
) VALUES (
  s.violation_key, s.employee_id, s.email, s.platform, s.principal_id,
  s.termination_date, s.hours_since_term, s.sla_hours, 'open',
  CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), s.details
);

-- Close violations no longer in the current failing set
UPDATE GRC_REVIEW.GOLD.EVAL_CURRENT t
SET status = 'resolved',
    resolved_at = COALESCE(resolved_at, CURRENT_TIMESTAMP()),
    last_seen_at = CURRENT_TIMESTAMP()
WHERE t.status = 'open'
  AND t.platform = 'entra'
  AND NOT EXISTS (
    SELECT 1
    FROM GRC_REVIEW.SILVER.WORKDAY_TERMINATIONS_LATEST w
    INNER JOIN GRC_REVIEW.SILVER.ENTRA_USERS_LATEST e
      ON LOWER(TRIM(w.email)) = LOWER(TRIM(COALESCE(e.mail, e.user_principal_name)))
    WHERE w.status = 'terminated'
      AND e.account_enabled = TRUE
      AND e.is_deleted = FALSE
      AND SHA2(CONCAT_WS('|', w.employee_id, 'entra', e.user_id)) = t.violation_key
      AND DATEDIFF('hour', w.termination_ts, CURRENT_TIMESTAMP()) > 24
  );

-- Daily snapshot (append open violations for today)
INSERT INTO GRC_REVIEW.GOLD.EVAL_SNAPSHOT (
  snapshot_date, snapshot_ts, violation_key, employee_id, email,
  platform, principal_id, termination_date, hours_since_term, sla_hours, details
)
SELECT
  CURRENT_DATE(),
  CURRENT_TIMESTAMP(),
  violation_key, employee_id, email, platform, principal_id,
  termination_date, hours_since_term, sla_hours, details
FROM GRC_REVIEW.GOLD.EVAL_CURRENT
WHERE status = 'open';

-- Daily summary (always — even 0)
MERGE INTO GRC_REVIEW.GOLD.EVAL_DAILY_SUMMARY t
USING (
  SELECT
    CURRENT_DATE() AS snapshot_date,
    CURRENT_TIMESTAMP() AS snapshot_ts,
    COUNT(*) AS open_violation_count,
    MD5(LISTAGG(violation_key, ',') WITHIN GROUP (ORDER BY violation_key)) AS violation_fingerprint
  FROM GRC_REVIEW.GOLD.EVAL_CURRENT
  WHERE status = 'open'
) s
ON t.snapshot_date = s.snapshot_date
WHEN MATCHED THEN UPDATE SET
  snapshot_ts = s.snapshot_ts,
  open_violation_count = s.open_violation_count,
  violation_fingerprint = s.violation_fingerprint,
  pipeline_ok = TRUE
WHEN NOT MATCHED THEN INSERT (
  snapshot_date, snapshot_ts, open_violation_count, violation_fingerprint, pipeline_ok
) VALUES (
  s.snapshot_date, s.snapshot_ts, s.open_violation_count, s.violation_fingerprint, TRUE
);
