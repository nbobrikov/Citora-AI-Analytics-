from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from snowflake.snowpark import Session

try:
    from citora_ai_analytic.config import load_excel_contract_from_import
    from citora_ai_analytic.excel import read_excel_from_stage
    from citora_ai_analytic.loader import append_raw_tables
except ModuleNotFoundError as error:
    if error.name != "citora_ai_analytic":
        raise
    # Snowflake places individually imported Git files in one flat directory.
    from excel import read_excel_from_stage
    from loader import append_raw_tables

    from config import load_excel_contract_from_import


def run(
    session: Session,
    excel_scoped_url: str,
    source_file: str,
    database: str,
    raw_schema: str,
) -> dict[str, Any]:
    """Validate a staged Excel workbook and append an immutable RAW batch."""
    started_at = datetime.now(UTC)
    load_id = str(uuid4())

    contract = load_excel_contract_from_import()
    frames, file_hash = read_excel_from_stage(excel_scoped_url, contract)
    tables = append_raw_tables(
        session=session,
        frames=frames,
        contract=contract,
        database=database,
        schema=raw_schema,
        load_id=load_id,
        loaded_at=started_at,
        source_file=source_file,
        file_hash=file_hash,
    )

    finished_at = datetime.now(UTC)
    return {
        "status": "success",
        "load_id": load_id,
        "source_file": source_file,
        "file_hash": file_hash,
        "workbook": contract.workbook.id,
        "tables": tables,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
    }
