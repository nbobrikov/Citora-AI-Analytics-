-- Deploy the latest dbt source from Git and build the final reporting table.
-- Run after the Git repository clone has been fetched.

USE ROLE CITORA_TRANSFORMER;
USE WAREHOUSE CITORA_TRANSFORMING_WH;
USE DATABASE CITORA;
USE SCHEMA PLATFORM;

ALTER DBT PROJECT CITORA.PLATFORM.CITORA_DBT_PROJECT
    DEPLOY
    FROM '@CITORA.PLATFORM.CITORA_REPO/branches/main/dbt';

EXECUTE DBT PROJECT CITORA.PLATFORM.CITORA_DBT_PROJECT
    ARGS = 'run --target prod --full-refresh';

SELECT
    COUNT(*) AS reporting_row_count,
    COUNT(DISTINCT application_id) AS application_count,
    COUNT(DISTINCT sale_id) AS sale_count,
    COUNT_IF(match_type = 'matched') AS matched_row_count,
    COUNT_IF(match_type = 'application_without_sale') AS application_only_row_count,
    COUNT_IF(match_type = 'sale_without_application') AS sale_only_row_count,
    SUM(amount) AS total_amount,
    MAX(dbt_built_at) AS dbt_built_at
FROM CITORA.ANALYTICS.FCT_APPLICATION_SALES;

SELECT
    final_segment,
    final_source,
    COUNT(*) AS row_count,
    SUM(amount) AS total_amount
FROM CITORA.ANALYTICS.FCT_APPLICATION_SALES
GROUP BY final_segment, final_source
ORDER BY row_count DESC, final_segment, final_source;
