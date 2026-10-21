from pathlib import Path

import pytest
from pydantic import ValidationError

from citora_ai_analytic.config import (
    load_excel_contract,
    load_field_mapping,
    parse_excel_contract,
)

PROJECT_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PROJECT_ROOT / "config" / "excel" / "source_db.yml"
MAPPING_PATH = PROJECT_ROOT / "config" / "mappings" / "crm_deals.yml"


def test_source_db_contract_is_valid() -> None:
    contract = load_excel_contract(CONTRACT_PATH)

    assert contract.version == 1
    assert contract.workbook.id == "source_db"
    assert contract.workbook.file_name == "source_db.xlsx"
    assert len(contract.workbook.sheets) == 1

    sheet = contract.workbook.sheets[0]
    assert sheet.name == "DEAL"
    assert sheet.target_table == "CRM_DEALS"
    assert len(sheet.columns) == 19
    assert len({column.name for column in sheet.columns}) == 19


def test_contract_rejects_duplicate_columns() -> None:
    yaml_content = """
version: 1
workbook:
  id: test_book
  description: Test workbook.
  file_name: test.xlsx
  sheets:
    - name: Sheet1
      description: Test sheet.
      header_row: 1
      target_table: TEST_TABLE
      columns:
        - name: ID
          type: integer
          nullable: false
          description: First identifier.
        - name: ID
          type: integer
          nullable: false
          description: Duplicate identifier.
"""

    with pytest.raises(ValidationError, match="duplicate columns"):
        parse_excel_contract(yaml_content)


def test_contract_rejects_unknown_properties() -> None:
    yaml_content = """
version: 1
unknown_property: true
workbook:
  id: test_book
  description: Test workbook.
  file_name: test.xlsx
  sheets:
    - name: Sheet1
      description: Test sheet.
      header_row: 1
      target_table: TEST_TABLE
      columns:
        - name: ID
          type: integer
          nullable: false
          description: Identifier.
"""

    with pytest.raises(ValidationError, match="unknown_property"):
        parse_excel_contract(yaml_content)


def test_crm_deals_mapping_has_all_calculation_fields() -> None:
    mapping = load_field_mapping(MAPPING_PATH)
    fields = {field.canonical_name: field for field in mapping.dataset.fields}

    assert set(fields) == {
        "deal_id",
        "contact_id",
        "funnel",
        "manager",
        "created_at",
        "phone_number",
        "paid_at",
        "utm_source",
        "utm_content",
        "promo_code",
        "product",
        "amount",
    }
    assert all(field.required for field in fields.values())
    assert fields["deal_id"].nullable is False
    assert fields["paid_at"].nullable is True
    assert fields["utm_source"].nullable is True
    assert fields["utm_content"].nullable is True
    assert fields["promo_code"].nullable is True
