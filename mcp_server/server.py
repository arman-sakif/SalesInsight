"""SalesInsight MCP Server.

Exposes the sales intelligence warehouse as MCP tools that any MCP client
(Claude Desktop, MCP Inspector) can call to answer natural-language questions.

Tool descriptions must be real docstrings: FastMCP reads ``__doc__`` to build
the schema the model sees, so the period/region vocabulary is spelled out in
each one rather than shared from a constant.
"""
from mcp.server.fastmcp import FastMCP

# Imported under a suffixed name so the `regions` tool parameter below doesn't
# shadow the module.
from mcp_server.tools import customers as customers_tools
from mcp_server.tools import metrics as metrics_tools
from mcp_server.tools import products as products_tools
from mcp_server.tools import regions as regions_tools

mcp = FastMCP("SalesInsight")


@mcp.tool()
def query_metric(
    metric: str, period: str = "all_time", regions: list[str] | None = None
) -> dict:
    """Query a core business metric.

    Available metrics: total_revenue, total_profit, gross_profit_margin,
    total_orders, total_units_sold, average_order_value, total_customers.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year like '2016'.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    """
    return metrics_tools.query_metric(metric, period, regions)


@mcp.tool()
def explain_metric(metric: str) -> dict:
    """Explain what a metric means and how it is calculated, including its
    SQL expression and source table. Useful when a user asks what a metric is.
    """
    return metrics_tools.explain_metric(metric)


@mcp.tool()
def get_top_customers(
    n: int = 10,
    period: str = "all_time",
    regions: list[str] | None = None,
    segments: list[str] | None = None,
) -> list[dict]:
    """Get the top N customers by revenue, with their RFM segment, order count,
    and profit.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    Segments: a list of any of Champions, Loyal Customers, Potential Loyalists,
    At Risk, Lost; omit for all segments.
    """
    return customers_tools.get_top_customers(n, period, regions, segments)


@mcp.tool()
def get_rfm_segments(
    period: str = "all_time", regions: list[str] | None = None
) -> list[dict]:
    """Get the breakdown of customers across RFM segments (Champions, Loyal
    Customers, Potential Loyalists, At Risk, Lost) with customer counts and
    revenue. The segment label is a lifetime scoring of the customer; period
    and regions filter the revenue and activity attributed to each segment.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    """
    return customers_tools.get_rfm_segments(period, regions)


@mcp.tool()
def revenue_by_region(
    period: str = "all_time", regions: list[str] | None = None
) -> list[dict]:
    """Get revenue, profit, margin, and order counts broken down by sales region
    (West, East, Central, South).

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: restrict to a subset of regions; omit for all four.
    """
    return regions_tools.revenue_by_region(period, regions)


@mcp.tool()
def get_product_performance(
    category: str | None = None,
    n: int = 10,
    period: str = "all_time",
    regions: list[str] | None = None,
    sub_categories: list[str] | None = None,
) -> list[dict]:
    """Get top products by revenue, optionally filtered to a category
    ('Furniture', 'Office Supplies', or 'Technology') and/or a list of
    sub-categories.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    """
    return products_tools.get_product_performance(
        category, n, period, regions, sub_categories
    )


@mcp.tool()
def get_category_breakdown(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Get revenue and profit margin broken down by category and sub-category,
    including the average discount applied in each.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    Categories: a list of any of Furniture, Office Supplies, Technology.
    """
    return products_tools.get_category_breakdown(period, regions, categories)


@mcp.tool()
def get_discount_impact(
    period: str = "all_time",
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Get the discount-vs-margin analysis: order lines grouped into discount
    bands (0%, 1-10%, 11-20%, 21-30%, 30%+) with revenue, average profit margin,
    and total profit per band. Use this to answer how discounting affects margin.

    Period: 'all_time' (default), 'this_year', 'last_year', 'last_30_days',
    'last_90_days', or a 4-digit year.
    Regions: a list of any of West, East, Central, South; omit for all regions.
    Categories: a list of any of Furniture, Office Supplies, Technology.
    """
    return products_tools.get_discount_impact(period, regions, categories)


if __name__ == "__main__":
    mcp.run()
