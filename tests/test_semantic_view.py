from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[1]
SEMANTIC_VIEW_PATH = (
    PROJECT_ROOT / "config" / "semantic" / "citora_analytics_semantic_view.yml"
)


def test_semantic_view_contains_catalog_metrics() -> None:
    semantic = yaml.safe_load(SEMANTIC_VIEW_PATH.read_text(encoding="utf-8"))
    table = semantic["tables"][0]
    metric_names = {metric["name"] for metric in table["metrics"]}

    assert semantic["name"] == "CITORA_ANALYTICS_SEMANTIC_VIEW"
    assert table["base_table"] == {
        "database": "CITORA",
        "schema": "ANALYTICS",
        "table": "FCT_APPLICATION_SALES",
    }
    assert metric_names == {
        "LEADS",
        "SALES_COUNT",
        "APPLICATIONS_COUNT",
        "APPLICATION_TO_SALE_CONVERSION",
        "SELF_FLOW_SALES_SHARE",
        "AVERAGE_CONVERSION_TIME",
        "MARKED_APPLICATIONS_SHARE",
    }


def test_semantic_view_has_separate_application_and_sale_dates() -> None:
    semantic = yaml.safe_load(SEMANTIC_VIEW_PATH.read_text(encoding="utf-8"))
    time_dimensions = {
        dimension["name"] for dimension in semantic["tables"][0]["time_dimensions"]
    }

    assert time_dimensions == {"APPLICATION_CREATED_AT", "PAID_AT"}
