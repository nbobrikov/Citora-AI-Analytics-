from datetime import UTC, datetime

import pandas as pd

from citora_ai_analytic.loader import METADATA_COLUMNS, _add_load_metadata


def test_load_metadata_identifies_batch_source_and_excel_rows() -> None:
    frame = pd.DataFrame({"ID": [101, 102], "Name": ["First", "Second"]})
    loaded_at = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)

    result = _add_load_metadata(
        frame,
        load_id="test-load-id",
        loaded_at=loaded_at,
        source_file="source_db_2026_10_20.xlsx",
        header_row=1,
    )

    assert list(result.columns[-5:]) == METADATA_COLUMNS
    assert result["_LOAD_ID"].tolist() == ["test-load-id", "test-load-id"]
    assert result["_LOADED_AT"].tolist() == [loaded_at, loaded_at]
    assert result["_SOURCE_FILE"].tolist() == [
        "source_db_2026_10_20.xlsx",
        "source_db_2026_10_20.xlsx",
    ]
    assert result["_SOURCE_ROW_NUMBER"].tolist() == [2, 3]
    assert result["_ROW_HASH"].str.fullmatch(r"[0-9a-f]{16}").all()
    assert frame.columns.tolist() == ["ID", "Name"]


def test_row_hash_changes_when_source_data_changes() -> None:
    loaded_at = datetime(2026, 10, 20, tzinfo=UTC)
    original = pd.DataFrame({"ID": [101], "Value": ["old"]})
    changed = pd.DataFrame({"ID": [101], "Value": ["new"]})

    original_result = _add_load_metadata(
        original, "load-1", loaded_at, "source.xlsx", header_row=1
    )
    changed_result = _add_load_metadata(
        changed, "load-2", loaded_at, "source.xlsx", header_row=1
    )

    assert original_result.loc[0, "_ROW_HASH"] != changed_result.loc[0, "_ROW_HASH"]
