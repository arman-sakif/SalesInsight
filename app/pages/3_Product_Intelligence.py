"""Product Intelligence — catalogue concentration, category mix, and discounting."""
import streamlit as st

from _shared import (
    category_breakdown,
    count_column,
    discount_bins,
    discount_impact,
    filter_caption,
    kpi_row,
    money_column,
    page_setup,
    pareto,
    percent_column,
    product_performance,
    sidebar_filters,
    table,
    to_frame,
)

import charts

page_setup("Product Intelligence", "📦")

st.caption(
    "Product and category performance, and what discounting does to margin. "
    "Every panel here honours the sidebar filters — including Period, which "
    "these queries previously ignored."
)

filters = sidebar_filters(categories=True, sub_categories=True, top_n=10)
filter_caption(filters)

kpi_row(["total_revenue", "total_units_sold", "gross_profit_margin"], filters)

st.divider()

tab_products, tab_mix, tab_discount = st.tabs(
    ["Top products", "Category mix", "Discount & margin"]
)

# --- Top products ---------------------------------------------------------
with tab_products:
    products = to_frame(
        product_performance(
            filters.category,
            filters.top_n,
            filters.period,
            filters.regions,
            filters.sub_categories,
        )
    )
    if products.empty:
        st.info("No products match this filter set.")
    else:
        st.altair_chart(charts.top_products_bars(products), width="stretch", theme=None)
        table(
            products.rename(
                columns={
                    "product_name": "Product",
                    "category": "Category",
                    "sub_category": "Sub-category",
                    "total_revenue": "Revenue",
                    "units_sold": "Units",
                    "total_profit": "Profit",
                    "avg_discount_pct": "Avg discount %",
                }
            ),
            {
                "Revenue": money_column("Revenue"),
                "Profit": money_column("Profit"),
                "Units": count_column("Units"),
                "Avg discount %": percent_column("Avg discount %"),
            },
        )

    st.subheader("How concentrated is the catalogue?")
    curve = to_frame(
        pareto(filters.period, filters.regions, filters.categories, 100)
    )
    st.altair_chart(charts.pareto_curve(curve), width="stretch", theme=None)
    if not curve.empty:
        # The rank where cumulative share first clears 80% -- the number the
        # curve exists to produce, so it should not have to be read off an axis.
        above = curve[curve["cumulative_pct"] >= 80]
        if not above.empty:
            rank = int(above.iloc[0]["rank"])
            st.caption(
                f"The top **{rank}** products carry 80% of revenue in this slice."
            )
        else:
            st.caption(
                f"The top {len(curve)} products carry "
                f"{curve['cumulative_pct'].iloc[-1]:.0f}% of revenue in this slice — "
                "the catalogue is less concentrated than the 80% mark."
            )

# --- Category mix ---------------------------------------------------------
with tab_mix:
    mix = to_frame(
        category_breakdown(filters.period, filters.regions, filters.categories)
    )
    if mix.empty:
        st.info("No categories match this filter set.")
    else:
        heat_col, mix_table_col = st.columns([2, 3], gap="large")
        with heat_col:
            st.altair_chart(charts.category_heatmap(mix), width="stretch", theme=None)
        with mix_table_col:
            table(
                mix.rename(
                    columns={
                        "category": "Category",
                        "sub_category": "Sub-category",
                        "total_revenue": "Revenue",
                        "margin_pct": "Margin %",
                        "avg_discount_pct": "Avg discount %",
                    }
                ),
                {
                    "Revenue": money_column("Revenue"),
                    "Margin %": percent_column("Margin %"),
                    "Avg discount %": percent_column("Avg discount %"),
                },
                height=380,
            )

# --- Discount -------------------------------------------------------------
with tab_discount:
    st.subheader("What discounting costs")
    bins = to_frame(discount_bins(filters.period, filters.regions, filters.categories))
    st.altair_chart(charts.discount_margin(bins), width="stretch", theme=None)

    if not bins.empty:
        negative = bins[bins["margin_pct"] < 0]
        if not negative.empty:
            crossover = negative.iloc[0]["discount_pct"]
            st.caption(
                f"Margin turns negative from about **{crossover:.0f}% off**. "
                "Blue bars are profitable discount depths, red are loss-making."
            )
        else:
            st.caption("No discount band is loss-making in this slice.")

    st.markdown("**Discount bands**")
    bands = to_frame(
        discount_impact(filters.period, filters.regions, filters.categories)
    )
    if bands.empty:
        st.info("No order lines in this selection.")
    else:
        table(
            bands.rename(
                columns={
                    "discount_band": "Discount band",
                    "order_lines": "Order lines",
                    "total_revenue": "Revenue",
                    "avg_margin_pct": "Margin %",
                    "total_profit": "Profit",
                }
            ),
            {
                "Order lines": count_column("Order lines"),
                "Revenue": money_column("Revenue"),
                "Margin %": percent_column("Margin %"),
                "Profit": money_column("Profit"),
            },
        )
        st.caption(
            "The band table is the `get_discount_impact` MCP tool verbatim — the "
            "same five buckets an AI client gets when asked how discounting "
            "affects margin."
        )
