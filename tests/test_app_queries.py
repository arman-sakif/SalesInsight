"""Tests for the app's presentation-shaped queries.

Like the tool tests, these run against whatever ``mcp_server.db`` resolves --
the DuckDB warehouse locally and in CI, the committed Parquet marts otherwise.
That matters more here than anywhere else: these queries were written after the
five-mart deployment limit was already in place, and referencing a staging or
intermediate model would pass locally and fail only on Streamlit Cloud.
"""
import pytest

from app.queries import (
    ERA_HISTORICAL,
    ERA_RECENT,
    available_periods,
    discount_margin_bins,
    filter_values,
    previous_period,
    product_pareto,
    revenue_by_state,
    revenue_timeseries,
    rfm_matrix,
    sub_categories,
)

# The only tables that exist in the deployed app.
EXPORTED_MARTS = {"fact_sales", "dim_customer", "dim_product", "dim_date", "dim_region"}


def test_available_periods_always_offers_all_time_first():
    options = available_periods()
    assert list(options)[0] == "All time"
    assert options["All time"] == "all_time"


def test_available_periods_only_offers_periods_with_data():
    """The whole point of deriving the list: no option may return zero rows."""
    from mcp_server.tools.metrics import query_metric

    for label, period in available_periods().items():
        value = query_metric("total_revenue", period)["value"]
        assert value is not None and value > 0, f"'{label}' returns no data"


def test_available_periods_includes_the_years_in_the_data():
    options = available_periods()
    assert "2016" in options and options["2016"] == "2016"


def test_filter_values_returns_the_four_regions():
    assert set(filter_values("region")) == {"West", "East", "Central", "South"}


def test_filter_values_rejects_columns_outside_the_allowlist():
    """The column name is interpolated into SQL, so the allowlist is the guard."""
    with pytest.raises(ValueError):
        filter_values("state; DROP TABLE fact_sales")


def test_sub_categories_narrow_to_their_category():
    furniture = set(sub_categories(["Furniture"]))
    assert furniture == {"Bookcases", "Chairs", "Furnishings", "Tables"}
    assert furniture < set(sub_categories())


def test_daily_timeseries_is_zero_filled_and_contiguous():
    """A day with no orders must still produce a row, or the rolling average
    silently spans a different number of calendar days at each step."""
    rows = revenue_timeseries("day", era=ERA_RECENT)
    assert len(rows) > 1
    dates = [row["period_start"] for row in rows]
    assert dates == sorted(dates)
    span = (dates[-1] - dates[0]).days + 1
    assert len(rows) == span
    assert all(row["revenue"] is not None for row in rows)


def test_rolling_average_is_present_and_smoother_than_the_raw_series():
    rows = revenue_timeseries("day", era=ERA_RECENT, rolling_window=7)
    assert all("revenue_rolling" in row for row in rows)
    # Compare only where the window is full, so the warm-up rows don't count.
    settled = rows[7:]
    if len(settled) > 2:
        raw = [float(r["revenue"]) for r in settled]
        smooth = [float(r["revenue_rolling"]) for r in settled]
        assert _spread(smooth) < _spread(raw)


def test_rolling_window_can_be_switched_off():
    rows = revenue_timeseries("month", era=ERA_HISTORICAL, rolling_window=0)
    assert rows and "revenue_rolling" not in rows[0]


def test_monthly_historical_series_covers_the_kaggle_years():
    rows = revenue_timeseries("month", era=ERA_HISTORICAL, rolling_window=0)
    years = {row["period_start"].year for row in rows}
    assert years == {2014, 2015, 2016, 2017}


def test_eras_partition_the_revenue():
    """historical + recent must add back to the unfiltered total, or the
    two-panel Trends page is quietly dropping rows."""
    both = _total(revenue_timeseries("month", rolling_window=0))
    historical = _total(revenue_timeseries("month", era=ERA_HISTORICAL, rolling_window=0))
    recent = _total(revenue_timeseries("month", era=ERA_RECENT, rolling_window=0))
    assert historical + recent == pytest.approx(both, rel=1e-6)
    assert historical > 0 and recent > 0


def test_timeseries_rejects_an_unknown_grain():
    with pytest.raises(ValueError):
        revenue_timeseries("fortnight")


def test_timeseries_respects_region_filter():
    west = _total(revenue_timeseries("month", regions=["West"], rolling_window=0))
    assert 0 < west < _total(revenue_timeseries("month", rolling_window=0))


