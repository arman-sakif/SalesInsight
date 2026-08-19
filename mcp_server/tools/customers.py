"""Customer analytics queries."""
from mcp_server.db import run_query
from mcp_server.tools._filters import in_predicate, period_predicate, where_clause


def get_top_customers(
    n: int = 10,
    period: str = "all_time",
    regions: list[str] | None = None,
    segments: list[str] | None = None,
) -> list[dict]:
    """Return the top N customers by total revenue.

    Args:
        n: Number of customers to return (default 10, max 50).
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to orders placed in these regions.
        segments: Restrict to these RFM segments (Champions, Loyal Customers,
            Potential Loyalists, At Risk, Lost).
    """
    n = min(max(n, 1), 50)
    params: list = []
    period_sql, _ = period_predicate(period, alias="f")
    clause = where_clause(
        period_sql,
        in_predicate("f.region", regions, params),
        in_predicate("c.rfm_segment", segments, params),
    )

    sql = f"""
        SELECT
            c.customer_name,
            c.rfm_segment,
            ROUND(SUM(f.sales_amount), 2)   AS total_revenue,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            ROUND(SUM(f.profit), 2)         AS total_profit
        FROM main.fact_sales f
        JOIN main.dim_customer c ON f.customer_id = c.customer_id
        {clause}
        GROUP BY c.customer_name, c.rfm_segment
        ORDER BY total_revenue DESC
        LIMIT {n}
    """
    return run_query(sql, params)


def get_rfm_segments(
    period: str = "all_time",
    regions: list[str] | None = None,
) -> list[dict]:
    """Return the distribution of customers across RFM segments with revenue.

    The segment label itself is assigned all-time on ``dim_customer`` (RFM is a
    lifetime scoring of the customer, not of a window). ``period`` and
    ``regions`` filter the *revenue* attributed to each segment, which is the
    question a slicer is actually asking: "what did Champions bring in this
    year?" -- so ``customer_count`` counts customers active in the window, and
    ``avg_customer_value`` stays a lifetime figure by definition.

    Args:
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to orders placed in these regions.
    """
    params: list = []
    period_sql, _ = period_predicate(period, alias="f")
    clause = where_clause(period_sql, in_predicate("f.region", regions, params))

    sql = f"""
        SELECT
            c.rfm_segment,
            COUNT(DISTINCT c.customer_id)       AS customer_count,
            ROUND(SUM(f.sales_amount), 2)       AS total_revenue,
            ROUND(AVG(c.monetary), 2)           AS avg_customer_value
        FROM main.dim_customer c
        JOIN main.fact_sales f ON c.customer_id = f.customer_id
        {clause}
        GROUP BY c.rfm_segment
        ORDER BY total_revenue DESC
    """
    return run_query(sql, params)
