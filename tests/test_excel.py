from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from citora_ai_analytic.config import load_excel_contract, load_field_mapping
from citora_ai_analytic.excel import read_excel_bytes, read_mapped_excel_bytes

PROJECT_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PROJECT_ROOT / "config" / "excel" / "source_db.yml"
SOURCE_EXCEL_PATH = PROJECT_ROOT.parent / "Исходные данные" / "source_db.xlsx"
MAPPING_PATH = PROJECT_ROOT / "config" / "mappings" / "crm_deals.yml"


def test_source_excel_matches_yaml_contract() -> None:
    if not SOURCE_EXCEL_PATH.is_file():
        pytest.skip(f"Source workbook is not available: {SOURCE_EXCEL_PATH}")

    contract = load_excel_contract(CONTRACT_PATH)
    frames = read_excel_bytes(SOURCE_EXCEL_PATH.read_bytes(), contract)

    assert set(frames) == {"CRM_DEALS"}

    deals = frames["CRM_DEALS"]
    expected_columns = [
        column.name for column in contract.workbook.sheets[0].columns
    ]

    assert deals.shape == (15_183, 19)
    assert list(deals.columns) == expected_columns
    assert deals["ID"].dtype == pd.Int64Dtype()
    assert deals["ID"].notna().all()
    assert deals["ID"].is_unique
    assert pd.api.types.is_datetime64_any_dtype(deals["Дата создания"])
    assert deals["Дата создания"].notna().all()
    assert pd.api.types.is_datetime64_any_dtype(deals["Дата оплаты"])
    assert isinstance(deals["Номер телефона контакта"].dtype, pd.StringDtype)
    assert isinstance(deals["UTM Term"].dtype, pd.StringDtype)


def test_empty_excel_file_is_rejected() -> None:
    contract = load_excel_contract(CONTRACT_PATH)

    with pytest.raises(ValueError, match="Excel file is empty"):
        read_excel_bytes(b"", contract)


def test_mapping_accepts_shuffled_aliases_and_ignores_extra_columns() -> None:
    contract = load_excel_contract(CONTRACT_PATH)
    mapping = load_field_mapping(MAPPING_PATH)
    source = pd.DataFrame(
        {
            "Лишнее поле": ["ignored"],
            "сумма": [1500.5],
            "Продукт": ["Course"],
            "promo_code": ["PROMO"],
            "utm_content": ["Banner"],
            "utm_source": ["Site"],
            "Дата оплаты": ["2026-10-20 12:00:00"],
            "Телефон": ["79991234567"],
            "Дата создания": ["2026-10-19 10:00:00"],
            "Ответственный": ["Manager"],
            "Воронка": ["Общая"],
            "Контакт: ID": [501],
            "ID": [101],
        }
    )
    content = BytesIO()
    with pd.ExcelWriter(content, engine="openpyxl") as writer:
        source.to_excel(writer, sheet_name="DEAL", index=False)

    result = read_mapped_excel_bytes(content.getvalue(), contract, mapping)["CRM_DEALS"]

    assert result.columns.tolist() == [
        field.canonical_name for field in mapping.dataset.fields
    ]
    assert result.loc[0, "deal_id"] == 101
    assert result.loc[0, "phone_number"] == "79991234567"
    assert result.loc[0, "amount"] == 1500.5
    assert "Лишнее поле" not in result.columns


def test_mapping_rejects_missing_required_field() -> None:
    contract = load_excel_contract(CONTRACT_PATH)
    mapping = load_field_mapping(MAPPING_PATH)
    source = pd.DataFrame({"ID": [101]})
    content = BytesIO()
    with pd.ExcelWriter(content, engine="openpyxl") as writer:
        source.to_excel(writer, sheet_name="DEAL", index=False)

    with pytest.raises(ValueError, match="missing required fields"):
        read_mapped_excel_bytes(content.getvalue(), contract, mapping)
