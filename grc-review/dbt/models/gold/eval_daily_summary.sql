{{
  config(
    materialized='incremental',
    unique_key='snapshot_date',
    incremental_strategy='merge',
    tags=['snapshot'],
  )
}}

-- Always log open_count including 0 — proves pipeline ran.

SELECT
  CURRENT_DATE() AS snapshot_date,
  CURRENT_TIMESTAMP() AS snapshot_ts,
  COUNT(*) AS open_violation_count,
  0 AS resolved_today_count,
  MD5(LISTAGG(violation_key, ',') WITHIN GROUP (ORDER BY violation_key)) AS violation_fingerprint,
  TRUE AS pipeline_ok
FROM {{ ref('termination_sla_violations_current') }}
