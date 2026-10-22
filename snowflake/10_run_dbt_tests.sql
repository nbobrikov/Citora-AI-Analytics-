-- Run all generic and singular Citora dbt data-quality tests.
-- Run after 09_run_dbt_models.sql succeeds.

USE ROLE CITORA_TRANSFORMER;
USE WAREHOUSE CITORA_TRANSFORMING_WH;
USE DATABASE CITORA;
USE SCHEMA PLATFORM;

EXECUTE DBT PROJECT CITORA.PLATFORM.CITORA_DBT_PROJECT
    ARGS = 'test --target prod';
