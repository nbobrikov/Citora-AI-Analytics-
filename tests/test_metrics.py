from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[1]
METRICS_PATH = PROJECT_ROOT / "config" / "metrics" / "analytics_metrics.yml"


def test_leads_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["catalog"]["dataset"]["database"] == "CITORA"
    assert payload["catalog"]["dataset"]["schema"] == "ANALYTICS"
    assert payload["catalog"]["dataset"]["table"] == "FCT_REPORTING_METRICS"

    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    leads = metrics["leads"]

    assert leads["type"] == "count_distinct"
    assert leads["expression"] == "phone_number"
    assert leads["time_dimension"] == "report_date"
    assert leads["additivity"] == "non_additive"
    assert leads["dimensions"] == ["final_source", "final_segment", "manager"]
    assert leads["filters"] == ["record_type = 'APPLICATION'"]


def test_sales_count_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    sales = metrics["sales_count"]

    assert sales["type"] == "count"
    assert sales["expression"] == "sale_id"
    assert sales["time_dimension"] == "report_date"
    assert sales["additivity"] == "additive"
    assert sales["dimensions"] == ["final_source", "final_segment", "manager"]
    assert sales["filters"] == ["record_type = 'SALE'"]


def test_applications_count_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    applications = metrics["applications_count"]

    assert applications["type"] == "sum"
    assert applications["expression"] == "reporting_event_id"
    assert applications["time_dimension"] == "report_date"
    assert applications["additivity"] == "additive"
    assert applications["dimensions"] == [
        "final_source",
        "final_segment",
        "manager",
    ]
    assert applications["filters"] == [
        "record_type = 'APPLICATION'",
        "manager != 'Самоток'",
    ]


def test_application_to_sale_conversion_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    conversion = metrics["application_to_sale_conversion"]

    assert conversion["type"] == "ratio"
    assert conversion["format"] == "percent"
    assert conversion["time_dimension"] == "report_date"
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
    assert conversion["numerator"]["aggregation"] == "sum"
    assert conversion["numerator"]["expression"] == "matched_sales_count"
    assert conversion["denominator"]["aggregation"] == "sum"
    assert conversion["denominator"]["expression"] == "reporting_event_id"
    assert "DIV0" in conversion["sql_template"]


def test_self_flow_sales_share_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    self_flow_share = metrics["self_flow_sales_share"]

    assert self_flow_share["type"] == "ratio"
    assert self_flow_share["format"] == "percent"
    assert self_flow_share["time_dimension"] == "report_date"
    assert self_flow_share["additivity"] == "non_additive"
    assert self_flow_share["dimensions"] == ["final_source", "final_segment"]
    assert self_flow_share["filters"] == ["record_type = 'SALE'"]
    assert self_flow_share["numerator"]["filters"] == [
        "match_type = 'sale_without_application'",
        "manager = 'Самоток'",
    ]
    assert self_flow_share["denominator"]["expression"] == "sale_id"
    assert "DIV0" in self_flow_share["sql_template"]


def test_average_conversion_time_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    average_time = metrics["average_conversion_time"]

    assert average_time["type"] == "average"
    assert average_time["format"] == "decimal_days"
    assert average_time["expression"] == "conversion_period_days"
    assert average_time["time_dimension"] == "report_date"
    assert average_time["additivity"] == "non_additive"
    assert average_time["conversion_window"] == {
        "parameter": "conversion_period_days",
        "default_days": 30,
    }
    assert average_time["dimensions"] == [
        "final_source",
        "final_segment",
        "manager",
    ]
    assert average_time["filters"] == [
        "record_type = 'APPLICATION'",
        "match_type = 'matched'",
        "manager != 'Самоток'",
    ]
    assert "AVG" in average_time["sql_template"]


def test_marked_applications_share_metric_definition() -> None:
    payload = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {metric["id"]: metric for metric in payload["metrics"]}
    marked_share = metrics["marked_applications_share"]

    assert marked_share["type"] == "ratio"
    assert marked_share["format"] == "percent"
    assert marked_share["time_dimension"] == "report_date"
    assert marked_share["additivity"] == "non_additive"
    assert marked_share["dimensions"] == [
        "final_source",
        "final_segment",
        "manager",
    ]
    assert marked_share["filters"] == [
        "record_type = 'APPLICATION'",
        "manager != 'Самоток'",
    ]
    assert marked_share["numerator"]["filters"] == [
        "final_segment != 'Без разметки' or final_source != 'Без разметки'"
    ]
    assert marked_share["denominator"]["expression"] == "reporting_event_id"
    assert "DIV0" in marked_share["sql_template"]
