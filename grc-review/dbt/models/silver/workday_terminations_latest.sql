{{
  config(
    unique_key='employee_id',
    incremental_strategy='merge',
    tags=['silver'],
  )
}}

SELECT
  employee_id,
  email,
  termination_date,
  termination_ts,
  status
FROM {{ ref('seed_workday_terminations') }}
