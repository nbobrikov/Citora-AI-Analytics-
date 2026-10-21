with prepared as (
    select *
    from {{ ref('int_crm_deals_prepared') }}
),

sales_funnels as (
    select funnel
    from {{ ref('sales_funnels') }}
),

sales as (
    select
        deals.deal_id as sale_id,
        deals.contact_id as sale_contact_id,
        deals.paid_at,
        deals.phone_number,
        deals.amount,
        deals.product,
        deals.load_id,
        deals.loaded_at,
        deals.source_file,
        deals.source_row_number,
        deals.row_hash
    from prepared as deals
    inner join sales_funnels as funnels
        on deals.funnel = funnels.funnel
    where deals.paid_at is not null
      and deals.product is not null
      and deals.product != ''
      and deals.amount > 0
)

select *
from sales
