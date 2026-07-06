{{
  config(
    materialized='incremental',
    unique_key=['snapshot_date', 'violation_key'],
    incremental_strategy='merge',
    tags=['snapshot'],
  )
}}

-- Daily auditor artifact: open violations as of this run.
-- Same 10 people Mon–Fri → 10 rows per snapshot_date (intentional for audit).

SELECT
  CURRENT_DATE() AS snapshot_date,
  CURRENT_TIMESTAMP() AS snapshot_ts,
  violation_key,
  employee_id,
  email,
  platform,
  principal_id,
  termination_date,
  hours_since_term,
  sla_hours,
  details
FROM {{ ref('termination_sla_violations_current') }}

{% if is_incremental() %}
  WHERE snapshot_date > (SELECT COALESCE(MAX(snapshot_date), '1900-01-01') FROM {{ this }})
     OR CURRENT_DATE() > (SELECT COALESCE(MAX(snapshot_date), '1900-01-01') FROM {{ this }})
{% endif %}
