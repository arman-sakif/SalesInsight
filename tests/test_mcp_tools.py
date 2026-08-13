"""Smoke tests for the MCP tool layer.

These call the same functions the MCP server registers and the Streamlit app
imports, against whatever source ``mcp_server.db`` resolves: the DuckDB
warehouse when it exists (locally and in CI, after dbt build) or the committed
Parquet marts otherwise. That makes them a check on the deployment fallback
the hosted app depends on as well as on the queries themselves.
"""
import pytest

from mcp_server.tools.customers import get_rfm_segments, get_top_customers
from mcp_server.tools.metrics import METRIC_DEFINITIONS, explain_metric, query_metric
from mcp_server.tools.products import (
    get_category_breakdown,
    get_discount_impact,
    get_product_performance,
)
from mcp_server.tools.regions import revenue_by_region

CATEGORIES = {"Furniture", "Office Supplies", "Technology"}
REGIONS = {"West", "East", "Central", "South"}


@pytest.mark.parametrize("metric", sorted(METRIC_DEFINITIONS))
def test_query_metric_returns_a_positive_value(metric):
    result = query_metric(metric)
    assert result["metric"] == metric
    assert result["period"] == "All time"
    assert result["value"] is not None and result["value"] > 0


def test_query_metric_rejects_unknown_metric():
    result = query_metric("total_vibes")
    assert "error" in result
    assert "total_revenue" in result["available_metrics"]


def test_explain_metric_documents_the_sql():
    result = explain_metric("gross_profit_margin")
    assert result["sql_expression"] == METRIC_DEFINITIONS["gross_profit_margin"]["sql"]
    assert result["description"]


def test_top_customers_respects_n_and_is_revenue_sorted():
    rows = get_top_customers(n=5)
    assert len(rows) == 5
    revenues = [row["total_revenue"] for row in rows]
    assert revenues == sorted(revenues, reverse=True)
    assert all(row["customer_name"] and row["rfm_segment"] for row in rows)


def test_top_customers_caps_n_at_50():
    assert len(get_top_customers(n=999)) <= 50


def test_rfm_segments_use_the_known_labels():
    rows = get_rfm_segments()
    labels = {row["rfm_segment"] for row in rows}
    assert labels
    assert labels <= {"Champions", "Loyal Customers", "Potential Loyalists", "At Risk", "Lost"}
    assert all(row["customer_count"] > 0 for row in rows)


def test_revenue_by_region_covers_all_four_regions():
    rows = revenue_by_region()
    assert {row["region"] for row in rows} == REGIONS
    assert all(row["total_revenue"] > 0 for row in rows)


def test_product_performance_filters_by_category_and_reports_discount():
    rows = get_product_performance(category="Technology", n=5)
    assert rows
    assert {row["category"] for row in rows} == {"Technology"}
    assert all(0 <= row["avg_discount_pct"] <= 100 for row in rows)


def test_category_breakdown_covers_the_three_categories():
    rows = get_category_breakdown()
    assert {row["category"] for row in rows} == CATEGORIES
    assert all(row["avg_discount_pct"] is not None for row in rows)


def test_discount_impact_margin_falls_as_discount_rises():
    """The whole point of the discount-aware profit model: deeper discount
    bands must show progressively lower margins."""
    rows = get_discount_impact()
    bands = [row["discount_band"] for row in rows]
    assert bands == [b for b in ["0%", "1-10%", "11-20%", "21-30%", "30%+"] if b in bands]

    margins = [row["avg_margin_pct"] for row in rows]
    assert margins == sorted(margins, reverse=True)
