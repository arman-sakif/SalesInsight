"""Customer Intelligence — top customers and RFM segmentation."""
import streamlit as st

from _shared import money, page_setup, period_selector, rfm_segments, to_frame, top_customers

page_setup("Customer Intelligence", "🧑‍💼")

period = period_selector()
n = st.sidebar.slider("Top N customers", min_value=5, max_value=50, value=10, step=5)

# --- Top customers --------------------------------------------------------
st.subheader(f"Top {n} customers by revenue")
cust_df = to_frame(top_customers(n, period))
if cust_df.empty:
    st.info("No data for the selected period.")
else:
    st.dataframe(
        cust_df.rename(
            columns={
                "customer_name": "Customer",
                "rfm_segment": "RFM segment",
                "total_revenue": "Revenue",
                "total_orders": "Orders",
                "total_profit": "Profit",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.bar_chart(cust_df.set_index("customer_name")["total_revenue"], height=320)

st.divider()

# --- RFM segments (all-time, matches the tool) ---------------------------
st.subheader("RFM segmentation")
st.caption("Recency / Frequency / Monetary segments from the intermediate model. All-time.")
rfm_df = to_frame(rfm_segments())
if not rfm_df.empty:
    total_customers = int(rfm_df["customer_count"].sum())
    total_revenue = rfm_df["total_revenue"].sum()
    c1, c2 = st.columns(2)
    c1.metric("Customers", f"{total_customers:,}")
    c2.metric("Revenue (all segments)", money(total_revenue))

    left, right = st.columns([3, 2])
    with left:
        st.dataframe(
            rfm_df.rename(
                columns={
                    "rfm_segment": "Segment",
                    "customer_count": "Customers",
                    "total_revenue": "Revenue",
                    "avg_customer_value": "Avg customer value",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.bar_chart(rfm_df.set_index("rfm_segment")["customer_count"], height=320)
