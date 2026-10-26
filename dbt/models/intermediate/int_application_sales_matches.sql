{% set conversion_period_days = var('conversion_period_days', 30) | int %}
with applications as (
    select *
    from {{ ref('int_crm_applications') }}
),

sales as (
    select *
    from {{ ref('int_crm_sales') }}
),

candidate_pairs as (
    select
        applications.application_id,
        applications.application_contact_id,
        applications.funnel,
        applications.application_manager,
        applications.application_source,
        applications.application_segment,
        applications.application_promo,
        applications.application_created_at,
        applications.phone_number,
        applications.application_sequence_number,
        sales.sale_id,
        sales.sale_contact_id,
        sales.sale_manager,
        sales.sale_source,
        sales.sale_segment,
        sales.sale_promo,
        sales.paid_at,
        sales.amount,
        applications.load_id as application_load_id,
        sales.load_id as sale_load_id,
        applications.row_hash as application_row_hash,
        sales.row_hash as sale_row_hash
    from applications
    inner join sales
        on applications.phone_number = sales.phone_number
       and sales.paid_at > applications.application_created_at
       and sales.paid_at < dateadd(
           day,
           {{ conversion_period_days }},
           applications.application_created_at
       )
),

assigned_sales as (
    select *
    from candidate_pairs
    qualify row_number() over (
        partition by sale_id
        order by
            application_created_at,
            application_sequence_number,
            application_id
    ) = 1
),

matched as (
    select
        application_id,
        application_contact_id,
        funnel,
        application_manager,
        application_source,
        application_segment,
        application_promo,
        application_created_at,
        phone_number,
        application_sequence_number,
        sale_id,
        sale_contact_id,
        sale_manager,
        sale_source,
        sale_segment,
        sale_promo,
        paid_at,
        datediff(
            millisecond,
            application_created_at,
            paid_at
        ) / 86400000.0 as conversion_period_days,
        case
            when row_number() over (
                partition by application_id
                order by paid_at, sale_id
            ) = 1 then 1
            else 0
        end as is_unique,
        amount,
        application_load_id,
        sale_load_id,
        application_row_hash,
        sale_row_hash,
        'matched'::varchar as match_type
    from assigned_sales
),

unmatched_applications as (
    select
        applications.application_id,
        applications.application_contact_id,
        applications.funnel,
        applications.application_manager,
        applications.application_source,
        applications.application_segment,
        applications.application_promo,
        applications.application_created_at,
        applications.phone_number,
        applications.application_sequence_number,
        cast(null as number) as sale_id,
        cast(null as varchar) as sale_contact_id,
        cast(null as varchar) as sale_manager,
        cast(null as varchar) as sale_source,
        cast(null as varchar) as sale_segment,
        cast(null as varchar) as sale_promo,
        cast(null as timestamp_ntz) as paid_at,
        cast(null as float) as conversion_period_days,
        1::number as is_unique,
        cast(null as number(38, 2)) as amount,
        applications.load_id as application_load_id,
        cast(null as varchar) as sale_load_id,
        applications.row_hash as application_row_hash,
        cast(null as varchar) as sale_row_hash,
        'application_without_sale'::varchar as match_type
    from applications
    where not exists (
        select 1
        from assigned_sales
        where assigned_sales.application_id = applications.application_id
    )
),

unmatched_sales as (
    select
        cast(null as number) as application_id,
        cast(null as varchar) as application_contact_id,
        cast(null as varchar) as funnel,
        cast(null as varchar) as application_manager,
        cast(null as varchar) as application_source,
        cast(null as varchar) as application_segment,
        cast(null as varchar) as application_promo,
        cast(null as timestamp_ntz) as application_created_at,
        sales.phone_number,
        cast(null as number) as application_sequence_number,
        sales.sale_id,
        sales.sale_contact_id,
        sales.sale_manager,
        sales.sale_source,
        sales.sale_segment,
        sales.sale_promo,
        sales.paid_at,
        cast(null as float) as conversion_period_days,
        0::number as is_unique,
        sales.amount,
        cast(null as varchar) as application_load_id,
        sales.load_id as sale_load_id,
        cast(null as varchar) as application_row_hash,
        sales.row_hash as sale_row_hash,
        'sale_without_application'::varchar as match_type
    from sales
    where not exists (
        select 1
        from assigned_sales
        where assigned_sales.sale_id = sales.sale_id
    )
),

combined as (
    select * from matched
    union all
    select * from unmatched_applications
    union all
    select * from unmatched_sales
)

select *
from combined
