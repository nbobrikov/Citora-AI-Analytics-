from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[1]
METRICS_PATH = PROJECT_ROOT / "config" / "metrics" / "analytics_metrics.yml"


def test_leads_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["catalog"]["dataset"] == {
        "database": "CITORA",
        "schema": "ANALYTICS",
        "table": "FCT_APPLICATION_SALES",
        "grain": "Одна связка заявки и продажи, включая несвязанные заявки и продажи.",
    }

    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    leads = metrics["leads"]

    assert leads["type"] == "count_distinct"
    assert leads["expression"] == "phone_number"
    assert leads["time_dimension"] == "application_created_at"
    assert leads["additivity"] == "non_additive"
    assert leads["dimensions"] == ["final_source", "final_segment", "manager"]
    assert leads["filters"] == ["application_id is not null"]


def test_sales_count_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    sales = metrics["sales_count"]

    assert sales["type"] == "count"
    assert sales["expression"] == "sale_id"
    assert sales["time_dimension"] == "paid_at"
    assert sales["additivity"] == "additive"
    assert sales["dimensions"] == ["final_source", "final_segment", "manager"]
    assert sales["filters"] == ["sale_id is not null"]
