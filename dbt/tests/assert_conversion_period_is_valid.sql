{% set conversion_period_days = var('conversion_period_days', 30) | int %}

select *
from {{ ref('int_application_sales_matches') }}
where {{ conversion_period_days }} <= 0
   or (
       match_type = 'matched'
       and (
           conversion_period_days <= 0
           or conversion_period_days >= {{ conversion_period_days }}
       )
   )
