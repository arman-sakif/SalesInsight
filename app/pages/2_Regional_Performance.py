"""Regional Performance — revenue, profit, and margin by region."""
import streamlit as st

from _shared import money, page_setup, period_selector, region_revenue, to_frame

page_setup("Regional Performance", "🗺️")

period = period_selector()

region_df = to_frame(region_revenue(period))
if region_df.empty:
    st.info("No data for the selected period.")
    st.stop()

# --- Summary tiles --------------------------------------------------------
best = region_df.iloc[0]
best_margin = region_df.loc[region_df["profit_margin_pct"].idxmax()]
c1, c2, c3 = st.columns(3)
c1.metric("Top region (revenue)", best["region"], money(best["total_revenue"]))
c2.metric("Best margin", best_margin["region"], f"{best_margin['profit_margin_pct']:.1f}%")
c3.metric("Total revenue", money(region_df["total_revenue"].sum()))

st.divider()

# --- Detail table + charts -----------------------------------------------
st.subheader("By region")
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

left, right = st.columns(2)
with left:
    st.caption("Revenue by region")
    st.bar_chart(region_df.set_index("region")["total_revenue"], height=300)
with right:
    st.caption("Profit margin % by region")
    st.bar_chart(region_df.set_index("region")["profit_margin_pct"], height=300)
