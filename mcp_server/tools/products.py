"""Product analytics queries."""
from mcp_server.db import run_query
from mcp_server.tools._filters import in_predicate, period_predicate, where_clause


def get_product_performance(
    category: str | None = None,
    n: int = 10,
    period: str = "all_time",
    regions: list[str] | None = None,
    sub_categories: list[str] | None = None,
) -> list[dict]:
    """Return top products by revenue, optionally filtered by category.

    Args:
        category: One of 'Furniture', 'Office Supplies', 'Technology', or None for all.
        n: Number of products to return (default 10, max 50).
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to orders placed in these regions.
        sub_categories: Restrict to these product sub-categories.
    """
    n = min(max(n, 1), 50)
    params: list = []
    period_sql, _ = period_predicate(period, alias="f")
    clause = where_clause(
        period_sql,
        in_predicate("p.category", category, params),
        in_predicate("p.sub_category", sub_categories, params),
        in_predicate("f.region", regions, params),
    )

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
        {clause}
        GROUP BY p.product_name, p.category, p.sub_category
        ORDER BY total_revenue DESC
        LIMIT {n}
    """
    return run_query(sql, params)


def get_category_breakdown(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Return revenue and margin by category and sub-category.

    Args:
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to orders placed in these regions.
        categories: Restrict to these product categories.
    """
    params: list = []
    period_sql, _ = period_predicate(period, alias="f")
    clause = where_clause(
        period_sql,
        in_predicate("p.category", categories, params),
        in_predicate("f.region", regions, params),
    )

    sql = f"""
        SELECT
            p.category,
            p.sub_category,
            ROUND(SUM(f.sales_amount), 2)                            AS total_revenue,
            ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct,
            ROUND(AVG(f.discount) * 100, 1)                          AS avg_discount_pct
        FROM main.fact_sales f
        JOIN main.dim_product p ON f.product_id = p.product_id
        {clause}
        GROUP BY p.category, p.sub_category
        ORDER BY total_revenue DESC
    """
    return run_query(sql, params)


def get_discount_impact(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Return the discount-vs-margin analysis: order lines bucketed into
    discount bands, with revenue, average profit margin, and total profit per
    band. Higher discount bands should show progressively lower margins now
    that synthetic profit accounts for discount.

    Args:
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year.
        regions: Restrict to orders placed in these regions.
        categories: Restrict to these product categories.
    """
    params: list = []
    period_sql, _ = period_predicate(period, alias="f")
    # dim_product is only joined when a category filter is asked for -- the band
    # analysis itself needs nothing but fact_sales.
    join = ""
    category_sql = ""
    if categories:
        join = "JOIN main.dim_product p ON f.product_id = p.product_id"
        category_sql = in_predicate("p.category", categories, params)
    clause = where_clause(period_sql, category_sql, in_predicate("f.region", regions, params))

    sql = f"""
        WITH banded AS (
            SELECT
                CASE
                    WHEN f.discount = 0          THEN '0%'
                    WHEN f.discount <= 0.10      THEN '1-10%'
                    WHEN f.discount <= 0.20      THEN '11-20%'
                    WHEN f.discount <= 0.30      THEN '21-30%'
                    ELSE '30%+'
                END                                          AS discount_band,
                f.sales_amount,
                f.profit
            FROM main.fact_sales f
            {join}
            {clause}
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
    return run_query(sql, params)
