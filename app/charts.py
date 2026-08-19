"""Altair chart builders for the SalesInsight dashboard.

One module so every visual in the app shares a single system: the same palette,
the same mark weights, the same axis chrome. Altair ships with Streamlit, so
this adds no dependency.

**Colour is assigned, not picked.** The categorical hues below are a validated
eight-slot order -- every adjacent pair clears a colour-vision-deficiency
separation threshold and a normal-vision floor against the light surface this
app renders on (see .streamlit/config.toml). Two rules follow from that and are
worth stating because breaking either is easy and silent:

* Slots are assigned in fixed order and never cycled. A ninth series folds into
  "Other" rather than getting a generated hue.
* Colour follows the entity, not its rank. Every categorical scale here pins an
  explicit ``domain``, so filtering a region out cannot repaint the survivors.

Charts are built with ``theme=None`` at the call site so these colours reach the
browser unmodified; the axis and grid chrome that Streamlit's own theme would
otherwise supply is set here instead.
"""
import altair as alt
import pandas as pd

# --- Palette -------------------------------------------------------------
# Categorical slots, in the validated order.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#4a3aa7",
    "#e34948",
)
CATEGORICAL = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

# Single hue, light to dark, for continuous magnitude.
SEQUENTIAL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
]

# Chart chrome. Text never wears a series colour -- identity comes from the
# coloured mark beside it.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
DE_EMPHASIS = "#898781"  # context series, when one series is the story

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
MONEY = "$,.0f"
PERCENT = ".1f"

# Regions get fixed slots so a region keeps its colour under any filter.
REGION_ORDER = ["West", "East", "Central", "South"]
REGION_COLORS = [BLUE, ORANGE, AQUA, YELLOW]
CATEGORY_ORDER = ["Furniture", "Office Supplies", "Technology"]
CATEGORY_COLORS = [BLUE, ORANGE, AQUA]


def _style(chart: alt.Chart) -> alt.Chart:
    """Apply the shared chrome: hairline solid grid, recessive axes, sans text."""
    return (
        chart.configure_view(strokeWidth=0, fill=SURFACE)
        .configure_axis(
            grid=True,
            gridColor=GRID,
            gridWidth=1,
            domainColor=AXIS,
            tickColor=AXIS,
            labelColor=INK_MUTED,
            titleColor=INK_SECONDARY,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
        )
        .configure_legend(
            labelColor=INK_SECONDARY,
            titleColor=INK_SECONDARY,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            symbolType="stroke",
            symbolStrokeWidth=3,
        )
        .configure_text(font=FONT, color=INK)
        .configure_title(font=FONT, color=INK, fontSize=13, anchor="start")
    )


def _empty(message: str) -> alt.Chart:
    """A placeholder that says why a panel is blank, rather than rendering axes
    over no data."""
    return _style(
        alt.Chart(pd.DataFrame({"msg": [message]}))
        .mark_text(align="center", color=INK_MUTED, fontSize=13, font=FONT)
        .encode(text="msg:N")
        .properties(height=120)
    )


# --- Time series ---------------------------------------------------------

