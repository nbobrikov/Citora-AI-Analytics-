with matches as (
    select *
    from {{ ref('int_application_sales_matches') }}
),

enriched as (
    select
        matches.*,
        coalesce(sale_segment, application_segment) as final_segment,
        coalesce(sale_source, application_source) as final_source
    from matches
)

select *
from enriched
