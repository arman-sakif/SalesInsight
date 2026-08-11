"""Customer analytics queries."""
from mcp_server.db import run_query


def get_top_customers(n: int = 10, period: str = "all_time") -> list[dict]:
    """Return the top N customers by total revenue.

    Args:
        n: Number of customers to return (default 10, max 50).
        period: 'all_time', 'this_year', 'last_year', or a 4-digit year.
    """
    n = min(max(n, 1), 50)
    where_clause = _period_filter(period)

    sql = f"""
        SELECT
            c.customer_name,
            c.rfm_segment,
            ROUND(SUM(f.sales_amount), 2)   AS total_revenue,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            ROUND(SUM(f.profit), 2)         AS total_profit
        FROM main.fact_sales f
        JOIN main.dim_customer c ON f.customer_id = c.customer_id
        {where_clause}
        GROUP BY c.customer_name, c.rfm_segment
        ORDER BY total_revenue DESC
        LIMIT {n}
    """
    return run_query(sql)


def get_rfm_segments() -> list[dict]:
    """Return the distribution of customers across RFM segments with revenue."""
    sql = """
        SELECT
            c.rfm_segment,
            COUNT(DISTINCT c.customer_id)       AS customer_count,
            ROUND(SUM(f.sales_amount), 2)       AS total_revenue,
            ROUND(AVG(c.monetary), 2)           AS avg_customer_value
        FROM main.dim_customer c
        JOIN main.fact_sales f ON c.customer_id = f.customer_id
        GROUP BY c.rfm_segment
        ORDER BY total_revenue DESC
    """
    return run_query(sql)


def _period_filter(period: str) -> str:
    if period == "this_year":
        return "WHERE f.order_year = YEAR(CURRENT_DATE)"
    if period == "last_year":
        return "WHERE f.order_year = YEAR(CURRENT_DATE) - 1"
    if period.isdigit() and len(period) == 4:
        return f"WHERE f.order_year = {int(period)}"
    return ""