def revenue_trend(
    df: pd.DataFrame,
    grain: str = "day",
    show_rolling: bool = True,
    height: int = 300,
) -> alt.Chart:
    """Revenue over time, with the rolling average as the emphasised series.

    Two marks, one measure: the raw series is context (de-emphasis grey) and the
    trailing average carries the story (blue). That is emphasis rather than a
    two-colour categorical pair -- the reader is not being asked to tell two
    subjects apart, they are being shown the signal through the noise.
    """
    if df.empty:
        return _empty("No orders in this selection.")

    time_title = "Date" if grain == "day" else "Month"
    time_format = "%d %b" if grain == "day" else "%b %Y"
    has_rolling = show_rolling and "revenue_rolling" in df.columns

    x = alt.X(
        "period_start:T",
        title=time_title,
        axis=alt.Axis(format=time_format, labelAngle=0, tickCount=8),
    )
    tooltip = [
        alt.Tooltip("period_start:T", title=time_title, format="%d %b %Y"),
        alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
        alt.Tooltip("profit:Q", title="Profit", format=MONEY),
        alt.Tooltip("orders:Q", title="Orders", format=","),
    ]
    if has_rolling:
        tooltip.insert(2, alt.Tooltip("revenue_rolling:Q", title="7-period average", format=MONEY))

    base = alt.Chart(df)
    # Area wash at ~10% under the raw series -- never a saturated block.
    area = base.mark_area(
        color=BLUE if not has_rolling else DE_EMPHASIS, opacity=0.10
    ).encode(x=x, y=alt.Y("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")))

    raw = base.mark_line(
        strokeWidth=2 if not has_rolling else 1.5,
        color=BLUE if not has_rolling else DE_EMPHASIS,
        interpolate="monotone",
        strokeJoin="round",
        strokeCap="round",
    ).encode(x=x, y=alt.Y("revenue:Q", title="Revenue"))

    layers = [area, raw]
    if has_rolling:
        layers.append(
            base.mark_line(
                strokeWidth=2, color=BLUE, strokeJoin="round", strokeCap="round"
            ).encode(x=x, y=alt.Y("revenue_rolling:Q", title="Revenue"))
        )

    # Crosshair + tooltip: a value must be readable at every x, not only where
    # a marker happens to sit.
    hover = alt.selection_point(
        fields=["period_start"], nearest=True, on="pointerover", empty=False, clear="pointerout"
    )
    rule = (
        base.mark_rule(color=AXIS, strokeWidth=1)
        .encode(x=x, opacity=alt.condition(hover, alt.value(1), alt.value(0)), tooltip=tooltip)
        .add_params(hover)
    )
    point = base.mark_point(
        size=90, filled=True, color=BLUE, stroke=SURFACE, strokeWidth=2
    ).encode(
        x=x,
        y=alt.Y("revenue_rolling:Q" if has_rolling else "revenue:Q"),
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )
    layers += [rule, point]

    chart = alt.layer(*layers).properties(height=height)
    if has_rolling:
        # Two marks of the same measure: a legend box would restate the title,
        # so identity rides a caption at the call site instead. Where a real
        # legend is needed (multi-series charts below) it is always present.
        pass
    return _style(chart)


