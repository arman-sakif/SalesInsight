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


# --- Period and region filters -------------------------------------------
#
# The point of these is not that the filtered call returns rows -- it is that
# it returns *different* rows. Four of these tools used to ignore `period`
# entirely while the dashboard rendered a Period slicer above them, so a test
# that only asserted "rows came back" would have passed against the bug.

def _revenue(rows: list[dict], key: str = "total_revenue") -> float:
    return float(sum(row[key] for row in rows if row[key] is not None))


def test_query_metric_period_narrows_the_value():
    all_time = query_metric("total_revenue")["value"]
    year = query_metric("total_revenue", "2016")["value"]
    assert year is not None
    assert 0 < year < all_time


def test_query_metric_region_filter_partitions_the_total():
    """The four regions must sum back to the unfiltered total."""
    total = float(query_metric("total_revenue")["value"])
    parts = sum(
        float(query_metric("total_revenue", regions=[region])["value"])
        for region in sorted(REGIONS)
    )
    assert parts == pytest.approx(total, rel=1e-6)


def test_query_metric_empty_region_list_means_all_regions():
    assert query_metric("total_revenue", regions=[])["value"] == query_metric("total_revenue")["value"]


def test_rfm_segments_respect_period():
    all_time = _revenue(get_rfm_segments())
    year = _revenue(get_rfm_segments("2016"))
    assert 0 < year < all_time


def test_rfm_segments_respect_regions():
    west = _revenue(get_rfm_segments(regions=["West"]))
    assert 0 < west < _revenue(get_rfm_segments())


def test_product_performance_respects_period():
    all_time = _revenue(get_product_performance(n=10))
    year = _revenue(get_product_performance(n=10, period="2016"))
    assert 0 < year < all_time


def test_product_performance_filters_by_sub_category():
    rows = get_product_performance(n=10, sub_categories=["Chairs"])
    assert rows
    assert {row["sub_category"] for row in rows} == {"Chairs"}


def test_product_performance_filters_by_region():
    rows = get_product_performance(n=5, regions=["West"])
    assert rows
    assert _revenue(rows) < _revenue(get_product_performance(n=5))


def test_category_breakdown_respects_period():
    all_time = _revenue(get_category_breakdown())
    year = _revenue(get_category_breakdown("2016"))
    assert 0 < year < all_time


def test_category_breakdown_filters_by_category():
    rows = get_category_breakdown(categories=["Technology"])
    assert rows
    assert {row["category"] for row in rows} == {"Technology"}


def test_discount_impact_respects_period():
    all_time = _revenue(get_discount_impact())
    year = _revenue(get_discount_impact("2016"))
    assert 0 < year < all_time


def test_discount_impact_category_filter_joins_dim_product():
    """The category filter is the only reason this query joins dim_product,
    so it is the one path where the join is built conditionally."""
    rows = get_discount_impact(categories=["Technology"])
    assert rows
    assert _revenue(rows) < _revenue(get_discount_impact())


def test_top_customers_respects_segments():
    rows = get_top_customers(n=10, segments=["Champions"])
    assert rows
    assert {row["rfm_segment"] for row in rows} == {"Champions"}


def test_top_customers_respects_period_and_region():
    all_time = _revenue(get_top_customers(n=10))
    narrowed = _revenue(get_top_customers(n=10, period="2016", regions=["West"]))
    assert 0 < narrowed < all_time


def test_revenue_by_region_can_be_restricted_to_a_subset():
    rows = revenue_by_region(regions=["West", "South"])
    assert {row["region"] for row in rows} == {"West", "South"}
