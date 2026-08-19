"""Presentation-shaped queries for the Streamlit app.

The app reads business metrics through the MCP tool layer in ``mcp_server/tools``
so the dashboard, the AI tools, and Power BI can never disagree on a number.
This module is the deliberate exception: time-series and geographic *shapes*
that only a chart needs (zero-filled day spines, rolling averages, cumulative
Pareto curves). They are cuts of the same marts, not a second definition of any
metric -- revenue here is still ``SUM(sales_amount)`` over ``main.fact_sales``.

Every query obeys the deployment constraint in ``mcp_server/db.py``: only the
five exported marts exist on Streamlit Community Cloud, they must be referenced
as ``main.<table>``, and everything goes through ``run_query`` so the DuckDB
and Parquet modes behave identically.
"""
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from mcp_server.db import run_query
from mcp_server.tools._filters import (
    in_predicate,
    parse_range,
    period_predicate,
    range_period,
    where_clause,
)

# The dataset is two eras with an eight-year gap between them: the Kaggle
# Superstore history (2014-2017) and the synthetic feed the pipeline
# regenerates on each refresh. Charting them as one continuous line would draw
# eight years of flatline, so callers pick an era explicitly. `is_synthetic` on
# fact_sales is the split, which keeps this correct as the window moves.
ERA_HISTORICAL = "historical"
ERA_RECENT = "recent"

_ERA_PREDICATES = {
    ERA_HISTORICAL: "NOT is_synthetic",
    ERA_RECENT: "is_synthetic",
}


def _era_predicate(era: str | None) -> str:
    return _ERA_PREDICATES.get(era or "", "")


def available_periods() -> dict[str, str]:
    """Build the period options from the years actually present in the data.

    A fixed list offers periods that can never return rows -- 'Last year' sits
    inside the gap between the two eras for most of the calendar. Deriving the
    options means a dead option never renders, and reappears on its own once
    the data spans it.

    Returns:
        An ordered ``{label: period_argument}`` mapping for the UI.
    """
    rows = run_query(
        """
        SELECT
            COUNT(*) FILTER (WHERE order_year = YEAR(CURRENT_DATE))     AS this_year,
            COUNT(*) FILTER (WHERE order_year = YEAR(CURRENT_DATE) - 1) AS last_year,
            COUNT(*) FILTER (WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY) AS last_30,
            COUNT(*) FILTER (WHERE order_date >= CURRENT_DATE - INTERVAL 90 DAY) AS last_90
        FROM main.fact_sales
        """
    )
    counts = rows[0] if rows else {}

    options = {"All time": "all_time"}
    if counts.get("last_30"):
        options["Last 30 days"] = "last_30_days"
    # Only worth offering when it is genuinely a wider window than the 30-day
    # option -- with a short synthetic feed the two select identical rows.
    if counts.get("last_90") and counts["last_90"] != counts.get("last_30"):
        options["Last 90 days"] = "last_90_days"
    if counts.get("this_year"):
        options["This year"] = "this_year"
    if counts.get("last_year"):
        options["Last year"] = "last_year"

    years = run_query(
        "SELECT DISTINCT order_year FROM main.fact_sales ORDER BY order_year DESC"
    )
    for row in years:
        year = str(int(row["order_year"]))
        options[year] = year
    return options


def filter_values(column: str) -> list[str]:
    """Distinct values of a fact_sales column, for populating a slicer."""
    if column not in {"region", "state", "ship_mode"}:
        raise ValueError(f"Unsupported slicer column: {column}")
    rows = run_query(
        f"SELECT DISTINCT {column} AS value FROM main.fact_sales "
        f"WHERE {column} IS NOT NULL ORDER BY value"
    )
    return [row["value"] for row in rows]


def sub_categories(categories: list[str] | None = None) -> list[str]:
    """Distinct product sub-categories, optionally within given categories."""
    params: list = []
    clause = where_clause(in_predicate("category", categories, params))
    rows = run_query(
        f"SELECT DISTINCT sub_category AS value FROM main.dim_product {clause} ORDER BY value",
        params,
    )
    return [row["value"] for row in rows]


