-- Prerequisites:
--   1. CITORA.PLATFORM.CITORA_REPO is connected to the GitHub repository.
--   2. source_db.xlsx is uploaded to CITORA_RAW_STAGE/files.
--   3. CITORA_LOADER has READ and WRITE on CITORA_REPO.
--   4. CITORA_LOADER has USAGE on the Git API integration when required.

USE ROLE CITORA_LOADER;
USE WAREHOUSE CITORA_LOADING_WH;
USE DATABASE CITORA;
USE SCHEMA PLATFORM;

-- Synchronize the Snowflake repository clone with GitHub.
ALTER GIT REPOSITORY CITORA.PLATFORM.CITORA_REPO FETCH;

-- Confirm that the required versioned inputs are present in the main branch.
LIST @CITORA.PLATFORM.CITORA_REPO/branches/main/src/citora_ai_analytic/;
LIST @CITORA.PLATFORM.CITORA_REPO/branches/main/config/excel/source_db.yml;

-- Re-create the procedure so IMPORTS resolve to the latest fetched Python code.
EXECUTE IMMEDIATE FROM
    @CITORA.PLATFORM.CITORA_REPO/branches/main/snowflake/02_register_procedure.sql;

-- Validate the staged workbook and replace CITORA.RAW.CRM_DEALS.
CALL CITORA.PLATFORM.LOAD_EXCEL(
    BUILD_SCOPED_FILE_URL(
        @CITORA.PLATFORM.CITORA_RAW_STAGE,
        'files/source_db.xlsx'
    ),
    BUILD_SCOPED_FILE_URL(
        @CITORA.PLATFORM.CITORA_REPO,
        'branches/main/config/excel/source_db.yml'
    ),
    'CITORA',
    'RAW'
);

-- Post-load checks that do not expose personal contact data.
SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT "ID") AS distinct_id_count,
    COUNT_IF("ID" IS NULL) AS null_id_count,
    COUNT_IF("Дата создания" IS NULL) AS null_created_at_count,
    MIN("Дата создания") AS first_created_at,
    MAX("Дата создания") AS last_created_at,
    COUNT_IF("Дата оплаты" IS NOT NULL) AS paid_deal_count
FROM CITORA.RAW.CRM_DEALS;

SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    ORDINAL_POSITION
FROM CITORA.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'RAW'
  AND TABLE_NAME = 'CRM_DEALS'
ORDER BY ORDINAL_POSITION;
