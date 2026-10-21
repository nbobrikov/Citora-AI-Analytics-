select *
from {{ ref('int_crm_sales') }}
where amount <= 0
