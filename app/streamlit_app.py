"""SalesInsight — Executive Overview (Streamlit home page).

Run with:  uv run streamlit run app/streamlit_app.py

This is the recruiter-facing web surface. It reads from the same dbt-built
DuckDB semantic layer as the MCP server and Power BI, reusing the query
functions in ``mcp_server/tools`` so every number is consistent across the
dashboard, the AI tools, and the .pbix report.
"""
import streamlit as st

from _shared import (
    ERA_HISTORICAL,
    ERA_RECENT,
    METRIC_DEFINITIONS,
    filter_caption,
    kpi_row,
    metric_explanation,
    money_column,
    page_setup,
    percent_column,
    count_column,
    region_revenue,
    sidebar_filters,
    state_revenue,
    table,
    timeseries,
    to_frame,
)

import charts

page_setup("Executive Overview", "📊")

st.caption(
    "Sales intelligence over a Superstore dataset, served from a dbt-built "
    "DuckDB semantic layer. The same layer powers the Power BI report and the "
    "MCP AI tools, so these figures match everywhere."
)

filters = sidebar_filters()
filter_caption(filters)

# --- Headline KPIs --------------------------------------------------------
kpi_row(
    [
        "total_revenue",
        "total_profit",
        "gross_profit_margin",
        "total_orders",
        "average_order_value",
        "total_customers",
    ],
    filters,
)

st.divider()

# --- Revenue trend --------------------------------------------------------
# The dataset is two eras with a gap between them, so the grain follows the
# selection rather than being fixed: a daily line with a trailing average where
# the selection reaches the live synthetic feed, monthly where it only covers
# the Superstore history. The full picture, both panels at once, is on Trends.
st.subheader("Revenue trend")

recent = to_frame(timeseries("day", filters.period, filters.regions, ERA_RECENT))
if not recent.empty and len(recent) > 1:
    st.altair_chart(charts.revenue_trend(recent, "day"), width="stretch", theme=None)
    st.caption(
        "Daily revenue in grey, 7-day trailing average in blue. "
        "Recent activity only — see **Trends** for the 2014–2017 history."
    )
else:
    historical = to_frame(
        timeseries("month", filters.period, filters.regions, ERA_HISTORICAL, 0)
    )
    st.altair_chart(charts.revenue_trend(historical, "month"), width="stretch", theme=None)
    st.caption(
        "Monthly revenue over the Superstore history. This selection predates "
        "the live synthetic feed — see **Trends** for both eras side by side."
    )

st.divider()

# --- Geography ------------------------------------------------------------
st.subheader("Where the revenue comes from")

map_col, region_col = st.columns([3, 2], gap="large")

with map_col:
    states = to_frame(state_revenue(filters.period, filters.regions))
    st.altair_chart(charts.state_choropleth(states), width="stretch", theme=None)
    st.caption("Revenue by state. Darker is higher; states with no orders stay unshaded.")

with region_col:
    regions = to_frame(region_revenue(filters.period, filters.regions))
    if regions.empty:
        st.info("No orders in this selection.")
    else:
        st.altair_chart(charts.region_bars(regions), width="stretch", theme=None)
        table(
            regions.rename(
                columns={
                    "region": "Region",
                    "total_revenue": "Revenue",
                    "total_profit": "Profit",
                    "profit_margin_pct": "Margin %",
                    "total_orders": "Orders",
                }
            ),
            {
                "Revenue": money_column("Revenue"),
                "Profit": money_column("Profit"),
                "Margin %": percent_column("Margin %"),
                "Orders": count_column("Orders"),
            },
        )

st.divider()

# --- Metric glossary (reuses explain_metric) -----------------------------
with st.expander("What do these metrics mean?"):
    st.markdown(
        "Each definition below is read straight from the MCP tool layer — the "
        "same `explain_metric` tool an AI client calls, so the dashboard cannot "
        "drift from the documented definition."
    )
    metric_name = st.selectbox(
        "Metric",
        list(METRIC_DEFINITIONS.keys()),
        format_func=lambda k: METRIC_DEFINITIONS[k]["label"],
    )
    info = metric_explanation(metric_name)
    st.markdown(f"**{info['label']}** — {info['description']}")
    st.code(info["sql_expression"], language="sql")
    st.caption(f"Source: {info['source_table']}")
