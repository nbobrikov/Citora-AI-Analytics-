{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='reporting_event_id',
    on_schema_change='sync_all_columns',
    pre_hook="{{ delete_recalculation_scope() }}"
) }}

{% set recalculation_id = var('recalculation_id', '') %}

with detailed as (
    select *
    from {{ ref('fct_application_sales') }} as facts
    {% if recalculation_id %}
    where exists (
        select 1
        from CITORA.PLATFORM.RECALCULATION_IDENTIFIERS as scope
        where scope.RECALCULATION_ID = '{{ recalculation_id }}'
          and (
              scope.PHONE_NUMBER_HASH = facts.phone_number
              or scope.CONTACT_ID_HASH = facts.application_contact_id
              or scope.CONTACT_ID_HASH = facts.sale_contact_id
          )
    )
    {% endif %}
),

application_sales_rollup as (
    select
        application_id,
        count(case when sale_id is not null then 1 end) as matched_sales_count
    from detailed
    where application_id is not null
    group by application_id
),

application_events as (
    select
        md5(concat('APPLICATION|', to_varchar(details.application_id)))
            as reporting_event_id,
        'APPLICATION'::varchar as record_type,
        details.application_created_at as report_date,
        details.application_id,
        details.application_contact_id,
        details.phone_number,
        details.application_sequence_number,
        cast(null as number) as sale_id,
        cast(null as varchar) as sale_contact_id,
        details.application_created_at,
        cast(null as timestamp_ntz) as paid_at,
        details.funnel,
        details.application_manager as manager,
        details.product,
        details.final_segment,
        details.final_source,
        details.application_promo,
        cast(null as varchar) as sale_promo,
        details.match_type,
        rollup.matched_sales_count,
        details.conversion_period_days,
        cast(null as number(38, 2)) as amount,
        details.application_load_id,
        cast(null as varchar) as sale_load_id,
        current_timestamp() as dbt_built_at
    from detailed as details
    inner join application_sales_rollup as rollup
        on details.application_id = rollup.application_id
    where details.application_id is not null
      and details.is_unique = 1
),

sale_events as (
    select
        md5(concat('SALE|', to_varchar(sale_id))) as reporting_event_id,
        'SALE'::varchar as record_type,
        paid_at as report_date,
        application_id,
        application_contact_id,
        phone_number,
        application_sequence_number,
        sale_id,
        sale_contact_id,
        application_created_at,
        paid_at,
        funnel,
        sale_manager as manager,
        product,
        final_segment,
        final_source,
        cast(null as varchar) as application_promo,
        sale_promo,
        match_type,
        0::number as matched_sales_count,
        cast(null as float) as conversion_period_days,
        amount,
        application_load_id,
        sale_load_id,
        current_timestamp() as dbt_built_at
    from detailed
    where sale_id is not null
),

reporting_events as (
    select * from application_events
    union all
    select * from sale_events
)

select *
from reporting_events
