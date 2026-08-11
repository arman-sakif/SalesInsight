"""Product Intelligence — product performance and category/margin breakdown."""
import streamlit as st

from _shared import (
    CATEGORIES,
    category_breakdown,
    discount_impact,
    page_setup,
    product_performance,
    to_frame,
)

page_setup("Product Intelligence", "📦")

category_label = st.sidebar.selectbox("Category", ["All"] + CATEGORIES)
category = None if category_label == "All" else category_label
n = st.sidebar.slider("Top N products", min_value=5, max_value=50, value=10, step=5)

# --- Top products ---------------------------------------------------------
st.subheader(f"Top {n} products" + (f" — {category}" if category else ""))
prod_df = to_frame(product_performance(category, n))
if prod_df.empty:
    st.info("No products for that filter.")
else:
    st.dataframe(
        prod_df.rename(
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
        hide_index=True,
        use_container_width=True,
    )
    st.bar_chart(prod_df.set_index("product_name")["total_revenue"], height=320)

st.divider()

# --- Category / sub-category margins -------------------------------------
st.subheader("Category & sub-category margins")
cat_df = to_frame(category_breakdown())
if not cat_df.empty:
    left, right = st.columns([3, 2])
    with left:
        st.dataframe(
            cat_df.rename(
                columns={
                    "category": "Category",
                    "sub_category": "Sub-category",
                    "total_revenue": "Revenue",
                    "margin_pct": "Margin %",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        by_cat = cat_df.groupby("category", as_index=True)["total_revenue"].sum()
        st.caption("Revenue by category")
        st.bar_chart(by_cat, height=300)

st.divider()

# --- Discount vs. margin --------------------------------------------------
st.subheader("Discount impact on margin")
st.caption(
    "Order lines grouped into discount bands. Margin falls as discounts deepen — "
    "beyond ~20% off, average margin turns negative. All-time."
)
disc_df = to_frame(discount_impact())
if not disc_df.empty:
    # Preserve the band ordering returned by the tool (0% → 30%+).
    disc_df = disc_df.set_index("discount_band")
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(
            disc_df.rename(
                columns={
                    "order_lines": "Order lines",
                    "total_revenue": "Revenue",
                    "avg_margin_pct": "Avg margin %",
                    "total_profit": "Profit",
                }
            ),
            use_container_width=True,
        )
    with right:
        st.caption("Average profit margin % by discount band")
        st.bar_chart(disc_df["avg_margin_pct"], height=300)
