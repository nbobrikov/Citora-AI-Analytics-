-- One-time privacy migration for existing RAW data.
-- Run as ACCOUNTADMIN only after the latest Git revision has been fetched and
-- 03_register_procedure.sql plus 18_register_frontend_excel_upload.sql have
-- recreated both loaders with SHA-256 protection.

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE CITORA_LOADING_WH;
USE DATABASE CITORA;

CREATE OR REPLACE TRANSIENT TABLE CITORA.RAW.CRM_DEALS_HASHED
DATA_RETENTION_TIME_IN_DAYS = 0
AS
SELECT * REPLACE (
    CASE
        WHEN REGEXP_LIKE(TRIM(TO_VARCHAR("contact_id")), '^[0-9a-fA-F]{64}$')
            THEN LOWER(TRIM(TO_VARCHAR("contact_id")))
        ELSE SHA2(COALESCE(NULLIF(TRIM(TO_VARCHAR("contact_id")), ''), '0'), 256)
    END AS "contact_id",
    CASE
        WHEN REGEXP_LIKE(TRIM(TO_VARCHAR("phone_number")), '^[0-9a-fA-F]{64}$')
            THEN LOWER(TRIM(TO_VARCHAR("phone_number")))
        ELSE SHA2(COALESCE(NULLIF(TRIM(LOWER(TO_VARCHAR("phone_number"))), ''), '0'), 256)
    END AS "phone_number"
)
FROM CITORA.RAW.CRM_DEALS;

CREATE OR REPLACE TRANSIENT TABLE CITORA.RAW.CRM_DEALS
COPY GRANTS
DATA_RETENTION_TIME_IN_DAYS = 0
AS
SELECT * FROM CITORA.RAW.CRM_DEALS_HASHED;

DROP TABLE CITORA.RAW.CRM_DEALS_HASHED;

-- Rebuild every derived model so plaintext identifiers disappear from the
-- current staging, intermediate and analytics objects as well.
EXECUTE DBT PROJECT CITORA.PLATFORM.CITORA_DBT_PROJECT
ARGS = 'run --target prod --full-refresh';

-- Verification: both sensitive RAW columns must contain only SHA-256 values.
SELECT
    COUNT(*) AS total_rows,
    COUNT_IF(NOT REGEXP_LIKE("contact_id", '^[0-9a-f]{64}$')) AS invalid_contact_ids,
    COUNT_IF(NOT REGEXP_LIKE("phone_number", '^[0-9a-f]{64}$')) AS invalid_phone_numbers
FROM CITORA.RAW.CRM_DEALS;
