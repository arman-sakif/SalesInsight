"""SalesInsight MCP Server.

Exposes the sales intelligence warehouse as MCP tools that any MCP client
(Claude Desktop, MCP Inspector) can call to answer natural-language questions.
"""
from mcp.server.fastmcp import FastMCP

from mcp_server.tools import metrics, customers, regions, products

mcp = FastMCP("SalesInsight")


@mcp.tool()
def query_metric(metric: str, period: str = "all_time") -> dict:
    """Query a core business metric.

    Available metrics: total_revenue, total_profit, gross_profit_margin,
    total_orders, total_units_sold, average_order_value, total_customers.

    Period options: 'all_time' (default), 'this_year', 'last_year',
    or a 4-digit year like '2016'.
    """
    return metrics.query_metric(metric, period)


@mcp.tool()
def explain_metric(metric: str) -> dict:
    """Explain what a metric means and how it is calculated, including its
    SQL expression and source table. Useful when a user asks what a metric is.
    """
    return metrics.explain_metric(metric)


@mcp.tool()
def get_top_customers(n: int = 10, period: str = "all_time") -> list[dict]:
    """Get the top N customers by revenue, with their RFM segment, order count,
    and profit. Period options: 'all_time', 'this_year', 'last_year', or a year.
    """
    return customers.get_top_customers(n, period)


@mcp.tool()
def get_rfm_segments() -> list[dict]:
    """Get the breakdown of customers across RFM segments (Champions, Loyal
    Customers, Potential Loyalists, At Risk, Lost) with customer counts and revenue.
    """
    return customers.get_rfm_segments()


@mcp.tool()
def revenue_by_region(period: str = "all_time") -> list[dict]:
    """Get revenue, profit, margin, and order counts broken down by sales region
    (West, East, Central, South). Period options as above.
    """
    return regions.revenue_by_region(period)


@mcp.tool()
def get_product_performance(category: str | None = None, n: int = 10) -> list[dict]:
    """Get top products by revenue, optionally filtered to a category
    ('Furniture', 'Office Supplies', or 'Technology').
    """
    return products.get_product_performance(category, n)


@mcp.tool()
def get_category_breakdown() -> list[dict]:
    """Get revenue and profit margin broken down by category and sub-category."""
    return products.get_category_breakdown()


if __name__ == "__main__":
    mcp.run()