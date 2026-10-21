select phone_number
from {{ ref('int_crm_applications') }}
group by phone_number
having min(application_sequence_number) != 1
    or max(application_sequence_number) != count(*)
