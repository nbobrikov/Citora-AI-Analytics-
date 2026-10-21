{% set empty_label = var('empty_attribution_label', 'Без разметки') %}

with matches as (
    select *
    from {{ ref('int_application_sales_matches') }}
),

attribution as (
    select *
    from {{ ref('int_crm_deal_attribution') }}
),

enriched as (
    select
        matches.*,
        application_attribution.segment as application_segment,
        application_attribution.source as application_source,
        sale_attribution.segment as sale_segment,
        sale_attribution.source as sale_source,
        case
            when coalesce(sale_attribution.segment, '{{ empty_label }}') = '{{ empty_label }}'
                and application_attribution.segment is not null
                then application_attribution.segment
            else coalesce(sale_attribution.segment, '{{ empty_label }}')
        end as final_segment,
        case
            when coalesce(sale_attribution.source, '{{ empty_label }}') = '{{ empty_label }}'
                and application_attribution.source is not null
                then application_attribution.source
            else coalesce(sale_attribution.source, '{{ empty_label }}')
        end as final_source
    from matches
    left join attribution as application_attribution
        on matches.application_id = application_attribution.deal_id
    left join attribution as sale_attribution
        on matches.sale_id = sale_attribution.deal_id
)

select *
from enriched
