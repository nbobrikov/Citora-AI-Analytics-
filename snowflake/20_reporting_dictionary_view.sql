-- Central report-time attribution layer.
-- Every consumer (web reports, SQL, Semantic View and Cortex Agent) must read
-- this view instead of applying dictionary logic independently.

USE ROLE ACCOUNTADMIN;
USE DATABASE CITORA;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE VIEW CITORA.ANALYTICS.V_REPORTING_METRICS_ENRICHED AS
WITH dictionary_rows AS (
    SELECT
        facts.*,
        sets.dictionary_id,
        sets.owner_email,
        IFF(
            facts.record_type = 'APPLICATION',
            facts.application_promo,
            facts.sale_promo
        ) AS event_promo
    FROM CITORA.ANALYTICS.FCT_REPORTING_METRICS AS facts
    CROSS JOIN CITORA.CONFIG.DICTIONARY_SETS AS sets
    WHERE sets.owner_email IS NOT NULL
),

promo_candidates AS (
    SELECT
        dictionary_data.dictionary_id,
        dictionary_data.reporting_event_id,
        entries.output_source,
        entries.output_segment
    FROM dictionary_rows AS dictionary_data
    INNER JOIN CITORA.CONFIG.DICTIONARY_ENTRIES AS entries
        ON dictionary_data.dictionary_id = entries.dictionary_id
       AND entries.mapping_type = 'PROMO'
       AND LOWER(TRIM(dictionary_data.event_promo)) = entries.match_value
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY dictionary_data.dictionary_id, dictionary_data.reporting_event_id
        ORDER BY entries.priority
    ) = 1
),

source_candidates AS (
    SELECT
        dictionary_data.dictionary_id,
        dictionary_data.reporting_event_id,
        entries.output_source
    FROM dictionary_rows AS dictionary_data
    INNER JOIN CITORA.CONFIG.DICTIONARY_ENTRIES AS entries
        ON dictionary_data.dictionary_id = entries.dictionary_id
       AND entries.mapping_type = 'SOURCE'
       AND (
            (NOT entries.is_prefix AND LOWER(TRIM(dictionary_data.final_source)) = entries.match_value)
            OR (
                entries.is_prefix
                AND STARTSWITH(
                    LOWER(TRIM(dictionary_data.final_source)),
                    LEFT(entries.match_value, LENGTH(entries.match_value) - 1)
                )
            )
       )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY dictionary_data.dictionary_id, dictionary_data.reporting_event_id
        ORDER BY entries.is_prefix, entries.priority
    ) = 1
),

segment_candidates AS (
    SELECT
        dictionary_data.dictionary_id,
        dictionary_data.reporting_event_id,
        entries.output_segment
    FROM dictionary_rows AS dictionary_data
    INNER JOIN CITORA.CONFIG.DICTIONARY_ENTRIES AS entries
        ON dictionary_data.dictionary_id = entries.dictionary_id
       AND entries.mapping_type = 'SEGMENT'
       AND (
            (NOT entries.is_prefix AND LOWER(TRIM(dictionary_data.final_segment)) = entries.match_value)
            OR (
                entries.is_prefix
                AND STARTSWITH(
                    LOWER(TRIM(dictionary_data.final_segment)),
                    LEFT(entries.match_value, LENGTH(entries.match_value) - 1)
                )
            )
       )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY dictionary_data.dictionary_id, dictionary_data.reporting_event_id
        ORDER BY entries.is_prefix, entries.priority
    ) = 1
),

manager_candidates AS (
    SELECT
        dictionary_data.dictionary_id,
        dictionary_data.reporting_event_id,
        entries.output_manager
    FROM dictionary_rows AS dictionary_data
    INNER JOIN CITORA.CONFIG.DICTIONARY_ENTRIES AS entries
        ON dictionary_data.dictionary_id = entries.dictionary_id
       AND entries.mapping_type = 'MANAGER'
       AND LOWER(TRIM(dictionary_data.manager)) = entries.match_value
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY dictionary_data.dictionary_id, dictionary_data.reporting_event_id
        ORDER BY entries.priority
    ) = 1
)

SELECT
    dictionary_data.* EXCLUDE (final_source, final_segment, manager, event_promo),
    dictionary_data.final_source AS raw_source,
    dictionary_data.final_segment AS raw_segment,
    dictionary_data.manager AS raw_manager,
    COALESCE(
        promo.output_source,
        source.output_source,
        IFF(NULLIF(TRIM(dictionary_data.final_source), '') IS NULL, 'Без разметки', 'Прочее')
    ) AS final_source,
    COALESCE(
        promo.output_segment,
        segment.output_segment,
        IFF(NULLIF(TRIM(dictionary_data.final_segment), '') IS NULL, 'Без разметки', 'Прочее')
    ) AS final_segment,
    COALESCE(
        manager.output_manager,
        IFF(NULLIF(TRIM(dictionary_data.manager), '') IS NULL, 'Без менеджера', 'Прочее')
    ) AS manager
FROM dictionary_rows AS dictionary_data
LEFT JOIN promo_candidates AS promo
    USING (dictionary_id, reporting_event_id)
LEFT JOIN source_candidates AS source
    USING (dictionary_id, reporting_event_id)
LEFT JOIN segment_candidates AS segment
    USING (dictionary_id, reporting_event_id)
LEFT JOIN manager_candidates AS manager
    USING (dictionary_id, reporting_event_id);

GRANT SELECT ON VIEW CITORA.ANALYTICS.V_REPORTING_METRICS_ENRICHED
    TO ROLE CITORA_FRONTEND_READER;
GRANT SELECT ON VIEW CITORA.ANALYTICS.V_REPORTING_METRICS_ENRICHED
    TO ROLE CITORA_TRANSFORMER;
GRANT SELECT ON VIEW CITORA.ANALYTICS.V_REPORTING_METRICS_ENRICHED
    TO ROLE CITORA_ANALYST;

SELECT dictionary_id, owner_email, COUNT(*) AS event_count
FROM CITORA.ANALYTICS.V_REPORTING_METRICS_ENRICHED
GROUP BY dictionary_id, owner_email
ORDER BY owner_email, dictionary_id;