def revenue_timeseries(
    grain: str = "day",
    period: str = "all_time",
    regions: list[str] | None = None,
    era: str | None = None,
    rolling_window: int = 7,
) -> list[dict]:
    """Revenue, profit, and order counts over time, zero-filled.

    Days with no orders produce no fact rows, so a bare GROUP BY would draw a
    line that skips them and a rolling average that silently spans a different
    number of calendar days at each step. The day spine comes from ``dim_date``,
    bounded by the data actually in the selection.

    Args:
        grain: 'day' or 'month'.
        period: A period argument understood by ``period_predicate``.
        regions: Restrict to these regions.
        era: ERA_HISTORICAL, ERA_RECENT, or None for both.
        rolling_window: Periods in the trailing average (0 or 1 to skip it).

    Returns:
        Rows of ``period_start``, ``revenue``, ``profit``, ``orders``,
        ``margin_pct`` and, when requested, ``revenue_rolling``.
    """
    if grain not in {"day", "month"}:
        raise ValueError("grain must be 'day' or 'month'")

    params: list = []
    clause = where_clause(
        period_predicate(period)[0],
        _era_predicate(era),
        in_predicate("region", regions, params),
    )

    bucket = "s.date_day" if grain == "day" else "DATE_TRUNC('month', s.date_day)"
    rolling = ""
    if rolling_window and rolling_window > 1:
        rolling = f""",
            ROUND(AVG(SUM(f.sales_amount)) OVER (
                ORDER BY {bucket}
                ROWS BETWEEN {int(rolling_window) - 1} PRECEDING AND CURRENT ROW
            ), 2) AS revenue_rolling"""

    sql = f"""
        WITH filtered AS (
            SELECT order_date, sales_amount, profit, order_id
            FROM main.fact_sales
            {clause}
        ),
        bounds AS (
            SELECT MIN(order_date) AS lo, MAX(order_date) AS hi FROM filtered
        ),
        spine AS (
            SELECT d.date_day
            FROM main.dim_date d, bounds b
            WHERE d.date_day BETWEEN b.lo AND b.hi
        )
        SELECT
            {bucket}                                   AS period_start,
            ROUND(COALESCE(SUM(f.sales_amount), 0), 2) AS revenue,
            ROUND(COALESCE(SUM(f.profit), 0), 2)       AS profit,
            COUNT(DISTINCT f.order_id)                 AS orders,
            ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct{rolling}
        FROM spine s
        LEFT JOIN filtered f ON f.order_date = s.date_day
        GROUP BY {bucket}
        ORDER BY period_start
    """
    return run_query(sql, params)


def revenue_by_state(
    period: str = "all_time", regions: list[str] | None = None
) -> list[dict]:
    """Revenue, profit, and orders per US state, for the choropleth.

    ``dim_region`` is only four rows; the granular geography lives on
    ``fact_sales.state``.
    """
    params: list = []
    clause = where_clause(
        period_predicate(period)[0], in_predicate("region", regions, params)
    )
    sql = f"""
        SELECT
            state,
            ANY_VALUE(region)                                        AS region,
            ROUND(SUM(sales_amount), 2)                              AS revenue,
            ROUND(SUM(profit), 2)                                    AS profit,
            ROUND(SUM(profit) / NULLIF(SUM(sales_amount), 0) * 100, 2) AS margin_pct,
            COUNT(DISTINCT order_id)                                 AS orders
        FROM main.fact_sales
        {clause}
        GROUP BY state
        ORDER BY revenue DESC
    """
    return run_query(sql, params)


def product_pareto(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
    limit: int = 60,
) -> list[dict]:
    """Products ranked by revenue with the running share of total revenue.

    The cumulative share is computed over *all* products before the limit is
    applied, so the curve reads against the true total rather than against the
    top N.
    """
    params: list = []
    clause = where_clause(
        period_predicate(period, alias="f")[0],
        in_predicate("p.category", categories, params),
        in_predicate("f.region", regions, params),
    )
    sql = f"""
        WITH by_product AS (
            SELECT
                p.product_name,
                p.category,
                SUM(f.sales_amount) AS revenue,
                SUM(f.profit)       AS profit
            FROM main.fact_sales f
            JOIN main.dim_product p ON f.product_id = p.product_id
            {clause}
            GROUP BY p.product_name, p.category
        ),
        ranked AS (
            SELECT
                product_name,
                category,
                revenue,
                profit,
                ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rank,
                SUM(revenue) OVER (ORDER BY revenue DESC
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    / NULLIF(SUM(revenue) OVER (), 0) * 100 AS cumulative_pct
            FROM by_product
        )
        SELECT
            rank,
            product_name,
            category,
            ROUND(revenue, 2)        AS revenue,
            ROUND(profit, 2)         AS profit,
            ROUND(cumulative_pct, 2) AS cumulative_pct
        FROM ranked
        WHERE rank <= {int(limit)}
        ORDER BY rank
    """
    return run_query(sql, params)


