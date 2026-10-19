from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ColumnType = Literal["string", "integer", "decimal", "boolean", "date", "timestamp"]


class ColumnConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: ColumnType
    nullable: bool
    description: str = Field(min_length=1)


class SheetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    header_row: int = Field(ge=1)
    target_table: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    columns: list[ColumnConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_columns(self) -> SheetConfig:
        names = [column.name for column in self.columns]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate columns: {duplicates}")
        return self


class WorkbookConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    file_name: str = Field(pattern=r"^.+\.xlsx?$")
    sheets: list[SheetConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_sheets_and_tables(self) -> WorkbookConfig:
        sheet_names = [sheet.name for sheet in self.sheets]
        table_names = [sheet.target_table for sheet in self.sheets]

        duplicate_sheets = sorted(
            {name for name in sheet_names if sheet_names.count(name) > 1}
        )
        duplicate_tables = sorted(
            {name for name in table_names if table_names.count(name) > 1}
        )
        if duplicate_sheets:
            raise ValueError(f"duplicate sheets: {duplicate_sheets}")
        if duplicate_tables:
            raise ValueError(f"duplicate target tables: {duplicate_tables}")
        return self


class ExcelContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    workbook: WorkbookConfig


def parse_excel_contract(content: str) -> ExcelContract:
    """Parse and validate an Excel contract from YAML text."""
    payload = yaml.safe_load(content)

    if not isinstance(payload, dict):
        raise ValueError("Excel contract must contain a YAML mapping")

    return ExcelContract.model_validate(payload)


def load_excel_contract(path: str | Path) -> ExcelContract:
    """Read and validate a local Excel YAML contract.

    This entry point is intended for local development and automated tests.
    Production procedures should use ``load_excel_contract_from_stage``.
    """
    contract_path = Path(path)
    if not contract_path.is_file():
        raise FileNotFoundError(f"Excel contract not found: {contract_path}")

    with contract_path.open(encoding="utf-8") as stream:
        return parse_excel_contract(stream.read())


def load_excel_contract_from_stage(scoped_url: str) -> ExcelContract:
    """Read and validate a YAML contract from a Snowflake scoped file URL."""
    if not scoped_url.startswith("https://"):
        raise ValueError(
            "Contract location must be a scoped URL created by BUILD_SCOPED_FILE_URL"
        )

    # The lazy import keeps local contract validation independent from Snowpark.
    from snowflake.snowpark.files import SnowflakeFile

    with SnowflakeFile.open(scoped_url, "r") as stream:
        content = stream.read()

    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return parse_excel_contract(content)
