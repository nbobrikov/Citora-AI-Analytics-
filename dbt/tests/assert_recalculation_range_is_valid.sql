{% set recalculation_date_from = var('recalculation_date_from', '') %}
{% set recalculation_date_to = var('recalculation_date_to', '') %}

with parameters as (
    select
        to_date(nullif('{{ recalculation_date_from }}', '')) as date_from,
        to_date(nullif('{{ recalculation_date_to }}', '')) as date_to
)

select *
from parameters
where date_from > date_to
