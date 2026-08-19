"""Regional analytics queries."""
from mcp_server.db import run_query
from mcp_server.tools._filters import in_predicate, period_predicate, where_clause


def revenue_by_region(period: str = "all_time", regions: list[str] | None = None) -> list[dict]:
    """Return revenue, profit, and order counts broken down by region.

    Args:
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to these regions. None or empty means all four.
    """
    params: list = []
    period_sql, _ = period_predicate(period)
    clause = where_clause(period_sql, in_predicate("region", regions, params))

    sql = f"""
        SELECT
            region,
            ROUND(SUM(sales_amount), 2)                              AS total_revenue,
            ROUND(SUM(profit), 2)                                    AS total_profit,
            ROUND(SUM(profit) / NULLIF(SUM(sales_amount), 0) * 100, 2) AS profit_margin_pct,
            COUNT(DISTINCT order_id)                                 AS total_orders
        FROM main.fact_sales
        {clause}
        GROUP BY region
        ORDER BY total_revenue DESC
    """
    return run_query(sql, params)
