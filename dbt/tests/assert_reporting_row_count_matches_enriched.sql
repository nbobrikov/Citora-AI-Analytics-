with reporting as (
    select count(*) as row_count
    from {{ ref('fct_application_sales') }}
),

enriched as (
    select count(*) as row_count
    from {{ ref('int_application_sales_enriched') }}
)

select
    reporting.row_count as reporting_row_count,
    enriched.row_count as enriched_row_count
from reporting
cross join enriched
where reporting.row_count != enriched.row_count
