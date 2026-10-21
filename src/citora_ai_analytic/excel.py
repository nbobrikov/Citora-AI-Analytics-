from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any

import pandas as pd

try:
    from citora_ai_analytic.config import (
        ColumnConfig,
        ExcelContract,
        FieldMappingContract,
        SheetConfig,
    )
except ModuleNotFoundError as error:
    if error.name != "citora_ai_analytic":
        raise
    from config import ColumnConfig, ExcelContract, FieldMappingContract, SheetConfig

MAX_EXCEL_BYTES = 100 * 1024 * 1024


def read_excel_from_stage(
    scoped_url: str,
    contract: ExcelContract,
    mapping: FieldMappingContract,
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

    return (
        read_mapped_excel_bytes(content, contract, mapping),
        hashlib.sha256(content).hexdigest(),
    )


def read_mapped_excel_bytes(
    content: bytes,
    contract: ExcelContract,
    mapping: FieldMappingContract,
) -> dict[str, pd.DataFrame]:
    """Read Excel bytes and normalize source columns to canonical field names."""
    if not content:
        raise ValueError("Excel file is empty")
    if len(contract.workbook.sheets) != 1:
        raise ValueError("A field mapping currently supports exactly one Excel sheet")

    sheet = contract.workbook.sheets[0]
    if mapping.dataset.source_table != sheet.target_table:
        raise ValueError(
            f"Mapping table {mapping.dataset.source_table!r} does not match "
            f"contract table {sheet.target_table!r}"
        )

    with pd.ExcelFile(BytesIO(content), engine="openpyxl") as workbook:
        if sheet.name not in workbook.sheet_names:
            raise ValueError(f"Excel workbook is missing sheets: {[sheet.name]}")
        source = pd.read_excel(
            workbook,
            sheet_name=sheet.name,
            header=sheet.header_row - 1,
            dtype=object,
        )

    normalized_columns: dict[str, list[str]] = {}
    for column in source.columns:
        normalized_columns.setdefault(_normalize_column_name(column), []).append(column)

    result = pd.DataFrame(index=source.index)
    missing: list[str] = []
    for field in mapping.dataset.fields:
        matches: list[str] = []
        for source_name in field.source_names:
            matches.extend(normalized_columns.get(_normalize_column_name(source_name), []))
        matches = list(dict.fromkeys(matches))

        if len(matches) > 1:
            raise ValueError(
                f"Multiple Excel columns match canonical field {field.canonical_name!r}: "
                f"{matches}"
            )
        if not matches:
            if field.required:
                missing.append(
                    f"{field.canonical_name} ({' | '.join(field.source_names)})"
                )
            else:
                result[field.canonical_name] = pd.NA
            continue

        column = ColumnConfig(
            name=field.canonical_name,
            type=field.type,
            nullable=field.nullable,
            description=field.description,
        )
        result[field.canonical_name] = _cast_column(
            source[matches[0]], column, sheet.name, sheet.header_row
        )

    if missing:
        raise ValueError(f"Excel workbook is missing required fields: {missing}")
    return {sheet.target_table: result}


def _normalize_column_name(value: object) -> str:
    return str(value).strip().casefold()


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
