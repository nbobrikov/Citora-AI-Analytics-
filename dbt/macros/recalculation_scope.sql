{% macro delete_recalculation_scope() %}
  {% set recalculation_id = var('recalculation_id', '') %}
  {% if is_incremental() and recalculation_id %}
    delete from {{ this }} as target
    where exists (
      select 1
      from CITORA.PLATFORM.RECALCULATION_IDENTIFIERS as scope
      where scope.RECALCULATION_ID = '{{ recalculation_id }}'
        and (
          scope.PHONE_NUMBER_HASH = target.PHONE_NUMBER
          or scope.CONTACT_ID_HASH = target.APPLICATION_CONTACT_ID
          or scope.CONTACT_ID_HASH = target.SALE_CONTACT_ID
        )
    )
  {% else %}
    select 1
  {% endif %}
{% endmacro %}
