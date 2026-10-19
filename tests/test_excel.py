from pathlib import Path

import pandas as pd
import pytest

from citora_ai_analytic.config import load_excel_contract
from citora_ai_analytic.excel import read_excel_bytes

PROJECT_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PROJECT_ROOT / "config" / "excel" / "source_db.yml"
SOURCE_EXCEL_PATH = PROJECT_ROOT.parent / "Исходные данные" / "source_db.xlsx"


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
