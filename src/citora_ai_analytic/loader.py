from __future__ import annotations

import hashlib
import re
from datetime import datetime
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


METADATA_COLUMNS = [
    "_LOAD_ID",
    "_LOADED_AT",
    "_SOURCE_FILE",
    "_SOURCE_ROW_NUMBER",
    "_ROW_HASH",
]


def append_raw_tables(
    session: Session,
    frames: dict[str, pd.DataFrame],
    contract: ExcelContract,
    database: str,
    schema: str,
    load_id: str,
    loaded_at: datetime,
    source_file: str,
    file_hash: str,
    uploaded_by: str,
) -> list[dict[str, Any]]:
    """Append one immutable, traceable Excel batch to Snowflake RAW tables."""
    database = _validate_identifier(database, "database")
    schema = _validate_identifier(schema, "schema")
    _reject_duplicate_file(session, database, schema, file_hash)

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
        frame = _add_load_metadata(
            hash_sensitive_columns(frames[table]),
            load_id=load_id,
            loaded_at=loaded_at,
            source_file=source_file,
            header_row=sheet.header_row,
        )

        snowpark_frame = session.write_pandas(
            frame,
            table_name=table,
            database=database,
            schema=schema,
            auto_create_table=True,
            overwrite=False,
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

    total_rows = sum(item["rows_loaded"] for item in results)
    period_values = []
    for frame in frames.values():
        for column in ("created_at", "paid_at"):
            if column in frame.columns:
                period_values.append(pd.to_datetime(frame[column], errors="coerce"))
    valid_period_values = (
        pd.concat(period_values).dropna()
        if period_values
        else pd.Series(dtype="datetime64[ns]")
    )
    period_start = valid_period_values.min().date() if not valid_period_values.empty else None
    period_end = valid_period_values.max().date() if not valid_period_values.empty else None
    session.sql(
        f"""
        INSERT INTO {database}.{schema}.LOAD_HISTORY (
            LOAD_ID, SOURCE_FILE, FILE_HASH, STARTED_AT, FINISHED_AT,
            STATUS, ROWS_LOADED, ERROR_MESSAGE, UPLOADED_BY,
            DATA_PERIOD_START, DATA_PERIOD_END, DBT_STATUS
        )
        SELECT ?, ?, ?, ?, CURRENT_TIMESTAMP(), 'SUCCESS', ?, NULL, ?, ?, ?, 'PENDING'
        """,
        params=[
            load_id,
            source_file,
            file_hash,
            loaded_at,
            total_rows,
            uploaded_by,
            period_start,
            period_end,
        ],
    ).collect()
    _queue_recalculation(
        session=session,
        database=database,
        schema=schema,
        tables=sorted(expected_tables),
        recalculation_id=load_id,
        load_id=load_id,
        uploaded_by=uploaded_by,
        period_start=period_start,
        period_end=period_end,
    )
    return results


def _queue_recalculation(
    session: Session,
    database: str,
    schema: str,
    tables: list[str],
    recalculation_id: str,
    load_id: str,
    uploaded_by: str,
    period_start: object,
    period_end: object,
) -> None:
    session.sql(
        f"""
        INSERT INTO {database}.PLATFORM.RECALCULATION_QUEUE (
            RECALCULATION_ID, OPERATION_TYPE, LOAD_ID, REQUESTED_AT,
            REQUESTED_BY, DATE_FROM, DATE_TO, CONVERSION_PERIOD_DAYS, STATUS
        )
        SELECT ?, 'LOAD', ?, CURRENT_TIMESTAMP(), ?, ?, ?, 30, 'PENDING'
        """,
        params=[recalculation_id, load_id, uploaded_by, period_start, period_end],
    ).collect()
    for table in tables:
        validated_table = _validate_identifier(table, "table")
        session.sql(
            f"""
            INSERT INTO {database}.PLATFORM.RECALCULATION_IDENTIFIERS (
                RECALCULATION_ID, PHONE_NUMBER_HASH, CONTACT_ID_HASH, CREATED_AT
            )
            SELECT DISTINCT ?, NULLIF(TRIM("phone_number"), ''),
                   NULLIF(TRIM("contact_id"), ''), CURRENT_TIMESTAMP()
            FROM {database}.{schema}.{validated_table}
            WHERE "_LOAD_ID" = ?
              AND (NULLIF(TRIM("phone_number"), '') IS NOT NULL
                   OR NULLIF(TRIM("contact_id"), '') IS NOT NULL)
            """,
            params=[recalculation_id, load_id],
        ).collect()


def hash_sensitive_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Replace phone numbers and contact IDs with deterministic SHA-256 values."""
    result = frame.copy()
    for column in ("phone_number", "contact_id"):
        if column in result.columns:
            result[column] = result[column].map(_hash_sensitive_value).astype("string")
    return result


def _hash_sensitive_value(value: object) -> str:
    if pd.isna(value):
        canonical = "0"
    elif isinstance(value, float) and value.is_integer():
        canonical = str(int(value))
    else:
        canonical = str(value).strip().casefold() or "0"
    if re.fullmatch(r"[0-9a-f]{64}", canonical):
        return canonical
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _add_load_metadata(
    frame: pd.DataFrame,
    load_id: str,
    loaded_at: datetime,
    source_file: str,
    header_row: int,
) -> pd.DataFrame:
    result = frame.copy()
    row_hashes = pd.util.hash_pandas_object(result, index=False).map(
        lambda value: f"{value:016x}"
    )
    result["_LOAD_ID"] = load_id
    result["_LOADED_AT"] = loaded_at
    result["_SOURCE_FILE"] = source_file
    result["_SOURCE_ROW_NUMBER"] = range(header_row + 1, header_row + 1 + len(result))
    result["_ROW_HASH"] = row_hashes
    return result


def _reject_duplicate_file(
    session: Session,
    database: str,
    schema: str,
    file_hash: str,
) -> None:
    duplicate = session.sql(
        f"""
        SELECT LOAD_ID
        FROM {database}.{schema}.LOAD_HISTORY
        WHERE FILE_HASH = ? AND STATUS = 'SUCCESS'
        LIMIT 1
        """,
        params=[file_hash],
    ).collect()
    if duplicate:
        raise ValueError(
            "This Excel file was already loaded successfully "
            f"with load ID {duplicate[0][0]}"
        )


def _validate_identifier(value: str, kind: str) -> str:
    normalized = value.strip().upper()
    if not IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Invalid Snowflake {kind} identifier {value!r}. "
            "Use uppercase letters, numbers, and underscores; start with a letter."
        )
    return normalized
