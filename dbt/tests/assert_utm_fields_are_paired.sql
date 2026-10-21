select *
from {{ ref('stg_crm_deals') }}
where (utm_source is null and utm_content is not null)
   or (utm_source is not null and utm_content is null)
