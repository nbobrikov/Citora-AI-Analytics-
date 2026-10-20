from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any

import pandas as pd

try:
    from citora_ai_analytic.config import ColumnConfig, ExcelContract, SheetConfig
except ModuleNotFoundError as error:
    if error.name != "citora_ai_analytic":
        raise
    from config import ColumnConfig, ExcelContract, SheetConfig

MAX_EXCEL_BYTES = 100 * 1024 * 1024


def read_excel_from_stage(
    scoped_url: str,
    contract: ExcelContract,
) -> tuple[dict[str, pd.DataFrame], str]:
    """Read and validate an Excel workbook from a Snowflake scoped file URL."""
    if not scoped_url.startswith("https://"):
        raise ValueError("Excel location must be a scoped URL created by BUILD_SCOPED_FILE_URL")

    # The lazy import allows local unit tests to run without a Snowflake session.
    from snowflake.snowpark.files import SnowflakeFile

    with SnowflakeFile.open(scoped_url, "rb") as stream:
        content = stream.read(MAX_EXCEL_BYTES + 1)

    if len(content) > MAX_EXCEL_BYTES:
        raise ValueError(f"Excel file exceeds the {MAX_EXCEL_BYTES} byte limit")

    return read_excel_bytes(content, contract), hashlib.sha256(content).hexdigest()


def read_excel_bytes(
    content: bytes,
    contract: ExcelContract,
) -> dict[str, pd.DataFrame]:
    """Read Excel bytes and return validated frames keyed by target table."""
    if not content:
        raise ValueError("Excel file is empty")

    source = BytesIO(content)
    with pd.ExcelFile(source, engine="openpyxl") as workbook:
        actual_sheets = set(workbook.sheet_names)
        required_sheets = {sheet.name for sheet in contract.workbook.sheets}
        missing_sheets = sorted(required_sheets - actual_sheets)
        if missing_sheets:
            raise ValueError(f"Excel workbook is missing sheets: {missing_sheets}")

        result: dict[str, pd.DataFrame] = {}
        for sheet in contract.workbook.sheets:
            frame = pd.read_excel(
                workbook,
                sheet_name=sheet.name,
                header=sheet.header_row - 1,
                dtype=object,
            )
            result[sheet.target_table] = validate_and_cast_sheet(frame, sheet)
    return result


def validate_and_cast_sheet(frame: pd.DataFrame, sheet: SheetConfig) -> pd.DataFrame:
    """Validate a worksheet against its contract and cast its columns."""
    actual_columns = list(frame.columns)
    expected_columns = [column.name for column in sheet.columns]

    if actual_columns != expected_columns:
        missing = [name for name in expected_columns if name not in actual_columns]
        unexpected = [name for name in actual_columns if name not in expected_columns]
        raise ValueError(
            f"Sheet {sheet.name!r} does not match the YAML contract. "
            f"Missing: {missing}; unexpected: {unexpected}; "
            f"column order matches: {set(actual_columns) == set(expected_columns)}"
        )

    result = frame.copy()
    for column in sheet.columns:
        result[column.name] = _cast_column(
            result[column.name], column, sheet.name, sheet.header_row
        )
        if not column.nullable and result[column.name].isna().any():
            rows = _excel_row_numbers(result[column.name].isna(), sheet.header_row)
            raise ValueError(
                f"Sheet {sheet.name!r}, column {column.name!r} contains null values "
                f"in Excel rows {rows}"
            )
    return result


def _cast_column(
    values: pd.Series,
    column: ColumnConfig,
    sheet_name: str,
    header_row: int,
) -> pd.Series:
    if column.type == "string":
        return values.map(_to_string).astype("string")

    if column.type in {"date", "timestamp"}:
        converted = pd.to_datetime(values, errors="coerce")
        _raise_for_invalid_values(values, converted, column, sheet_name, header_row)
        if column.type == "date":
            return converted.dt.date
        return converted

    if column.type in {"integer", "decimal"}:
        converted = pd.to_numeric(values, errors="coerce")
        _raise_for_invalid_values(values, converted, column, sheet_name, header_row)
        if column.type == "integer":
            fractional = converted.notna() & (converted % 1 != 0)
            if fractional.any():
                rows = _excel_row_numbers(fractional, header_row)
                raise ValueError(
                    f"Sheet {sheet_name!r}, column {column.name!r} contains "
                    f"non-integer values in data rows {rows}"
                )
            return converted.astype("Int64")
        return converted.astype("Float64")

    if column.type == "boolean":
        return _to_boolean(values, column, sheet_name, header_row)

    raise ValueError(f"Unsupported type {column.type!r} for column {column.name!r}")


def _to_string(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=" ")
    return str(value)


def _to_boolean(
    values: pd.Series,
    column: ColumnConfig,
    sheet_name: str,
    header_row: int,
) -> pd.Series:
    mapping = {
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
    }

    def convert(value: Any) -> Any:
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (bool, int, float)) and value in (0, 1):
            return bool(value)
        key = value.strip().lower() if isinstance(value, str) else value
        return mapping.get(key, pd.NA)

    converted = values.map(convert).astype("boolean")
    _raise_for_invalid_values(values, converted, column, sheet_name, header_row)
    return converted


def _raise_for_invalid_values(
    original: pd.Series,
    converted: pd.Series,
    column: ColumnConfig,
    sheet_name: str,
    header_row: int,
) -> None:
    invalid = original.notna() & converted.isna()
    if invalid.any():
        rows = _excel_row_numbers(invalid, header_row)
        raise ValueError(
            f"Sheet {sheet_name!r}, column {column.name!r} contains values that "
            f"cannot be converted to {column.type!r} in data rows {rows}"
        )


def _excel_row_numbers(mask: pd.Series, header_row: int, limit: int = 10) -> list[int]:
    return [int(index) + header_row + 1 for index in mask[mask].index[:limit]]
