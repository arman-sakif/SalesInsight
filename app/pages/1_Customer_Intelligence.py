"""Customer Intelligence — RFM segmentation and the top of the customer base."""
import streamlit as st

from _shared import (
    chart_mode,
    count_column,
    filter_caption,
    kpi_row,
    money_column,
    page_setup,
    rfm_matrix,
    rfm_segments,
    sidebar_filters,
    table,
    to_frame,
    top_customers,
)

import charts

page_setup("Customer Intelligence", "👥")

st.caption(
    "RFM segmentation built in the dbt intermediate layer: customers are scored "
    "into quartiles on recency, frequency, and monetary value, then labelled. "
    "The scores are a lifetime view of each customer; the filters narrow the "
    "revenue and activity attributed to them."
)

filters = sidebar_filters(segments=True, top_n=10)
filter_caption(filters)

# Resolved once per run and handed to every chart below: the palette has to
# match the theme the viewer is actually in.
mode = chart_mode()

kpi_row(["total_customers", "total_orders", "average_order_value"], filters)

st.divider()

# --- RFM ------------------------------------------------------------------
st.subheader("How the customer base splits")

grid_col, segment_col = st.columns([3, 2], gap="large")

with grid_col:
    matrix = to_frame(rfm_matrix(filters.period, filters.regions))
    st.altair_chart(charts.rfm_heatmap(matrix, mode=mode), width="stretch", theme=None)
    st.caption(
        "Each cell is a recency × frequency quartile pair, shaded by revenue "
        "and labelled with its customer count. The top-right corner is the "
        "best of the base: recent and frequent."
    )

with segment_col:
    segments = to_frame(rfm_segments(filters.period, filters.regions))
    if segments.empty:
        st.info("No customers ordered in this selection.")
    else:
        st.altair_chart(
            charts.segment_revenue_bars(segments, mode=mode), width="stretch", theme=None
        )
        table(
            segments.rename(
                columns={
                    "rfm_segment": "Segment",
                    "customer_count": "Customers",
                    "total_revenue": "Revenue",
                    "avg_customer_value": "Avg lifetime value",
                }
            ),
            {
                "Customers": count_column("Customers"),
                "Revenue": money_column("Revenue"),
                "Avg lifetime value": money_column("Avg lifetime value"),
            },
        )
        st.caption(
            "Average lifetime value is a whole-history figure by definition, so "
            "it does not move with the period filter."
        )

st.divider()

# --- Top customers --------------------------------------------------------
st.subheader(f"Top {filters.top_n} customers by revenue")

customers = to_frame(
    top_customers(filters.top_n, filters.period, filters.regions, filters.segments)
)
if customers.empty:
    st.info("No customers match this filter set.")
else:
    renamed = customers.rename(
        columns={
            "customer_name": "Customer",
            "rfm_segment": "Segment",
            "total_revenue": "Revenue",
            "total_orders": "Orders",
            "total_profit": "Profit",
        }
    )
    table(
        renamed,
        {
            "Revenue": st.column_config.ProgressColumn(
                "Revenue",
                format="$%,.0f",
                min_value=0,
                max_value=float(renamed["Revenue"].max()),
                help="Bar length is revenue relative to the top customer in this slice.",
            ),
            "Profit": money_column("Profit"),
            "Orders": count_column("Orders"),
        },
    )
