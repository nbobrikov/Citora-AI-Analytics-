select deal_id
from {{ ref('int_crm_deal_attribution') }}
where segment is null
   or source is null
