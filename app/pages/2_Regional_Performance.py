"""Regional Performance — geography from four regions down to fifty states."""
import streamlit as st

from _shared import (
    chart_mode,
    count_column,
    filter_caption,
    kpi_row,
    money_column,
    page_setup,
    percent_column,
    region_revenue,
    sidebar_filters,
    state_revenue,
    table,
    to_frame,
)

import charts

page_setup("Regional Performance", "🗺️")

st.caption(
    "`dim_region` is a four-row dimension; the granular geography lives on "
    "`fact_sales` as state and city. Both are shown here — the map for where "
    "the business actually is, the region table for how it is managed."
)

filters = sidebar_filters()
filter_caption(filters)

# Resolved once per run and handed to every chart below: the palette has to
# match the theme the viewer is actually in.
mode = chart_mode()

kpi_row(["total_revenue", "total_profit", "gross_profit_margin"], filters)

st.divider()

# --- Map ------------------------------------------------------------------
st.subheader("Revenue by state")

states = to_frame(state_revenue(filters.period, filters.regions))
map_col, table_col = st.columns([3, 2], gap="large")

with map_col:
    st.altair_chart(
        charts.state_choropleth(states, height=420, mode=mode), width="stretch", theme=None
    )
    st.caption(
        "Shaded on a square-root scale — a linear ramp would leave everything "
        "but California and New York indistinguishable."
    )

with table_col:
    if states.empty:
        st.info("No orders in this selection.")
    else:
        renamed = states.rename(
            columns={
                "state": "State",
                "region": "Region",
                "revenue": "Revenue",
                "profit": "Profit",
                "margin_pct": "Margin %",
                "orders": "Orders",
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
                ),
                "Profit": money_column("Profit"),
                "Margin %": percent_column("Margin %"),
                "Orders": count_column("Orders"),
            },
            height=420,
        )

st.divider()

# --- Regions --------------------------------------------------------------
st.subheader("Region summary")

regions = to_frame(region_revenue(filters.period, filters.regions))
if regions.empty:
    st.info("No orders in this selection.")
else:
    chart_col, summary_col = st.columns([2, 3], gap="large")
    with chart_col:
        st.altair_chart(charts.region_bars(regions, mode=mode), width="stretch", theme=None)
    with summary_col:
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
        best = regions.loc[regions["profit_margin_pct"].idxmax()]
        worst = regions.loc[regions["profit_margin_pct"].idxmin()]
        st.caption(
            f"Widest margin: **{best['region']}** at {best['profit_margin_pct']:.1f}%. "
            f"Narrowest: **{worst['region']}** at {worst['profit_margin_pct']:.1f}%."
        )
