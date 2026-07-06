{{
  config(
    unique_key='user_id',
    incremental_strategy='merge',
    tags=['silver'],
  )
}}

-- Silver: 1 row per Entra user (current state).
-- "Incremental" = dbt only READS new ingest_batch_id partitions from bronze.
-- The TABLE stores latest state, not history.

WITH batch_rows AS (
  SELECT
    user_id,
    user_principal_name,
    mail,
    account_enabled,
    employee_id,
    display_name,
    ingest_batch_id,
    ingest_time,
    source_operation = 'delete' AS is_deleted,
    SHA2(CONCAT_WS('|',
      COALESCE(user_id, ''),
      COALESCE(TO_VARCHAR(account_enabled), ''),
      COALESCE(employee_id, ''),
      COALESCE(source_operation, '')
    )) AS content_hash
  FROM {{ ref('stg_raw_entra_users') }}
  {% if is_incremental() %}
    WHERE ingest_batch_id > (SELECT COALESCE(MAX(ingest_batch_id), '') FROM {{ this }})
  {% endif %}
  QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ingest_time DESC) = 1
)

SELECT
  user_id,
  user_principal_name,
  mail,
  account_enabled,
  employee_id,
  display_name,
  ingest_batch_id,
  ingest_time,
  is_deleted,
  content_hash,
  CURRENT_TIMESTAMP() AS updated_at
FROM batch_rows
