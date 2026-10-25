from __future__ import annotations

import sys
from pathlib import Path

from snowflake.snowpark import Session

SEMANTIC_SCHEMA = "CITORA.ANALYTICS"
SEMANTIC_YAML_FILE = "citora_analytics_semantic_view.yml"


def run(session: Session) -> str:
    """Validate and deploy the Citora Snowflake semantic view from YAML."""
    import_directory = sys._xoptions.get("snowflake_import_directory")
    if not import_directory:
        raise RuntimeError("Snowflake import directory is not available")

    yaml_path = Path(import_directory) / SEMANTIC_YAML_FILE
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Imported semantic YAML not found: {SEMANTIC_YAML_FILE}")

    yaml_specification = yaml_path.read_text(encoding="utf-8")

    session.call(
        "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML",
        SEMANTIC_SCHEMA,
        yaml_specification,
        True,
        True,
    )
    result = session.call(
        "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML",
        SEMANTIC_SCHEMA,
        yaml_specification,
        False,
        True,
    )
    return str(result)
