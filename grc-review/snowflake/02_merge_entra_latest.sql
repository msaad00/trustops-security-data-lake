-- MERGE silver LATEST from bronze RAW (run via dbt model or Snowflake task).
-- This is the SQL dbt incremental merge implements.

MERGE INTO GRC_REVIEW.SILVER.ENTRA_USERS_LATEST AS t
USING (
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
  FROM GRC_REVIEW.BRONZE.RAW_ENTRA_USERS
  WHERE ingest_batch_id = :ingest_batch_id  -- dbt replaces with max-new-batch filter
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY user_id ORDER BY ingest_time DESC
  ) = 1
) AS s
ON t.user_id = s.user_id
WHEN MATCHED THEN UPDATE SET
  user_principal_name = s.user_principal_name,
  mail = s.mail,
  account_enabled = s.account_enabled,
  employee_id = s.employee_id,
  display_name = s.display_name,
  ingest_batch_id = s.ingest_batch_id,
  ingest_time = s.ingest_time,
  is_deleted = s.is_deleted,
  content_hash = s.content_hash,
  updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
  user_id, user_principal_name, mail, account_enabled, employee_id,
  display_name, ingest_batch_id, ingest_time, is_deleted, content_hash, updated_at
) VALUES (
  s.user_id, s.user_principal_name, s.mail, s.account_enabled, s.employee_id,
  s.display_name, s.ingest_batch_id, s.ingest_time, s.is_deleted, s.content_hash,
  CURRENT_TIMESTAMP()
);
