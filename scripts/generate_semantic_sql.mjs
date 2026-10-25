import { readFileSync, writeFileSync } from "node:fs";

const yaml = readFileSync("config/semantic/citora_analytics_semantic_view.yml", "utf8").trimEnd();
const header = `-- Validate and deploy the Snowflake-native Citora semantic view from Git YAML.
-- The YAML below is generated from config/semantic/citora_analytics_semantic_view.yml.

USE ROLE SECURITYADMIN;

GRANT CREATE SEMANTIC VIEW ON SCHEMA CITORA.ANALYTICS
    TO ROLE CITORA_TRANSFORMER;

USE ROLE CITORA_TRANSFORMER;
USE WAREHOUSE CITORA_TRANSFORMING_WH;
USE DATABASE CITORA;
USE SCHEMA ANALYTICS;

-- Remove the obsolete Python wrapper used by the previous deployment approach.
DROP PROCEDURE IF EXISTS CITORA.PLATFORM.DEPLOY_SEMANTIC_VIEW();

-- Validate the full specification without changing Snowflake objects.
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
    'CITORA.ANALYTICS',
    $$
`;
const between = `
    $$,
    TRUE,
    TRUE
);
-- Create a new semantic view or alter the existing one after validation succeeds.
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
    'CITORA.ANALYTICS',
    $$
`;
const footer = `
    $$,
    FALSE,
    TRUE
);

SHOW SEMANTIC VIEWS LIKE 'CITORA_ANALYTICS_SEMANTIC_VIEW'
    IN SCHEMA CITORA.ANALYTICS;

SELECT *
FROM SEMANTIC_VIEW(
    CITORA.ANALYTICS.CITORA_ANALYTICS_SEMANTIC_VIEW
    METRICS
        APPLICATION_SALES.LEADS,
        APPLICATION_SALES.APPLICATIONS_COUNT,
        APPLICATION_SALES.SALES_COUNT
);
`;

writeFileSync("snowflake/12_register_semantic_view.sql", `${header}${yaml}${between}${yaml}${footer}`);
