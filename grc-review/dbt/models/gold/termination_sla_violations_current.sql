{{
  config(
    materialized='table',
    tags=['gold'],
  )
}}

-- Gold: current SLA violations (terminated + still active past SLA).
-- Rebuilt each run; small table. Use snowflake/03_eval_violations_merge.sql
-- for production MERGE semantics (first_detected_at, resolved_at).

{% set sla = var('sla_hours', 24) %}

SELECT
  SHA2(CONCAT_WS('|', w.employee_id, 'entra', e.user_id)) AS violation_key,
  w.employee_id,
  COALESCE(w.email, e.mail, e.user_principal_name) AS email,
  'entra' AS platform,
  e.user_id AS principal_id,
  w.termination_date,
  DATEDIFF('hour', w.termination_ts, CURRENT_TIMESTAMP()) AS hours_since_term,
  {{ sla }} AS sla_hours,
  'open' AS status,
  CURRENT_TIMESTAMP() AS first_detected_at,
  CURRENT_TIMESTAMP() AS last_seen_at,
  CAST(NULL AS TIMESTAMP_NTZ) AS resolved_at,
  OBJECT_CONSTRUCT(
    'upn', e.user_principal_name,
    'account_enabled', e.account_enabled
  ) AS details
FROM {{ ref('workday_terminations_latest') }} w
INNER JOIN {{ ref('entra_users_latest') }} e
  ON LOWER(TRIM(w.email)) = LOWER(TRIM(COALESCE(e.mail, e.user_principal_name)))
WHERE w.status = 'terminated'
  AND e.account_enabled = TRUE
  AND e.is_deleted = FALSE
  AND DATEDIFF('hour', w.termination_ts, CURRENT_TIMESTAMP()) > {{ sla }}
