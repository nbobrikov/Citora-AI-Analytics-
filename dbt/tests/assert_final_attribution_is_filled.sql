select
    application_id,
    sale_id
from {{ ref('int_application_sales_enriched') }}
where final_segment is null
   or final_source is null
