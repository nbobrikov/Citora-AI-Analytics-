{% set other_label = var('other_attribution_label', 'Прочее') %}
{% set empty_label = var('empty_attribution_label', 'Без разметки') %}

with deals as (
    select
        deal_id,
        utm_source,
        utm_content,
        promo_code
    from {{ ref('stg_crm_deals') }}
),

promocode_dictionary as (
    select
        lower(trim(promocode)) as match_value,
        segment,
        source
    from {{ ref('promocode_mapping') }}
    qualify row_number() over (
        partition by lower(trim(promocode))
        order by priority
    ) = 1
),

source_dictionary as (
    select
        lower(trim(utm_source)) as match_value,
        source,
        endswith(trim(utm_source), '*') as is_prefix,
        priority
    from {{ ref('utm_source_mapping') }}
    qualify row_number() over (
        partition by lower(trim(utm_source))
        order by priority
    ) = 1
),

segment_dictionary as (
    select
        lower(trim(utm_content)) as match_value,
        segment,
        endswith(trim(utm_content), '*') as is_prefix,
        priority
    from {{ ref('utm_content_mapping') }}
    qualify row_number() over (
        partition by lower(trim(utm_content))
        order by priority
    ) = 1
),

source_candidates as (
    select
        deals.deal_id,
        dictionary.source
    from deals
    inner join source_dictionary as dictionary
        on (
            not dictionary.is_prefix
            and deals.utm_source = dictionary.match_value
        ) or (
            dictionary.is_prefix
            and startswith(
                deals.utm_source,
                left(dictionary.match_value, length(dictionary.match_value) - 1)
            )
        )
    qualify row_number() over (
        partition by deals.deal_id
        order by dictionary.is_prefix, dictionary.priority
    ) = 1
),

segment_candidates as (
    select
        deals.deal_id,
        dictionary.segment
    from deals
    inner join segment_dictionary as dictionary
        on (
            not dictionary.is_prefix
            and deals.utm_content = dictionary.match_value
        ) or (
            dictionary.is_prefix
            and startswith(
                deals.utm_content,
                left(dictionary.match_value, length(dictionary.match_value) - 1)
            )
        )
    qualify row_number() over (
        partition by deals.deal_id
        order by dictionary.is_prefix, dictionary.priority
    ) = 1
),

enriched as (
    select
        deals.deal_id,
        deals.utm_source,
        deals.utm_content,
        deals.promo_code,
        coalesce(
            promo.segment,
            content.segment,
            case
                when nullif(deals.utm_content, '') is null then '{{ empty_label }}'
                else '{{ other_label }}'
            end
        ) as segment,
        coalesce(
            promo.source,
            source.source,
            case
                when nullif(deals.utm_source, '') is null then '{{ empty_label }}'
                else '{{ other_label }}'
            end
        ) as source
    from deals
    left join promocode_dictionary as promo
        on deals.promo_code = promo.match_value
    left join segment_candidates as content
        on deals.deal_id = content.deal_id
    left join source_candidates as source
        on deals.deal_id = source.deal_id
)

select *
from enriched
