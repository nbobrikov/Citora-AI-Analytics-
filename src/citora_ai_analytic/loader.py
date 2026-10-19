from __future__ import annotations

import re
from typing import Any

import pandas as pd
from snowflake.snowpark import Session

try:
    from citora_ai_analytic.config import ExcelContract
except ModuleNotFoundError as error:
    if error.name != "citora_ai_analytic":
        raise
    from config import ExcelContract

IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def replace_raw_tables(
    session: Session,
    frames: dict[str, pd.DataFrame],
    contract: ExcelContract,
    database: str,
    schema: str,
) -> list[dict[str, Any]]:
    """Replace Snowflake RAW tables with validated Excel data."""
    database = _validate_identifier(database, "database")
    schema = _validate_identifier(schema, "schema")

    expected_tables = {sheet.target_table for sheet in contract.workbook.sheets}
    actual_tables = set(frames)
    if actual_tables != expected_tables:
        raise ValueError(
            "Loaded frames do not match the YAML contract. "
            f"Missing tables: {sorted(expected_tables - actual_tables)}; "
            f"unexpected tables: {sorted(actual_tables - expected_tables)}"
        )

    results: list[dict[str, Any]] = []
    for sheet in contract.workbook.sheets:
        table = _validate_identifier(sheet.target_table, "table")
        frame = frames[table]

        snowpark_frame = session.write_pandas(
            frame,
            table_name=table,
            database=database,
            schema=schema,
            auto_create_table=True,
            overwrite=True,
            quote_identifiers=True,
            use_logical_type=True,
        )

        results.append(
            {
                "sheet": sheet.name,
                "table": f"{database}.{schema}.{table}",
                "rows_loaded": len(frame),
                "columns_loaded": len(frame.columns),
                "snowflake_columns": snowpark_frame.columns,
                "status": "loaded",
            }
        )

    return results


def _validate_identifier(value: str, kind: str) -> str:
    normalized = value.strip().upper()
    if not IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Invalid Snowflake {kind} identifier {value!r}. "
            "Use uppercase letters, numbers, and underscores; start with a letter."
        )
    return normalized
