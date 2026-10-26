{% set recalculation_date_from = var('recalculation_date_from', '') %}
{% set recalculation_date_to = var('recalculation_date_to', '') %}
{% set conversion_period_days = var('conversion_period_days', 30) | int %}
{% set recalculation_id = var('recalculation_id', '') %}

with parameters as (
    select
        to_date(nullif('{{ recalculation_date_from }}', '')) as date_from,
        to_date(nullif('{{ recalculation_date_to }}', '')) as date_to,
        {{ conversion_period_days }}::number as conversion_period_days
),

prepared as (
    select deals.*
    from {{ ref('stg_crm_deals') }} as deals
    cross join parameters as params
    where
      {% if recalculation_id %}
      exists (
          select 1
          from CITORA.PLATFORM.RECALCULATION_IDENTIFIERS as scope
          where scope.RECALCULATION_ID = '{{ recalculation_id }}'
            and (
                scope.PHONE_NUMBER_HASH = deals.phone_number
                or scope.CONTACT_ID_HASH = deals.contact_id
            )
      )
      {% else %}
      (params.date_from is null and params.date_to is null)
      or (
          (
              (
                  params.date_from is null
                  or deals.created_at > dateadd(
                      day,
                      -params.conversion_period_days,
                      params.date_from
                  )
              )
              and (
                  params.date_to is null
                  or deals.created_at < dateadd(day, 1, params.date_to)
              )
          )
          or (
              (
                  params.date_from is null
                  or deals.paid_at >= params.date_from
              )
              and (
                  params.date_to is null
                  or deals.paid_at < dateadd(
                      day,
                      params.conversion_period_days,
                      params.date_to
                  )
              )
          )
      )
      {% endif %}
)

select *
from prepared