def revenue_vs_profit(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Revenue and profit on one axis over time.

    Both are dollars, so they share a scale honestly -- this is deliberately not
    a dual-axis chart. Profit is small against revenue and that gap is the
    point: it is the margin story, and a second y-scale would flatten it into a
    fake correlation.
    """
    if df.empty:
        return _empty("No orders in this selection.")

    long = df.melt(
        id_vars=["period_start"],
        value_vars=["revenue", "profit"],
        var_name="measure",
        value_name="amount",
    )
    long["measure"] = long["measure"].map({"revenue": "Revenue", "profit": "Profit"})

    color = alt.Color(
        "measure:N",
        title=None,
        scale=alt.Scale(domain=["Revenue", "Profit"], range=[BLUE, ORANGE]),
        legend=alt.Legend(orient="top", direction="horizontal", offset=4),
    )
    chart = (
        alt.Chart(long)
        .mark_line(strokeWidth=2, strokeJoin="round", strokeCap="round", interpolate="monotone")
        .encode(
            x=alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y", labelAngle=0)),
            y=alt.Y("amount:Q", title="Amount", axis=alt.Axis(format="$,.0s")),
            color=color,
            tooltip=[
                alt.Tooltip("period_start:T", title="Month", format="%b %Y"),
                alt.Tooltip("measure:N", title="Measure"),
                alt.Tooltip("amount:Q", title="Amount", format=MONEY),
            ],
        )
        .properties(height=height)
    )
    return _style(chart)


# --- Geography -----------------------------------------------------------

# us-atlas keys its state features by two-digit FIPS. The dataset carries state
# names, so the join needs this map. Kept here rather than in the query layer:
# it is a property of the basemap, not of the warehouse.
_STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38", "Ohio": "39",
    "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44",
    "South Carolina": "45", "South Dakota": "46", "Tennessee": "47", "Texas": "48",
    "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
}

_US_STATES_TOPOJSON = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"


def state_choropleth(df: pd.DataFrame, height: int = 380) -> alt.Chart:
    """Revenue by US state.

    Sequential single hue: the value is magnitude, so more revenue is darker.
    The states with no orders stay at the surface-adjacent base tint rather than
    disappearing, so "we don't sell here" is visible instead of ambiguous.

    The basemap is fetched by the browser from a CDN at render time -- the only
    external request the app makes. The state table beside it carries every
    value, so the panel still answers the question if that request fails.
    """
    if df.empty:
        return _empty("No orders in this selection.")

    data = df.copy()
    data["fips"] = data["state"].map(_STATE_FIPS)
    data = data.dropna(subset=["fips"])

    states = alt.topo_feature(_US_STATES_TOPOJSON, "states")
    chart = (
        alt.Chart(states)
        .mark_geoshape(stroke=SURFACE, strokeWidth=1)
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(
                data, "fips", ["state", "region", "revenue", "profit", "orders", "margin_pct"]
            ),
        )
        .encode(
            color=alt.Color(
                "revenue:Q",
                title="Revenue",
                scale=alt.Scale(range=SEQUENTIAL, type="sqrt"),
                legend=alt.Legend(format="$,.0s", orient="right", gradientLength=200),
            ),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
                alt.Tooltip("profit:Q", title="Profit", format=MONEY),
                alt.Tooltip("margin_pct:Q", title="Margin %", format=PERCENT),
                alt.Tooltip("orders:Q", title="Orders", format=","),
            ],
        )
        .project(type="albersUsa")
        .properties(height=height)
    )
    return _style(chart)


def region_bars(df: pd.DataFrame, height: int = 260) -> alt.Chart:
    """Revenue by region: one series, so one colour and no legend.

    A value ramp across four nominal regions would double-encode bar length as
    hue and spend the only free channel on information the bars already carry.
    """
    if df.empty:
        return _empty("No orders in this selection.")

    base = alt.Chart(df).encode(
        y=alt.Y("region:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=12)),
        x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
    )
    bars = base.mark_bar(color=BLUE, height=20, cornerRadiusEnd=4).encode(
        tooltip=[
            alt.Tooltip("region:N", title="Region"),
            alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
            alt.Tooltip("total_profit:Q", title="Profit", format=MONEY),
            alt.Tooltip("profit_margin_pct:Q", title="Margin %", format=PERCENT),
            alt.Tooltip("total_orders:Q", title="Orders", format=","),
        ]
    )
    # Four bars, so every one can carry its value without becoming noise.
    labels = base.mark_text(
        align="left", dx=6, color=INK_SECONDARY, fontSize=11, font=FONT
    ).encode(text=alt.Text("total_revenue:Q", format=MONEY))
    return _style(alt.layer(bars, labels).properties(height=height))


# --- Customers -----------------------------------------------------------

def rfm_heatmap(df: pd.DataFrame, height: int = 320) -> alt.Chart:
    """Recency x frequency grid, shaded by revenue.

    A grid of magnitude, so: sequential hue, and the customer count printed in
    each cell. The label colour flips by cell luminance so it always clears
    contrast against its own fill.
    """
    if df.empty:
        return _empty("No customers in this selection.")

    base = alt.Chart(df).encode(
        x=alt.X(
            "f_score:O",
            title="Frequency score  (1 = fewest orders, 4 = most)",
            axis=alt.Axis(labelAngle=0),
        ),
        y=alt.Y(
            "r_score:O",
            title="Recency score  (4 = most recent)",
            sort="descending",
        ),
    )
    cells = base.mark_rect(stroke=SURFACE, strokeWidth=2, cornerRadius=4).encode(
        color=alt.Color(
            "revenue:Q",
            title="Revenue",
            scale=alt.Scale(range=SEQUENTIAL),
            legend=alt.Legend(format="$,.0s", gradientLength=180),
        ),
        tooltip=[
            alt.Tooltip("r_score:O", title="Recency score"),
            alt.Tooltip("f_score:O", title="Frequency score"),
            alt.Tooltip("example_segment:N", title="Typical segment"),
            alt.Tooltip("customers:Q", title="Customers", format=","),
            alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
        ],
    )
    midpoint = df["revenue"].max() * 0.55 if not df.empty else 0
    labels = base.mark_text(fontSize=11, font=FONT).encode(
        text=alt.Text("customers:Q", format=","),
        color=alt.condition(
            alt.datum.revenue > midpoint, alt.value(SURFACE), alt.value(INK_SECONDARY)
        ),
    )
    return _style(alt.layer(cells, labels).properties(height=height))


# --- Products ------------------------------------------------------------

def pareto_curve(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Cumulative share of revenue by product rank.

    Deliberately *not* the textbook Pareto combo chart: bars of revenue against
    a cumulative percentage line needs two y-scales, and the alignment between
    them is arbitrary. The cumulative curve alone is the part that answers the
    question, and the ranked table beside it carries the per-product revenue.
    """
    if df.empty:
        return _empty("No products in this selection.")

    x = alt.X("rank:Q", title="Products, ranked by revenue")
    line = (
        alt.Chart(df)
        .mark_line(strokeWidth=2, color=BLUE, strokeJoin="round", strokeCap="round")
        .encode(
            x=x,
            y=alt.Y(
                "cumulative_pct:Q",
                title="Cumulative share of revenue",
                axis=alt.Axis(format=".0f", values=[0, 20, 40, 60, 80, 100]),
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                alt.Tooltip("rank:Q", title="Rank"),
                alt.Tooltip("product_name:N", title="Product"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
                alt.Tooltip("cumulative_pct:Q", title="Cumulative %", format=PERCENT),
            ],
        )
    )
    area = (
        alt.Chart(df)
        .mark_area(color=BLUE, opacity=0.10)
        .encode(x=x, y=alt.Y("cumulative_pct:Q", scale=alt.Scale(domain=[0, 100])))
    )
    # A single reference line, solid hairline -- the 80% mark is the one value
    # a reader looks for on this chart.
    rule = (
        alt.Chart(pd.DataFrame({"y": [80]}))
        .mark_rule(color=INK_MUTED, strokeWidth=1)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])))
    )
    label = (
        alt.Chart(pd.DataFrame({"y": [80], "t": ["80% of revenue"]}))
        .mark_text(align="left", dx=6, dy=-6, color=INK_MUTED, fontSize=11, font=FONT)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])), text="t:N")
    )
    return _style(alt.layer(area, line, rule, label).properties(height=height))


