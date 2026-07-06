-- Bronze staging view on RAW (optional clarity layer)
SELECT
  user_id,
  user_principal_name,
  mail,
  account_enabled,
  employee_id,
  display_name,
  ingest_batch_id,
  ingest_time,
  COALESCE(source_operation, 'upsert') AS source_operation,
  raw_payload
FROM {{ source('bronze', 'raw_entra_users') }}
