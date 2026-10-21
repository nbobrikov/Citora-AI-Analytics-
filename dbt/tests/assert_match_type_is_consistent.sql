select *
from {{ ref('int_application_sales_matches') }}
where (match_type = 'matched' and (application_id is null or sale_id is null))
   or (
       match_type = 'application_without_sale'
       and (application_id is null or sale_id is not null or is_unique != 1)
   )
   or (
       match_type = 'sale_without_application'
       and (application_id is not null or sale_id is null or is_unique != 0)
   )
