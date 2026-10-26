{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='reporting_row_id',
    on_schema_change='sync_all_columns',
    pre_hook=delete_recalculation_scope()
) }}

with enriched_matches as (
    select *
    from {{ ref('int_application_sales_enriched') }}
),

sales as (
    select
        sale_id,
        product
    from {{ ref('int_crm_sales') }}
),

final as (
    select
        md5(concat_ws(
            '|',
            coalesce(to_varchar(matches.application_id), 'NULL'),
            coalesce(to_varchar(matches.sale_id), 'NULL'),
            matches.match_type
        )) as reporting_row_id,
        matches.application_id,
        matches.application_contact_id,
        matches.application_created_at,
        matches.funnel,
        matches.application_manager,
        matches.sale_manager,
        matches.application_sequence_number,
        matches.is_unique,
        matches.phone_number,
        matches.sale_id,
        matches.sale_contact_id,
        matches.paid_at,
        matches.conversion_period_days,
        matches.amount,
        sales.product,
        matches.application_segment,
        matches.application_source,
        matches.application_promo,
        matches.sale_segment,
        matches.sale_source,
        matches.sale_promo,
        matches.final_segment,
        matches.final_source,
        matches.match_type,
        matches.application_load_id,
        matches.sale_load_id,
        matches.application_row_hash,
        matches.sale_row_hash,
        current_timestamp() as dbt_built_at
    from enriched_matches as matches
    left join sales
        on matches.sale_id = sales.sale_id
)

select *
from final
