-- GRC Review: storage integration, external stage, Snowpipe, and core tables.
-- Run as ACCOUNTADMIN or platform role with CREATE INTEGRATION privileges.
-- Replace placeholders before execution.

USE ROLE ACCOUNTADMIN;

-- ─── Database / schema ───────────────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS GRC_REVIEW
  COMMENT = 'Harvey interview demo — termination SLA pipeline';

CREATE SCHEMA IF NOT EXISTS GRC_REVIEW.BRONZE
  COMMENT = 'Append-only ingest (Snowpipe landing)';

CREATE SCHEMA IF NOT EXISTS GRC_REVIEW.SILVER
  COMMENT = 'Current-state entities (1 row per user/principal)';

CREATE SCHEMA IF NOT EXISTS GRC_REVIEW.GOLD
  COMMENT = 'Violations, snapshots, monitoring';

CREATE WAREHOUSE IF NOT EXISTS GRC_REVIEW_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- ─── Roles (least privilege) ─────────────────────────────────────────────────

CREATE ROLE IF NOT EXISTS GRC_INGEST_SVC;
CREATE ROLE IF NOT EXISTS GRC_DBT_RUNNER;
CREATE ROLE IF NOT EXISTS GRC_AUDIT_READER;

GRANT USAGE ON WAREHOUSE GRC_REVIEW_WH TO ROLE GRC_INGEST_SVC;
GRANT USAGE ON WAREHOUSE GRC_REVIEW_WH TO ROLE GRC_DBT_RUNNER;
GRANT USAGE ON WAREHOUSE GRC_REVIEW_WH TO ROLE GRC_AUDIT_READER;

GRANT USAGE ON DATABASE GRC_REVIEW TO ROLE GRC_INGEST_SVC;
GRANT USAGE ON SCHEMA GRC_REVIEW.BRONZE TO ROLE GRC_INGEST_SVC;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA GRC_REVIEW.BRONZE TO ROLE GRC_INGEST_SVC;
GRANT USAGE ON STAGE GRC_REVIEW.BRONZE.AZURE_GRC_STAGE TO ROLE GRC_INGEST_SVC;

GRANT USAGE ON DATABASE GRC_REVIEW TO ROLE GRC_DBT_RUNNER;
GRANT ALL ON SCHEMA GRC_REVIEW.SILVER TO ROLE GRC_DBT_RUNNER;
GRANT ALL ON SCHEMA GRC_REVIEW.GOLD TO ROLE GRC_DBT_RUNNER;
GRANT SELECT ON ALL TABLES IN SCHEMA GRC_REVIEW.BRONZE TO ROLE GRC_DBT_RUNNER;

GRANT USAGE ON DATABASE GRC_REVIEW TO ROLE GRC_AUDIT_READER;
GRANT SELECT ON ALL TABLES IN SCHEMA GRC_REVIEW.GOLD TO ROLE GRC_AUDIT_READER;

-- ─── Storage integration (Azure Blob) ────────────────────────────────────────
-- Replace tenant, app id, container, and allowed locations.

/*
CREATE OR REPLACE STORAGE INTEGRATION azure_grc_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<tenant-id>'
  AZURE_CONSENT_URL = 'https://login.microsoftonline.com/<tenant-id>/oauth2/authorize'
  STORAGE_ALLOWED_LOCATIONS = ('azure://<account>.blob.core.windows.net/grc-review/')
  COMMENT = 'GRC Review Entra ingest blob';

CREATE OR REPLACE STAGE GRC_REVIEW.BRONZE.AZURE_GRC_STAGE
  STORAGE_INTEGRATION = azure_grc_integration
  URL = 'azure://<account>.blob.core.windows.net/grc-review/entra/'
  FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = TRUE);
*/

-- ─── Bronze: RAW append table ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.BRONZE.RAW_ENTRA_USERS (
  user_id               VARCHAR NOT NULL,
  user_principal_name   VARCHAR,
  mail                  VARCHAR,
  account_enabled       BOOLEAN,
  employee_id           VARCHAR,
  display_name          VARCHAR,
  ingest_batch_id       VARCHAR NOT NULL,
  ingest_time           TIMESTAMP_NTZ NOT NULL,
  source_operation      VARCHAR,  -- upsert | delete
  raw_payload           VARIANT,
  CONSTRAINT pk_raw_entra_users PRIMARY KEY (user_id, ingest_batch_id)
)
COMMENT = 'Bronze: every Graph pull; same user_id across many batches';

