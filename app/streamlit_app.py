"""SalesInsight — Executive Overview (Streamlit home page).

Run with:  uv run streamlit run app/streamlit_app.py

This is the recruiter-facing web surface. It reads from the same
dbt-built DuckDB semantic layer as the MCP server and Power BI, reusing
the query functions in ``mcp_server/tools`` so every number is consistent
across the dashboard, the AI tools, and the .pbix report.
"""
import streamlit as st

from _shared import (
    METRIC_DEFINITIONS,
    metric,
    metric_explanation,
    money,
    page_setup,
    period_selector,
    region_revenue,
    to_frame,
)

page_setup("Executive Overview", "📊")

st.caption(
    "Sales intelligence over a Superstore dataset, served from a dbt-built "
    "DuckDB semantic layer. The same layer powers the Power BI report and the "
    "MCP AI tools, so these figures match everywhere."
)

period = period_selector()

# --- Headline KPIs --------------------------------------------------------
kpi_metrics = [
    "total_revenue",
    "total_profit",
    "gross_profit_margin",
    "total_orders",
    "average_order_value",
    "total_customers",
]


def _format(name: str, value) -> str:
    if value is None:
        return "—"
    if name == "gross_profit_margin":
        return f"{float(value):.1f}%"
    if name in {"total_revenue", "total_profit", "average_order_value"}:
        return money(value)
    return f"{int(value):,}"


cols = st.columns(3)
for i, name in enumerate(kpi_metrics):
    result = metric(name, period)
    cols[i % 3].metric(result["label"], _format(name, result["value"]))

st.divider()

# --- Revenue & profit by region ------------------------------------------
st.subheader("Revenue by region")
region_df = to_frame(region_revenue(period))
if not region_df.empty:
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(
            region_df.rename(
                columns={
                    "region": "Region",
                    "total_revenue": "Revenue",
                    "total_profit": "Profit",
                    "profit_margin_pct": "Margin %",
                    "total_orders": "Orders",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.bar_chart(region_df.set_index("region")["total_revenue"], height=320)
else:
    st.info("No data for the selected period.")

st.divider()

# --- Metric glossary (reuses explain_metric) -----------------------------
with st.expander("What do these metrics mean?"):
    metric_name = st.selectbox(
        "Metric", list(METRIC_DEFINITIONS.keys()), format_func=lambda k: METRIC_DEFINITIONS[k]["label"]
    )
    info = metric_explanation(metric_name)
    st.markdown(f"**{info['label']}** — {info['description']}")
    st.code(info["sql_expression"], language="sql")
    st.caption(f"Source: {info['source_table']}")
