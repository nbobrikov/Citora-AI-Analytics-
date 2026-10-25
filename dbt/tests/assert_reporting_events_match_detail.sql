with detail_counts as (
    select
        count(distinct application_id) as applications_count,
        count(distinct sale_id) as sales_count,
        count(case
            when application_id is not null and sale_id is not null then 1
        end) as matched_sales_count
    from {{ ref('fct_application_sales') }}
),

event_counts as (
    select
        count(case when record_type = 'APPLICATION' then 1 end)
            as applications_count,
        count(case when record_type = 'SALE' then 1 end) as sales_count,
        sum(case
            when record_type = 'APPLICATION' then matched_sales_count
            else 0
        end) as matched_sales_count
    from {{ ref('fct_reporting_metrics') }}
)

select event_counts.*
from event_counts
cross join detail_counts
where event_counts.applications_count != detail_counts.applications_count
   or event_counts.sales_count != detail_counts.sales_count
   or event_counts.matched_sales_count != detail_counts.matched_sales_count
