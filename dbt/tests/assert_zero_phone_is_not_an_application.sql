select application_id
from {{ ref('int_crm_applications') }}
where phone_number = '0'
