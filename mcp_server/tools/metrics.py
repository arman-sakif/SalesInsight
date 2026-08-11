"""Core business metric queries."""
from mcp_server.db import run_query

METRIC_DEFINITIONS = {
    "total_revenue": {
        "sql": "SUM(sales_amount)",
        "label": "Total Revenue",
        "description": "Sum of all sales amounts across order lines.",
    },
    "total_profit": {
        "sql": "SUM(profit)",
        "label": "Total Profit",
        "description": "Sum of profit across all order lines.",
    },
    "gross_profit_margin": {
        "sql": "ROUND(SUM(profit) / NULLIF(SUM(sales_amount), 0) * 100, 2)",
        "label": "Gross Profit Margin %",
        "description": "Total profit divided by total revenue, as a percentage.",
    },
    "total_orders": {
        "sql": "COUNT(DISTINCT order_id)",
        "label": "Total Orders",
        "description": "Count of unique orders.",
    },
    "total_units_sold": {
        "sql": "SUM(quantity)",
        "label": "Total Units Sold",
        "description": "Sum of quantity across all order lines.",
    },
    "average_order_value": {
        "sql": "ROUND(SUM(sales_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2)",
        "label": "Average Order Value",
        "description": "Total revenue divided by number of distinct orders.",
    },
    "total_customers": {
        "sql": "COUNT(DISTINCT customer_id)",
        "label": "Total Customers",
        "description": "Count of unique customers.",
    },
}


def query_metric(metric: str, period: str = "all_time") -> dict:
    """Query a single business metric, optionally filtered by period.

    Args:
        metric: One of the keys in METRIC_DEFINITIONS.
        period: 'all_time', 'this_year', 'last_year', or a 4-digit year like '2016'.
    """
    if metric not in METRIC_DEFINITIONS:
        return {
            "error": f"Unknown metric '{metric}'.",
            "available_metrics": list(METRIC_DEFINITIONS.keys()),
        }

    definition = METRIC_DEFINITIONS[metric]
    where_clause, filter_label = _build_period_filter(period)

    sql = f"""
        SELECT {definition['sql']} AS value
        FROM main.fact_sales
        {where_clause}
    """
    rows = run_query(sql)
    value = rows[0]["value"] if rows else None

    return {
        "metric": metric,
        "label": definition["label"],
        "value": value,
        "period": filter_label,
    }


def _build_period_filter(period: str) -> tuple[str, str]:
    """Return a WHERE clause and a human-readable label for the period."""
    if period == "all_time":
        return "", "All time"
    if period == "this_year":
        return "WHERE order_year = YEAR(CURRENT_DATE)", "This year"
    if period == "last_year":
        return "WHERE order_year = YEAR(CURRENT_DATE) - 1", "Last year"
    if period.isdigit() and len(period) == 4:
        return f"WHERE order_year = {int(period)}", f"Year {period}"
    return "", "All time"


def explain_metric(metric: str) -> dict:
    """Return a plain-English explanation of a metric and how it's calculated."""
    if metric not in METRIC_DEFINITIONS:
        return {
            "error": f"Unknown metric '{metric}'.",
            "available_metrics": list(METRIC_DEFINITIONS.keys()),
        }
    definition = METRIC_DEFINITIONS[metric]
    return {
        "metric": metric,
        "label": definition["label"],
        "description": definition["description"],
        "sql_expression": definition["sql"],
        "source_table": "main.fact_sales (built by dbt from the medallion pipeline)",
    }