def discount_margin(df: pd.DataFrame, height: int = 300) -> alt.Chart:
    """Profit margin by discount depth, with a zero-margin reference rule.

    The value has a sign, so the colour job is diverging: blue above zero, red
    below, meeting at a neutral baseline. This is the one chart in the app where
    colour carries polarity rather than identity or magnitude.
    """
    if df.empty:
        return _empty("No order lines in this selection.")

    base = alt.Chart(df).encode(
        x=alt.X(
            "discount_pct:Q",
            title="Discount applied (%)",
            axis=alt.Axis(format=".0f", labelAngle=0),
            scale=alt.Scale(nice=False, padding=12),
        ),
        y=alt.Y("margin_pct:Q", title="Profit margin (%)", axis=alt.Axis(format=".0f")),
    )
    bars = base.mark_bar(width=14, cornerRadiusEnd=4).encode(
        color=alt.condition(alt.datum.margin_pct >= 0, alt.value(BLUE), alt.value(RED)),
        tooltip=[
            alt.Tooltip("discount_pct:Q", title="Discount band start (%)", format=".0f"),
            alt.Tooltip("margin_pct:Q", title="Margin %", format=PERCENT),
            alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
            alt.Tooltip("profit:Q", title="Profit", format=MONEY),
            alt.Tooltip("order_lines:Q", title="Order lines", format=","),
        ],
    )
    zero = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color=AXIS, strokeWidth=1)
        .encode(y="y:Q")
    )
    return _style(alt.layer(bars, zero).properties(height=height))


