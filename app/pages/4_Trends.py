"""Trends — revenue over time, in the two eras the dataset actually has.

Two stacked panels rather than one continuous line, because the data is two
sources with an eight-year gap between them: the Kaggle Superstore extract
(2014-2017) and the synthetic feed the pipeline regenerates on every refresh.
Plotting them as one series would draw eight years of flatline through the
middle of the chart and invite the reader to interpret it as a collapse.
"""
import streamlit as st

from _shared import (
    ERA_HISTORICAL,
    ERA_RECENT,
    chart_mode,
    compact_money,
    filter_caption,
    money_column,
    page_setup,
    percent_column,
    count_column,
    sidebar_filters,
    table,
    timeseries,
    to_frame,
)

import charts

page_setup("Trends", "📈")

st.caption(
    "How revenue moves over time. The two panels are the two data sources: a "
    "live synthetic order feed for the recent window, and the Superstore "
    "history behind it."
)

filters = sidebar_filters()
filter_caption(filters)

# Resolved once per run and handed to every chart below: the palette has to
# match the theme the viewer is actually in.
mode = chart_mode()

# --- Recent activity ------------------------------------------------------
st.subheader("Recent activity")

recent = to_frame(timeseries("day", filters.period, filters.regions, ERA_RECENT))
if recent.empty or len(recent) < 2:
    st.info(
        "The selected period doesn't reach the recent synthetic window. "
        "Pick **Last 30 days**, **Last 90 days**, or the current year to see it."
    )
else:
    st.altair_chart(charts.revenue_trend(recent, "day", mode=mode), width="stretch", theme=None)
    st.caption(
        "Daily revenue in grey, 7-day trailing average in blue. Days with no "
        "orders are plotted as zero rather than skipped, so the average always "
        "spans seven calendar days."
    )

    busiest = recent.loc[recent["revenue"].idxmax()]
    summary = st.columns(4)
    summary[0].metric("Days shown", f"{len(recent):,}")
    summary[1].metric("Revenue", compact_money(recent["revenue"].sum()))
    summary[2].metric("Best day", busiest["period_start"].strftime("%d %b"),
                      help=f"{compact_money(busiest['revenue'])} on this day")
    summary[3].metric("Daily average", compact_money(recent["revenue"].mean()))

st.divider()

# --- Historical -----------------------------------------------------------
st.subheader("Superstore history (2014–2017)")

historical = to_frame(
    timeseries("month", filters.period, filters.regions, ERA_HISTORICAL, 0)
)
if historical.empty:
    st.info(
        "The selected period doesn't overlap the 2014–2017 history. "
        "Pick **All time** or one of the year options to see it."
    )
else:
    st.altair_chart(charts.revenue_vs_profit(historical, mode=mode), width="stretch", theme=None)
    st.caption(
        "Revenue and profit share one axis on purpose. They are both dollars, "
        "and the distance between the lines is the margin story — a second "
        "y-scale would rescale that gap into a coincidence."
    )

    with st.expander("Monthly figures"):
        monthly = historical.copy()
        monthly["Month"] = monthly["period_start"].dt.strftime("%b %Y")
        table(
            monthly[["Month", "revenue", "profit", "margin_pct", "orders"]].rename(
                columns={
                    "revenue": "Revenue",
                    "profit": "Profit",
                    "margin_pct": "Margin %",
                    "orders": "Orders",
                }
            ),
            {
                "Revenue": money_column("Revenue"),
                "Profit": money_column("Profit"),
                "Margin %": percent_column("Margin %"),
                "Orders": count_column("Orders"),
            },
            height=360,
        )

st.divider()
st.caption(
    "Why the gap: the historical extract ends in 2017 and the synthetic "
    "generator writes a rolling window ending today, so there is no data in "
    "between. Retention prunes synthetic rows older than a year but never "
    "touches the Kaggle baseline — deleting it would collapse the "
    "year-over-year view and the RFM recency spread."
)
