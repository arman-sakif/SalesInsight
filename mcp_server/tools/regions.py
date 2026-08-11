"""Regional analytics queries."""
from mcp_server.db import run_query


def revenue_by_region(period: str = "all_time") -> list[dict]:
    """Return revenue, profit, and order counts broken down by region.

    Args:
        period: 'all_time', 'this_year', 'last_year', or a 4-digit year.
    """
    where_clause = _period_filter(period)

    sql = f"""
        SELECT
            region,
            ROUND(SUM(sales_amount), 2)                              AS total_revenue,
            ROUND(SUM(profit), 2)                                    AS total_profit,
            ROUND(SUM(profit) / NULLIF(SUM(sales_amount), 0) * 100, 2) AS profit_margin_pct,
            COUNT(DISTINCT order_id)                                 AS total_orders
        FROM main.fact_sales
        {where_clause}
        GROUP BY region
        ORDER BY total_revenue DESC
    """
    return run_query(sql)


def _period_filter(period: str) -> str:
    if period == "this_year":
        return "WHERE order_year = YEAR(CURRENT_DATE)"
    if period == "last_year":
        return "WHERE order_year = YEAR(CURRENT_DATE) - 1"
    if period.isdigit() and len(period) == 4:
        return f"WHERE order_year = {int(period)}"
    return ""