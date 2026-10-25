-- Register the website-safe Excel upload procedure.
-- Run as ACCOUNTADMIN after fetching the latest Git branch.

USE ROLE CITORA_LOADER;
USE WAREHOUSE CITORA_LOADING_WH;
USE DATABASE CITORA;
USE SCHEMA PLATFORM;

CREATE OR REPLACE PROCEDURE CITORA.PLATFORM.LOAD_EXCEL_BASE64(
    EXCEL_BASE64 VARCHAR,
    SOURCE_FILE VARCHAR,
    TARGET_DATABASE VARCHAR,
    TARGET_SCHEMA VARCHAR,
    UPLOADED_BY VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.12'
PACKAGES = (
    'snowflake-snowpark-python',
    'openpyxl',
    'pandas',
    'pyarrow',
    'pydantic',
    'pyyaml'
)
IMPORTS = (
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/src/citora_ai_analytic/procedure.py',
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/src/citora_ai_analytic/config.py',
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/src/citora_ai_analytic/excel.py',
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/src/citora_ai_analytic/loader.py',
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/config/excel/source_db.yml',
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/config/mappings/crm_deals.yml'
)
HANDLER = 'procedure.run_base64'
COMMENT = 'Receives an XLSX file from the Citora website and appends a traceable RAW batch'
EXECUTE AS OWNER;

USE ROLE ACCOUNTADMIN;

GRANT USAGE ON PROCEDURE CITORA.PLATFORM.LOAD_EXCEL_BASE64(
    VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR
) TO ROLE CITORA_FRONTEND_UPLOADER;

DESCRIBE PROCEDURE CITORA.PLATFORM.LOAD_EXCEL_BASE64(
    VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR
);
