-- Prerequisites:
--   1. Run 01_infrastructure.sql.
--   2. Create CITORA.PLATFORM.CITORA_REPO using Snowflake Git integration.
--   3. Fetch the GitHub branch that contains this project.
--   4. Grant CITORA_LOADER READ on CITORA.PLATFORM.CITORA_REPO.

USE ROLE CITORA_LOADER;
USE WAREHOUSE CITORA_LOADING_WH;
USE DATABASE CITORA;
USE SCHEMA PLATFORM;

CREATE OR REPLACE PROCEDURE CITORA.PLATFORM.LOAD_EXCEL(
    EXCEL_SCOPED_URL VARCHAR,
    CONTRACT_SCOPED_URL VARCHAR,
    TARGET_DATABASE VARCHAR,
    TARGET_SCHEMA VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.12'
PACKAGES = (
    'snowflake-snowpark-python',
    'openpyxl',
    'pandas',
    'pydantic',
    'pyyaml'
)
IMPORTS = (
    '@CITORA.PLATFORM.CITORA_REPO/branches/main/src/'
)
HANDLER = 'citora_ai_analytic.procedure.run'
EXECUTE AS OWNER
COMMENT = 'Validates a staged Excel workbook using a Git-versioned YAML contract and replaces RAW tables';

GRANT USAGE ON PROCEDURE CITORA.PLATFORM.LOAD_EXCEL(
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR
) TO ROLE CITORA_LOADER;

-- Example after uploading source_db.xlsx to CITORA_RAW_STAGE/files.
-- The YAML contract is read directly from the Git repository clone.
--
-- PUT file://<absolute-path>/source_db.xlsx
--     @CITORA.PLATFORM.CITORA_RAW_STAGE/files
--     AUTO_COMPRESS = FALSE
--     OVERWRITE = TRUE;
--
-- CALL CITORA.PLATFORM.LOAD_EXCEL(
--     BUILD_SCOPED_FILE_URL(
--         @CITORA.PLATFORM.CITORA_RAW_STAGE,
--         'files/source_db.xlsx'
--     ),
--     BUILD_SCOPED_FILE_URL(
--         @CITORA.PLATFORM.CITORA_REPO,
--         'branches/main/config/excel/source_db.yml'
--     ),
--     'CITORA',
--     'RAW'
-- );

DESCRIBE PROCEDURE CITORA.PLATFORM.LOAD_EXCEL(
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR
);
