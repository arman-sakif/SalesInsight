"""Product analytics queries."""
from mcp_server.db import run_query


def get_product_performance(category: str | None = None, n: int = 10) -> list[dict]:
    """Return top products by revenue, optionally filtered by category.

    Args:
        category: One of 'Furniture', 'Office Supplies', 'Technology', or None for all.
        n: Number of products to return (default 10, max 50).
    """
    n = min(max(n, 1), 50)
    where_clause = ""
    params = []
    if category:
        where_clause = "WHERE p.category = ?"
        params.append(category)

    sql = f"""
        SELECT
            p.product_name,
            p.category,
            p.sub_category,
            ROUND(SUM(f.sales_amount), 2)   AS total_revenue,
            SUM(f.quantity)                 AS units_sold,
            ROUND(SUM(f.profit), 2)         AS total_profit
        FROM main.fact_sales f
        JOIN main.dim_product p ON f.product_id = p.product_id
        {where_clause}
        GROUP BY p.product_name, p.category, p.sub_category
        ORDER BY total_revenue DESC
        LIMIT {n}
    """
    return run_query(sql, params if params else None)


def get_category_breakdown() -> list[dict]:
    """Return revenue and margin by category and sub-category."""
    sql = """
        SELECT
            p.category,
            p.sub_category,
            ROUND(SUM(f.sales_amount), 2)                            AS total_revenue,
            ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
        FROM main.fact_sales f
        JOIN main.dim_product p ON f.product_id = p.product_id
        GROUP BY p.category, p.sub_category
        ORDER BY total_revenue DESC
    """
    return run_query(sql)