def test_revenue_by_state_is_revenue_sorted_and_tagged_with_a_region():
    rows = revenue_by_state()
    assert len(rows) > 40
    revenues = [float(row["revenue"]) for row in rows]
    assert revenues == sorted(revenues, reverse=True)
    assert all(row["region"] in {"West", "East", "Central", "South"} for row in rows)


def test_pareto_cumulative_share_rises_to_100_percent():
    rows = product_pareto(limit=10_000)
    shares = [float(row["cumulative_pct"]) for row in rows]
    assert shares == sorted(shares)
    assert shares[-1] == pytest.approx(100.0, abs=0.01)


def test_pareto_share_is_measured_against_the_full_catalogue():
    """Truncating to the top N must not renormalise the curve to 100%."""
    top = product_pareto(limit=10)
    assert len(top) == 10
    assert float(top[-1]["cumulative_pct"]) < 100.0


def test_discount_bins_show_margin_turning_negative():
    """The synthetic profit model makes deep discounts unprofitable; this is
    the chart's whole story, so it is worth asserting rather than captioning."""
    rows = discount_margin_bins()
    assert rows
    assert float(rows[0]["discount_pct"]) == 0.0
    assert float(rows[0]["margin_pct"]) > 0
    assert min(float(row["margin_pct"]) for row in rows) < 0


def test_every_query_only_touches_the_exported_marts():
    """Staging and intermediate models do not exist on Streamlit Cloud."""
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parent.parent / "app" / "queries.py"
    referenced = set(re.findall(r"main\.(\w+)", source.read_text(encoding="utf-8")))
    assert referenced <= EXPORTED_MARTS, f"unexported tables: {referenced - EXPORTED_MARTS}"


def _total(rows: list[dict]) -> float:
    return float(sum(row["revenue"] for row in rows))


def _spread(values: list[float]) -> float:
    """Mean absolute step between consecutive points -- a cheap jitter measure."""
    if len(values) < 2:
        return 0.0
    return sum(abs(b - a) for a, b in zip(values, values[1:])) / (len(values) - 1)


# --- Deployment fallback --------------------------------------------------

@pytest.fixture
def parquet_mode(monkeypatch):
    """Force the Parquet-backed connection the deployed app actually uses.

    Locally and in CI ``data/warehouse.db`` exists, so every other test in this
    file runs against DuckDB and would never notice a query that referenced a
    staging or intermediate model. Pointing DB_PATH at a file that does not
    exist takes the same branch Streamlit Community Cloud takes.
    """
    from mcp_server import db

    monkeypatch.setattr(db, "DB_PATH", db.ROOT_DIR / "data" / "does-not-exist.db")
    assert not db.DB_PATH.exists()
    return db


def test_parquet_fallback_is_actually_exercised(parquet_mode):
    conn = parquet_mode.get_connection()
    try:
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    finally:
        conn.close()
    assert tables == EXPORTED_MARTS


def test_every_app_query_runs_against_the_parquet_marts(parquet_mode):
    """The queries this redesign added, run the way the deployed app runs them."""
    assert available_periods()["All time"] == "all_time"
    assert set(filter_values("region")) == {"West", "East", "Central", "South"}
    assert sub_categories(["Furniture"])
    assert revenue_timeseries("day", era=ERA_RECENT)
    assert revenue_timeseries("month", era=ERA_HISTORICAL, rolling_window=0)
    assert revenue_by_state()
    assert product_pareto(limit=10)
    assert discount_margin_bins()
    assert rfm_matrix()
    assert previous_period("2016").startswith("range:")


def test_every_tool_runs_against_the_parquet_marts(parquet_mode):
    """The tool layer gained new filters; they must work in both modes too."""
    from mcp_server.tools.customers import get_rfm_segments, get_top_customers
    from mcp_server.tools.metrics import query_metric
    from mcp_server.tools.products import (
        get_category_breakdown,
        get_discount_impact,
        get_product_performance,
    )
    from mcp_server.tools.regions import revenue_by_region

    assert query_metric("total_revenue", "2016", ["West"])["value"] > 0
    assert get_top_customers(5, "2016", ["West"], ["Champions"]) is not None
    assert get_rfm_segments("2016", ["West"])
    assert revenue_by_region("2016", ["West"])
    assert get_product_performance(None, 5, "2016", ["West"], ["Chairs"]) is not None
    assert get_category_breakdown("2016", ["West"], ["Technology"])
    assert get_discount_impact("2016", ["West"], ["Technology"])
