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


def test_applications_count_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    applications = metrics["applications_count"]

    assert applications["type"] == "sum"
    assert applications["expression"] == "is_unique"
    assert applications["time_dimension"] == "application_created_at"
    assert applications["additivity"] == "additive"
    assert applications["dimensions"] == [
        "final_source",
        "final_segment",
        "manager",
    ]
    assert applications["filters"] == [
        "application_id is not null",
        "match_type != 'sale_without_application'",
        "manager != 'Самоток'",
    ]


def test_application_to_sale_conversion_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    conversion = metrics["application_to_sale_conversion"]

    assert conversion["type"] == "ratio"
    assert conversion["format"] == "percent"
    assert conversion["time_dimension"] == "application_created_at"
    assert conversion["additivity"] == "non_additive"
    assert conversion["conversion_window"] == {
        "parameter": "conversion_period_days",
        "default_days": 30,
    }
    assert conversion["dimensions"] == [
        "final_source",
        "final_segment",
        "manager",
    ]
    assert conversion["numerator"]["aggregation"] == "count"
    assert conversion["numerator"]["expression"] == "sale_id"
    assert conversion["denominator"]["aggregation"] == "sum"
    assert conversion["denominator"]["expression"] == "is_unique"
    assert "DIV0" in conversion["sql_template"]


def test_self_flow_sales_share_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    self_flow_share = metrics["self_flow_sales_share"]

    assert self_flow_share["type"] == "ratio"
    assert self_flow_share["format"] == "percent"
    assert self_flow_share["time_dimension"] == "paid_at"
    assert self_flow_share["additivity"] == "non_additive"
    assert self_flow_share["dimensions"] == ["final_source", "final_segment"]
    assert self_flow_share["filters"] == ["sale_id is not null"]
    assert self_flow_share["numerator"]["filters"] == [
        "match_type = 'sale_without_application'",
        "manager = 'Самоток'",
    ]
    assert self_flow_share["denominator"]["expression"] == "sale_id"
    assert "DIV0" in self_flow_share["sql_template"]
