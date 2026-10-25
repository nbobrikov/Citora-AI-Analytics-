with prepared as (
    select *
    from {{ ref('int_crm_deals_prepared') }}
),

application_funnels as (
    select funnel
    from {{ ref('application_funnels') }}
),

applications as (
    select
        deals.deal_id as application_id,
        deals.contact_id as application_contact_id,
        deals.funnel,
        deals.manager as application_manager,
        deals.utm_source as application_source,
        deals.utm_content as application_segment,
        deals.promo_code as application_promo,
        deals.created_at as application_created_at,
        deals.phone_number,
        row_number() over (
            partition by deals.phone_number
            order by deals.created_at, deals.deal_id
        ) as application_sequence_number,
        deals.load_id,
        deals.loaded_at,
        deals.source_file,
        deals.source_row_number,
        deals.row_hash
    from prepared as deals
    inner join application_funnels as funnels
        on deals.funnel = funnels.funnel
    where deals.paid_at is null
      and deals.phone_number is not null
      and deals.phone_number != ''
)

select *
from applications
