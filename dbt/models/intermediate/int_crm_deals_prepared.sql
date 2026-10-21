{% set configured_report_date = var('report_date', '') %}
{% set report_period = var('report_period', 'month') | lower %}
{% set report_period_number = var('report_period_number', 12) | int %}
{% set conversion_period_days = var('conversion_period_days', 30) | int %}

with parameters as (
    select
        coalesce(
            try_to_date('{{ configured_report_date }}'),
            current_date()
        ) as report_date,
        '{{ report_period }}'::varchar as report_period,
        {{ report_period_number }}::number as report_period_number,
        {{ conversion_period_days }}::number as conversion_period_days
),

period_boundary as (
    select
        *,
        case report_period
            when 'day' then dateadd(day, -report_period_number, report_date)
            when 'week' then dateadd(day, -7 * report_period_number, report_date)
            when 'month' then last_day(
                dateadd(month, -report_period_number, report_date),
                'month'
            )
            when 'quarter' then last_day(
                dateadd(quarter, -report_period_number, report_date),
                'quarter'
            )
            else null
        end as oldest_period_end
    from parameters
),

prepared as (
    select deals.*
    from {{ ref('stg_crm_deals') }} as deals
    cross join period_boundary as params
    where params.oldest_period_end is not null
      and (
          (
              deals.created_at > dateadd(
                  day,
                  -params.conversion_period_days,
                  params.oldest_period_end
              )
              and deals.created_at < dateadd(day, 1, params.report_date)
          )
          or (
              deals.paid_at > dateadd(day, 1, params.oldest_period_end)
              and deals.paid_at < dateadd(
                  day,
                  params.conversion_period_days,
                  params.report_date
              )
          )
      )
)

select *
from prepared
