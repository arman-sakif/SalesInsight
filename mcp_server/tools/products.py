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
            ROUND(SUM(f.profit), 2)         AS total_profit,
            ROUND(AVG(f.discount) * 100, 1) AS avg_discount_pct
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
            ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct,
            ROUND(AVG(f.discount) * 100, 1)                          AS avg_discount_pct
        FROM main.fact_sales f
        JOIN main.dim_product p ON f.product_id = p.product_id
        GROUP BY p.category, p.sub_category
        ORDER BY total_revenue DESC
    """
    return run_query(sql)


def get_discount_impact() -> list[dict]:
    """Return the discount-vs-margin analysis: order lines bucketed into
    discount bands, with revenue, average profit margin, and total profit per
    band. Higher discount bands should show progressively lower margins now
    that synthetic profit accounts for discount.
    """
    sql = """
        WITH banded AS (
            SELECT
                CASE
                    WHEN discount = 0            THEN '0%'
                    WHEN discount <= 0.10        THEN '1-10%'
                    WHEN discount <= 0.20        THEN '11-20%'
                    WHEN discount <= 0.30        THEN '21-30%'
                    ELSE '30%+'
                END                                          AS discount_band,
                sales_amount,
                profit
            FROM main.fact_sales
        )
        SELECT
            discount_band,
            COUNT(*)                                                 AS order_lines,
            ROUND(SUM(sales_amount), 2)                              AS total_revenue,
            ROUND(SUM(profit) / NULLIF(SUM(sales_amount), 0) * 100, 2) AS avg_margin_pct,
            ROUND(SUM(profit), 2)                                    AS total_profit
        FROM banded
        GROUP BY discount_band
        ORDER BY
            CASE discount_band
                WHEN '0%'     THEN 0
                WHEN '1-10%'  THEN 1
                WHEN '11-20%' THEN 2
                WHEN '21-30%' THEN 3
                ELSE 4
            END
    """
    return run_query(sql)