def category_heatmap(df: pd.DataFrame, height: int = 340) -> alt.Chart:
    """Revenue by category x sub-category.

    Seventeen sub-categories is well past the point where colour can carry
    identity, so the grid carries it: position names the cell, and the single
    hue carries magnitude.
    """
    if df.empty:
        return _empty("No products in this selection.")

    return _style(
        alt.Chart(df)
        .mark_rect(stroke=SURFACE, strokeWidth=2, cornerRadius=4)
        .encode(
            x=alt.X("category:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
            y=alt.Y("sub_category:N", title=None, sort="-x"),
            color=alt.Color(
                "total_revenue:Q",
                title="Revenue",
                scale=alt.Scale(range=SEQUENTIAL),
                legend=alt.Legend(format="$,.0s", gradientLength=200),
            ),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("sub_category:N", title="Sub-category"),
                alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
                alt.Tooltip("margin_pct:Q", title="Margin %", format=PERCENT),
                alt.Tooltip("avg_discount_pct:Q", title="Avg discount %", format=PERCENT),
            ],
        )
        .properties(height=height)
    )


def top_products_bars(df: pd.DataFrame, height: int = 340) -> alt.Chart:
    """Top products by revenue, coloured by category.

    Three categories, so colour can carry identity here -- with an explicit
    domain, so a category filter never repaints the survivors.
    """
    if df.empty:
        return _empty("No products in this selection.")

    return _style(
        alt.Chart(df)
        .mark_bar(height=16, cornerRadiusEnd=4)
        .encode(
            y=alt.Y("product_name:N", title=None, sort="-x", axis=alt.Axis(labelLimit=280)),
            x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
            color=alt.Color(
                "category:N",
                title=None,
                scale=alt.Scale(domain=CATEGORY_ORDER, range=CATEGORY_COLORS),
                legend=alt.Legend(orient="top", direction="horizontal", offset=4),
            ),
            tooltip=[
                alt.Tooltip("product_name:N", title="Product"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("sub_category:N", title="Sub-category"),
                alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
                alt.Tooltip("total_profit:Q", title="Profit", format=MONEY),
                alt.Tooltip("avg_discount_pct:Q", title="Avg discount %", format=PERCENT),
            ],
        )
        .properties(height=height)
    )


def segment_revenue_bars(df: pd.DataFrame, height: int = 240) -> alt.Chart:
    """Revenue by RFM segment: one measure, one hue, values direct-labelled."""
    if df.empty:
        return _empty("No customers in this selection.")

    base = alt.Chart(df).encode(
        y=alt.Y("rfm_segment:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=12)),
        x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
    )
    bars = base.mark_bar(color=BLUE, height=20, cornerRadiusEnd=4).encode(
        tooltip=[
            alt.Tooltip("rfm_segment:N", title="Segment"),
            alt.Tooltip("customer_count:Q", title="Customers", format=","),
            alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
            alt.Tooltip("avg_customer_value:Q", title="Avg lifetime value", format=MONEY),
        ]
    )
    labels = base.mark_text(
        align="left", dx=6, color=INK_SECONDARY, fontSize=11, font=FONT
    ).encode(text=alt.Text("total_revenue:Q", format=MONEY))
    return _style(alt.layer(bars, labels).properties(height=height))
