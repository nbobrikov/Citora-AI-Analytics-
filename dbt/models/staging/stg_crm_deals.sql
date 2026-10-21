with latest_successful_load as (
    select load_id
    from {{ source('citora_raw', 'load_history') }}
    where status = 'SUCCESS'
    qualify row_number() over (
        order by finished_at desc, started_at desc, load_id desc
    ) = 1
),

source_data as (
    select raw.*
    from {{ source('citora_raw', 'crm_deals') }} as raw
    inner join latest_successful_load as latest
        on raw."_LOAD_ID" = latest.load_id
),

renamed_and_cleaned as (
    select
        "deal_id"::number as deal_id,
        "contact_id"::number as contact_id,
        "funnel"::varchar as funnel,
        "manager"::varchar as manager,
        "created_at"::timestamp_ntz as created_at,
        lower("phone_number"::varchar) as phone_number,
        "paid_at"::timestamp_ntz as paid_at,
        case
            when "utm_content" is null then null
            else lower("utm_source"::varchar)
        end as utm_source,
        case
            when "utm_source" is null then null
            else lower("utm_content"::varchar)
        end as utm_content,
        lower("promo_code"::varchar) as promo_code,
        lower("product"::varchar) as product,
        "amount"::number(38, 2) as amount,
        raw."_LOAD_ID"::varchar as load_id,
        raw."_LOADED_AT"::timestamp_tz as loaded_at,
        raw."_SOURCE_FILE"::varchar as source_file,
        raw."_SOURCE_ROW_NUMBER"::number as source_row_number,
        raw."_ROW_HASH"::varchar as row_hash
    from source_data as raw
)

select *
from renamed_and_cleaned
