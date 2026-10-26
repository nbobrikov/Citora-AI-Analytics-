with source_data as (
    select
        raw.*,
        history.finished_at as load_finished_at
    from {{ source('citora_raw', 'crm_deals') }} as raw
    inner join {{ source('citora_raw', 'load_history') }} as history
        on raw."_LOAD_ID" = history.load_id
    where history.status = 'SUCCESS'
),

latest_deal_version as (
    select *
    from source_data
    qualify row_number() over (
        partition by "deal_id"
        order by
            load_finished_at desc,
            "_LOADED_AT" desc,
            "_SOURCE_ROW_NUMBER" desc,
            "_LOAD_ID" desc
    ) = 1
),

renamed_and_cleaned as (
    select
        "deal_id"::number as deal_id,
        coalesce(
            nullif(trim(lower("contact_id"::varchar)), ''),
            sha2('0', 256)
        ) as contact_id,
        "funnel"::varchar as funnel,
        "manager"::varchar as manager,
        "created_at"::timestamp_ntz as created_at,
        coalesce(
            nullif(trim(lower("phone_number"::varchar)), ''),
            sha2('0', 256)
        ) as phone_number,
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
    from latest_deal_version as raw
)

select *
from renamed_and_cleaned
