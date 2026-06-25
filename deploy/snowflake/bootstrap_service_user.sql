-- TrustOps Snowflake service-user bootstrap.
--
-- Run after bootstrap_poc.sql from ACCOUNTADMIN or a governed GRC admin role
-- allowed to manage users and grant TRUSTOPS_READER.
--
-- This script creates a non-human Snowflake service user for scheduled
-- TrustOps ingestion. It does not create passwords, PATs, network integrations,
-- stages, or write privileges.
--
-- Before running, generate or retrieve an RSA public key from your secret
-- manager process, remove BEGIN/END delimiters and line breaks, then set:
--
--   SET TRUSTOPS_SERVICE_RSA_PUBLIC_KEY = '<public-key-body-without-delimiters>';
--
-- The matching private key stays outside Snowflake and outside this repo. Mount
-- it into the TrustOps runtime and reference it with SNOWFLAKE_PRIVATE_KEY_FILE.

USE ROLE ACCOUNTADMIN;

SET TRUSTOPS_SERVICE_USER = 'TRUSTOPS_INGEST_SVC';

CREATE USER IF NOT EXISTS IDENTIFIER($TRUSTOPS_SERVICE_USER)
  TYPE = SERVICE
  DEFAULT_ROLE = TRUSTOPS_READER
  DEFAULT_WAREHOUSE = TRUSTOPS_READ_WH
  COMMENT = 'TrustOps read-only evidence ingestion service user';

ALTER USER IDENTIFIER($TRUSTOPS_SERVICE_USER)
  SET RSA_PUBLIC_KEY = $TRUSTOPS_SERVICE_RSA_PUBLIC_KEY;

GRANT ROLE TRUSTOPS_READER TO USER IDENTIFIER($TRUSTOPS_SERVICE_USER);

-- Optional verification. RSA_PUBLIC_KEY_FP should be populated, and the user
-- should have only TRUSTOPS_READER for this POC path.
DESC USER IDENTIFIER($TRUSTOPS_SERVICE_USER);
SHOW GRANTS TO USER IDENTIFIER($TRUSTOPS_SERVICE_USER);