def discount_margin_bins(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Margin by 5-point discount bin, for the discount-vs-margin chart.

    ``get_discount_impact`` answers the same question in five broad bands for
    the AI and the summary table; a chart with a zero-margin reference rule
    needs finer resolution to show *where* the crossover actually happens.
    """
    params: list = []
    join = ""
    category_sql = ""
    if categories:
        join = "JOIN main.dim_product p ON f.product_id = p.product_id"
        category_sql = in_predicate("p.category", categories, params)
    clause = where_clause(
        period_predicate(period, alias="f")[0],
        category_sql,
        in_predicate("f.region", regions, params),
    )
    sql = f"""
        SELECT
            ROUND(FLOOR(f.discount * 20) / 20 * 100)                 AS discount_pct,
            COUNT(*)                                                 AS order_lines,
            ROUND(SUM(f.sales_amount), 2)                            AS revenue,
            ROUND(SUM(f.profit), 2)                                  AS profit,
            ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
        FROM main.fact_sales f
        {join}
        {clause}
        GROUP BY discount_pct
        HAVING COUNT(*) > 0
        ORDER BY discount_pct
    """
    return run_query(sql, params)


def current_date():
    """Today according to the database, so date maths matches the SQL filters."""
    return run_query("SELECT CURRENT_DATE AS today")[0]["today"]


def previous_period(period: str = "all_time") -> str | None:
    """The equally-long window immediately before ``period``, as a range token.

    KPI deltas need a "compared to what". Rather than define a second set of
    metric SQL for the prior window, the comparison is expressed as a period
    argument and handed back to ``query_metric`` -- so the delta and the
    headline figure are computed by the same expression over the same mart.

    Windows follow the calendar rather than the first and last order in the
    data: 2016 compares against the whole of 2015, not against "the 362 days
    before the first 2016 order".

    Returns:
        A ``range:`` period argument, or None when there is nothing sensible to
        compare against (all-time has no predecessor).
    """
    period = (period or "all_time").strip()
    today = current_date()

    if period == "all_time":
        return None
    if period == "this_year":
        return range_period(date(today.year - 1, 1, 1), today.replace(year=today.year - 1))
    if period == "last_year":
        return range_period(date(today.year - 2, 1, 1), date(today.year - 2, 12, 31))
    if period == "last_30_days":
        return range_period(today - timedelta(days=59), today - timedelta(days=30))
    if period == "last_90_days":
        return range_period(today - timedelta(days=179), today - timedelta(days=90))
    if period.isdigit() and len(period) == 4:
        year = int(period) - 1
        return range_period(date(year, 1, 1), date(year, 12, 31))

    bounds = parse_range(period)
    if bounds:
        lo, hi = bounds
        span = (hi - lo).days + 1
        return range_period(lo - timedelta(days=span), lo - timedelta(days=1))
    return None


def rfm_matrix(
    period: str = "all_time", regions: list[str] | None = None
) -> list[dict]:
    """Customers and revenue per recency x frequency score cell.

    The RFM scores are quartiles assigned over a customer's lifetime on
    ``dim_customer`` (1 = worst, 4 = best), so the grid itself does not move
    with the period; the revenue and customer counts in each cell do. That is
    the honest reading of "what did each part of the base contribute this
    quarter" without silently redefining the segmentation per window.
    """
    params: list = []
    clause = where_clause(
        period_predicate(period, alias="f")[0],
        in_predicate("f.region", regions, params),
    )
    sql = f"""
        SELECT
            c.r_score,
            c.f_score,
            COUNT(DISTINCT c.customer_id)  AS customers,
            ROUND(SUM(f.sales_amount), 2)  AS revenue,
            ANY_VALUE(c.rfm_segment)       AS example_segment
        FROM main.dim_customer c
        JOIN main.fact_sales f ON c.customer_id = f.customer_id
        {clause}
        GROUP BY c.r_score, c.f_score
        ORDER BY c.r_score, c.f_score
    """
    return run_query(sql, params)


def to_frame(rows: list[dict]) -> pd.DataFrame:
    """Turn a query result into a chart- and display-ready DataFrame.

    Two conversions, both of which Altair needs and neither of which pandas
    does on its own:

    * SQL DECIMAL arrives as ``decimal.Decimal``, which breaks arithmetic on a
      Series and cannot be serialised into a chart spec.
    * DATE arrives as ``datetime.date`` in an object column, which serialises
      as a bare Python object rather than a temporal value -- a temporal axis
      silently fails on it.

    Converting here rather than in the Streamlit layer means every consumer --
    charts, tables, tests -- gets the same types from one place.
    """
    df = pd.DataFrame(rows)
    for column in df.columns:
        values = df[column]
        if values.map(lambda v: isinstance(v, Decimal)).any():
            df[column] = values.astype(float)
        elif values.map(lambda v: isinstance(v, date)).any():
            df[column] = pd.to_datetime(values)
    return df