-- ─── Silver: current Entra state (dbt-maintained; DDL for reference) ─────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.SILVER.ENTRA_USERS_LATEST (
  user_id               VARCHAR NOT NULL PRIMARY KEY,
  user_principal_name   VARCHAR,
  mail                  VARCHAR,
  account_enabled       BOOLEAN,
  employee_id           VARCHAR,
  display_name          VARCHAR,
  ingest_batch_id       VARCHAR NOT NULL,
  ingest_time           TIMESTAMP_NTZ NOT NULL,
  is_deleted            BOOLEAN DEFAULT FALSE,
  content_hash          VARCHAR,
  updated_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Silver: 1 row per Entra user — current state only';

-- ─── Silver: Workday terminations (seed or sync from HRIS view) ──────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.SILVER.WORKDAY_TERMINATIONS_LATEST (
  employee_id           VARCHAR NOT NULL PRIMARY KEY,
  email                 VARCHAR,
  termination_date      DATE NOT NULL,
  termination_ts        TIMESTAMP_NTZ,
  status                VARCHAR DEFAULT 'terminated',
  updated_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Silver: terminated employees from Workday';

-- ─── Gold: live violations (MERGE target) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.GOLD.EVAL_CURRENT (
  violation_key         VARCHAR NOT NULL PRIMARY KEY,
  employee_id           VARCHAR NOT NULL,
  email                 VARCHAR,
  platform              VARCHAR NOT NULL,  -- entra | aws
  principal_id          VARCHAR NOT NULL,
  termination_date      DATE,
  hours_since_term      NUMBER,
  sla_hours             NUMBER DEFAULT 24,
  status                VARCHAR NOT NULL,  -- open | resolved
  first_detected_at     TIMESTAMP_NTZ NOT NULL,
  last_seen_at          TIMESTAMP_NTZ NOT NULL,
  resolved_at           TIMESTAMP_NTZ,
  details               VARIANT
)
COMMENT = 'Gold: open SLA violations — UI reads this';

-- ─── Gold: daily auditor snapshot ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.GOLD.EVAL_SNAPSHOT (
  snapshot_date         DATE NOT NULL,
  snapshot_ts           TIMESTAMP_NTZ NOT NULL,
  violation_key         VARCHAR NOT NULL,
  employee_id           VARCHAR NOT NULL,
  email                 VARCHAR,
  platform              VARCHAR NOT NULL,
  principal_id          VARCHAR NOT NULL,
  termination_date      DATE,
  hours_since_term      NUMBER,
  sla_hours             NUMBER,
  details               VARIANT,
  CONSTRAINT pk_eval_snapshot PRIMARY KEY (snapshot_date, violation_key)
)
COMMENT = 'Gold: point-in-time open violations per day';

-- ─── Gold: daily metrics (including open_count = 0) ──────────────────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.GOLD.EVAL_DAILY_SUMMARY (
  snapshot_date         DATE NOT NULL PRIMARY KEY,
  snapshot_ts             TIMESTAMP_NTZ NOT NULL,
  open_violation_count    NUMBER NOT NULL,
  resolved_today_count    NUMBER DEFAULT 0,
  violation_fingerprint   VARCHAR,
  pipeline_ok             BOOLEAN DEFAULT TRUE
)
COMMENT = 'Gold: monitoring — proves eval ran even when count is 0';

-- ─── Watermark for Graph deltaLink ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS GRC_REVIEW.BRONZE.INGEST_WATERMARKS (
  source_name           VARCHAR NOT NULL PRIMARY KEY,
  cursor_value          VARCHAR,
  updated_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO GRC_REVIEW.BRONZE.INGEST_WATERMARKS (source_name, cursor_value)
SELECT 'entra_users_delta', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM GRC_REVIEW.BRONZE.INGEST_WATERMARKS WHERE source_name = 'entra_users_delta'
);

-- ─── Snowpipe (uncomment after stage exists) ─────────────────────────────────

/*
CREATE OR REPLACE PIPE GRC_REVIEW.BRONZE.ENTRA_USERS_PIPE
  AUTO_INGEST = TRUE
  AS
  COPY INTO GRC_REVIEW.BRONZE.RAW_ENTRA_USERS (
    user_id, user_principal_name, mail, account_enabled, employee_id,
    display_name, ingest_batch_id, ingest_time, source_operation, raw_payload
  )
  FROM (
    SELECT
      $1:id::VARCHAR,
      $1:userPrincipalName::VARCHAR,
      $1:mail::VARCHAR,
      $1:accountEnabled::BOOLEAN,
      $1:employeeId::VARCHAR,
      $1:displayName::VARCHAR,
      REGEXP_SUBSTR(METADATA$FILENAME, 'ingest_batch_id=([^/]+)', 1, 1, 'e', 1),
      $1:ingest_time::TIMESTAMP_NTZ,
      $1:source_operation::VARCHAR,
      $1
    FROM @GRC_REVIEW.BRONZE.AZURE_GRC_STAGE
  )
  FILE_FORMAT = (TYPE = JSON)
  ON_ERROR = 'CONTINUE';
*/

-- ─── UI view for TrustOps / dashboard ────────────────────────────────────────

CREATE OR REPLACE VIEW GRC_REVIEW.GOLD.V_TERMINATION_SLA_VIOLATIONS AS
SELECT
  violation_key,
  employee_id,
  email,
  platform,
  principal_id,
  termination_date,
  hours_since_term,
  sla_hours,
  status,
  first_detected_at,
  last_seen_at,
  resolved_at,
  details
FROM GRC_REVIEW.GOLD.EVAL_CURRENT
WHERE status = 'open';

GRANT SELECT ON VIEW GRC_REVIEW.GOLD.V_TERMINATION_SLA_VIOLATIONS TO ROLE GRC_AUDIT_READER;
