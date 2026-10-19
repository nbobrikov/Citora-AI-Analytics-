from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from snowflake.snowpark import Session

try:
    from citora_ai_analytic.config import load_excel_contract_from_import
    from citora_ai_analytic.excel import read_excel_from_stage
    from citora_ai_analytic.loader import replace_raw_tables
except ModuleNotFoundError as error:
    if error.name != "citora_ai_analytic":
        raise
    # Snowflake places individually imported Git files in one flat directory.
    from excel import read_excel_from_stage
    from loader import replace_raw_tables

    from config import load_excel_contract_from_import


def run(
    session: Session,
    excel_scoped_url: str,
    database: str,
    raw_schema: str,
) -> dict[str, Any]:
    """Validate a staged Excel workbook and replace its Snowflake RAW tables."""
    started_at = datetime.now(UTC)

    contract = load_excel_contract_from_import()
    frames = read_excel_from_stage(excel_scoped_url, contract)
    tables = replace_raw_tables(
        session=session,
        frames=frames,
        contract=contract,
        database=database,
        schema=raw_schema,
    )

    finished_at = datetime.now(UTC)
    return {
        "status": "success",
        "workbook": contract.workbook.id,
        "tables": tables,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
    }
