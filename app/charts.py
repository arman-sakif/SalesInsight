"""Altair chart builders for the SalesInsight dashboard.

One module so every visual in the app shares a single system: the same palette,
the same mark weights, the same axis chrome. Altair ships with Streamlit, so
this adds no dependency.

**Colour is assigned, not picked.** The categorical hues below are a validated
eight-slot order -- every adjacent pair clears a colour-vision-deficiency
separation threshold and a normal-vision floor against the surface it renders
on. Two rules follow from that and are worth stating because breaking either is
easy and silent:

* Slots are assigned in fixed order and never cycled. A ninth series folds into
  "Other" rather than getting a generated hue.
* Colour follows the entity, not its rank. Every categorical scale here pins an
  explicit ``domain``, so filtering a region out cannot repaint the survivors.

**Two palettes, one per theme.** A dark palette is not an inversion of a light
one -- it is its own set of steps, re-validated against the dark surface -- so
:data:`LIGHT` and :data:`DARK` are declared separately and picked by
:func:`palette` from the ``mode`` each builder is called with. Streamlit's own
``chartCategoricalColors``/``chartSequentialColors`` config options have no
per-mode variant, which is why the choice is made here in Python instead: this
module sets every colour explicitly and the app renders with ``theme=None``, so
that config limit only governs Streamlit's built-in chart elements, which this
app does not use. The caller resolves the mode (see ``app._shared.chart_mode``);
this module deliberately imports no Streamlit.

Charts are built with ``theme=None`` at the call site so these colours reach the
browser unmodified; the axis and grid chrome that Streamlit's own theme would
otherwise supply is set here instead.
"""
from dataclasses import dataclass

import altair as alt
import pandas as pd

# --- Palette -------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    """One theme's worth of colour: eight categorical slots, a sequential ramp,
    and the chrome the marks sit on."""

    mode: str
    categorical: tuple[str, ...]
    sequential: tuple[str, ...]
    surface: str
    ink: str
    ink_secondary: str
    ink_muted: str
    grid: str
    axis: str

    # Named slots, so a chart can ask for "the blue one" rather than index a
    # tuple and leave the reader to count.
    @property
    def blue(self) -> str:
        return self.categorical[0]

    @property
    def orange(self) -> str:
        return self.categorical[1]

    @property
    def aqua(self) -> str:
        return self.categorical[2]

    @property
    def yellow(self) -> str:
        return self.categorical[3]

    @property
    def red(self) -> str:
        return self.categorical[7]

    @property
    def de_emphasis(self) -> str:
        """Context series, when one series is the story."""
        return self.ink_muted

    @property
    def region_colors(self) -> list[str]:
        return list(self.categorical[:4])

    @property
    def category_colors(self) -> list[str]:
        return list(self.categorical[:3])


# Light: validated against the #fcfcfb surface.
LIGHT = Palette(
    mode="light",
    categorical=(
        "#2a78d6",  # 1 blue
        "#eb6834",  # 2 orange
        "#1baf7a",  # 3 aqua
        "#eda100",  # 4 yellow
        "#e87ba4",  # 5 magenta
        "#008300",  # 6 green
        "#4a3aa7",  # 7 violet
        "#e34948",  # 8 red
    ),
    # Single hue, light to dark: more is darker against a light page.
    sequential=(
        "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
        "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    ),
    surface="#fcfcfb",
    ink="#0b0b0b",
    ink_secondary="#52514e",
    ink_muted="#898781",
    grid="#e1e0d9",
    axis="#c3c2b7",
)

# Dark: re-validated against the #1a1a19 surface rather than derived from the
# light steps. Worst adjacent separation under simulated colour-vision
# deficiency 8.4 dE, normal vision 19.8, and the four hues that sit below 3:1
# against the light page all clear it against this one.
DARK = Palette(
    mode="dark",
    categorical=(
        "#3987e5",  # 1 blue
        "#d95926",  # 2 orange
        "#199e70",  # 3 aqua
        "#c98500",  # 4 yellow
        "#d55181",  # 5 magenta
        "#008300",  # 6 green
        "#9085e9",  # 7 violet
        "#e66767",  # 8 red
    ),
    # The same ramp read the other way. On a dark surface more has to be
    # *lighter*, or magnitude runs backwards against the background.
    sequential=tuple(reversed(LIGHT.sequential)),
    surface="#1a1a19",
    ink="#ffffff",
    ink_secondary="#c3c2b7",
    ink_muted="#898781",
    grid="#2c2c2a",
    axis="#383835",
)

PALETTES = {"light": LIGHT, "dark": DARK}
DEFAULT_MODE = "light"


def palette(mode: str | Palette | None = None) -> Palette:
    """Resolve a theme name to its palette, defaulting to light.

    Anything unrecognised -- including the ``None`` Streamlit reports while a
    theme is still settling -- falls back to light rather than raising. A chart
    drawn in the wrong palette for one frame is a cosmetic problem; a chart that
    raises is a broken page.
    """
    if isinstance(mode, Palette):
        return mode
    return PALETTES.get(mode or DEFAULT_MODE, LIGHT)


FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
MONEY = "$,.0f"
PERCENT = ".1f"

# Regions and categories get fixed slots so either keeps its colour under any
# filter; the hues themselves come from whichever palette is in play.
REGION_ORDER = ["West", "East", "Central", "South"]
CATEGORY_ORDER = ["Furniture", "Office Supplies", "Technology"]


def _style(chart: alt.Chart, p: Palette) -> alt.Chart:
    """Apply the shared chrome: hairline solid grid, recessive axes, sans text."""
    return (
        chart.configure_view(strokeWidth=0, fill=p.surface)
        .configure_axis(
            grid=True,
            gridColor=p.grid,
            gridWidth=1,
            domainColor=p.axis,
            tickColor=p.axis,
            labelColor=p.ink_muted,
            titleColor=p.ink_secondary,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
        )
        .configure_legend(
            labelColor=p.ink_secondary,
            titleColor=p.ink_secondary,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            symbolType="stroke",
            symbolStrokeWidth=3,
        )
        .configure_text(font=FONT, color=p.ink)
        .configure_title(font=FONT, color=p.ink, fontSize=13, anchor="start")
    )


def _empty(message: str, p: Palette) -> alt.Chart:
    """A placeholder that says why a panel is blank, rather than rendering axes
    over no data."""
    return _style(
        alt.Chart(pd.DataFrame({"msg": [message]}))
        .mark_text(align="center", color=p.ink_muted, fontSize=13, font=FONT)
        .encode(text="msg:N")
        .properties(height=120),
        p,
    )


def _crosshair(
    p: Palette,
    *,
    data: pd.DataFrame,
    x: alt.X,
    field: str,
    tooltip: list,
    y: alt.Y | None = None,
    point_data: pd.DataFrame | None = None,
    point_color: str | None = None,
    color: alt.Color | None = None,
) -> list:
    """A nearest-point hover: a full-height rule carrying the tooltip, plus a dot.

    A line is a 2px target, and asking a reader to land on one is not a tooltip.
    Every line chart here gets its values through this instead: the
    invisible-until-hovered ``rule`` spans the full plot height, so anywhere in
    the column reads that x.

    Hanging the tooltip on the rule rather than on the marks also makes it
    *shared* -- every series at that x arrives in one tooltip, instead of
    whichever line the cursor happened to be nearest.
    """
    hover = alt.selection_point(
        fields=[field], nearest=True, on="pointerover", empty=False, clear="pointerout"
    )
    rule = (
        alt.Chart(data)
        .mark_rule(color=p.axis, strokeWidth=1)
        .encode(x=x, opacity=alt.condition(hover, alt.value(1), alt.value(0)), tooltip=tooltip)
        .add_params(hover)
    )
    layers = [rule]

    if y is not None:
        # The 2px ring around the dot is the surface colour, so the dot reads as
        # sitting on the page rather than merging into the line under it. That
        # is why the ring has to follow the theme as well.
        mark = {"size": 90, "filled": True, "stroke": p.surface, "strokeWidth": 2}
        if color is None:
            mark["color"] = point_color or p.blue
        dot = alt.Chart(point_data if point_data is not None else data).mark_point(**mark)
        encodings = {
            "x": x,
            "y": y,
            "opacity": alt.condition(hover, alt.value(1), alt.value(0)),
        }
        if color is not None:
            encodings["color"] = color
        layers.append(dot.encode(**encodings))

    return layers


# --- Time series ---------------------------------------------------------

def revenue_trend(
    df: pd.DataFrame,
    grain: str = "day",
    show_rolling: bool = True,
    height: int = 300,
    mode: str | None = None,
) -> alt.Chart:
    """Revenue over time, with the rolling average as the emphasised series.

    Two marks, one measure: the raw series is context (de-emphasis grey) and the
    trailing average carries the story (blue). That is emphasis rather than a
    two-colour categorical pair -- the reader is not being asked to tell two
    subjects apart, they are being shown the signal through the noise.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No orders in this selection.", p)

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
        color=p.blue if not has_rolling else p.de_emphasis, opacity=0.10
    ).encode(x=x, y=alt.Y("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")))

    raw = base.mark_line(
        strokeWidth=2 if not has_rolling else 1.5,
        color=p.blue if not has_rolling else p.de_emphasis,
        interpolate="monotone",
        strokeJoin="round",
        strokeCap="round",
    ).encode(x=x, y=alt.Y("revenue:Q", title="Revenue"))

    layers = [area, raw]
    if has_rolling:
        layers.append(
            base.mark_line(
                strokeWidth=2, color=p.blue, strokeJoin="round", strokeCap="round"
            ).encode(x=x, y=alt.Y("revenue_rolling:Q", title="Revenue"))
        )

    # Crosshair + tooltip: a value must be readable at every x, not only where
    # a marker happens to sit.
    layers += _crosshair(
        p,
        data=df,
        x=x,
        field="period_start",
        tooltip=tooltip,
        y=alt.Y("revenue_rolling:Q" if has_rolling else "revenue:Q"),
    )

    chart = alt.layer(*layers).properties(height=height)
    if has_rolling:
        # Two marks of the same measure: a legend box would restate the title,
        # so identity rides a caption at the call site instead. Where a real
        # legend is needed (multi-series charts below) it is always present.
        pass
    return _style(chart, p)


def revenue_vs_profit(
    df: pd.DataFrame, height: int = 300, mode: str | None = None
) -> alt.Chart:
    """Revenue and profit on one axis over time.

    Both are dollars, so they share a scale honestly -- this is deliberately not
    a dual-axis chart. Profit is small against revenue and that gap is the
    point: it is the margin story, and a second y-scale would flatten it into a
    fake correlation.

    Because the gap is the subject, the crosshair reads *both* series at the
    hovered month rather than whichever line the pointer is nearest. A per-mark
    tooltip would answer half the question the chart exists to ask.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No orders in this selection.", p)

    long = df.melt(
        id_vars=["period_start"],
        value_vars=["revenue", "profit"],
        var_name="measure",
        value_name="amount",
    )
    long["measure"] = long["measure"].map({"revenue": "Revenue", "profit": "Profit"})

    x = alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y", labelAngle=0))
    y = alt.Y("amount:Q", title="Amount", axis=alt.Axis(format="$,.0s"))
    color = alt.Color(
        "measure:N",
        title=None,
        scale=alt.Scale(domain=["Revenue", "Profit"], range=[p.blue, p.orange]),
        legend=alt.Legend(orient="top", direction="horizontal", offset=4),
    )
    lines = (
        alt.Chart(long)
        .mark_line(strokeWidth=2, strokeJoin="round", strokeCap="round", interpolate="monotone")
        .encode(x=x, y=y, color=color)
    )
    # The rule reads the wide frame, which is what lets one tooltip name both
    # measures at the same x; the dots read the long one, so each series gets
    # its own marker in its own colour.
    hover = _crosshair(
        p,
        data=df,
        x=x,
        field="period_start",
        tooltip=[
            alt.Tooltip("period_start:T", title="Month", format="%b %Y"),
            alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
            alt.Tooltip("profit:Q", title="Profit", format=MONEY),
        ],
        y=y,
        point_data=long,
        color=color,
    )
    return _style(alt.layer(lines, *hover).properties(height=height), p)


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


def state_choropleth(
    df: pd.DataFrame, height: int = 380, mode: str | None = None
) -> alt.Chart:
    """Revenue by US state.

    Sequential single hue: the value is magnitude, so more revenue reads further
    from the page -- darker on the light theme, lighter on the dark one. States
    with no orders stay at the base tint rather than disappearing, so "we don't
    sell here" is visible instead of ambiguous.

    The basemap is fetched by the browser from a CDN at render time -- the only
    external request the app makes. The state table beside it carries every
    value, so the panel still answers the question if that request fails.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No orders in this selection.", p)

    data = df.copy()
    data["fips"] = data["state"].map(_STATE_FIPS)
    data = data.dropna(subset=["fips"])

    states = alt.topo_feature(_US_STATES_TOPOJSON, "states")
    chart = (
        alt.Chart(states)
        # The 1px border between states is the surface colour, so it follows the
        # theme; a fixed light hairline would glow against the dark page.
        .mark_geoshape(stroke=p.surface, strokeWidth=1)
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
                scale=alt.Scale(range=list(p.sequential), type="sqrt"),
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
    return _style(chart, p)


def region_bars(
    df: pd.DataFrame, height: int = 260, mode: str | None = None
) -> alt.Chart:
    """Revenue by region: one series, so one colour and no legend.

    A value ramp across four nominal regions would double-encode bar length as
    hue and spend the only free channel on information the bars already carry.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No orders in this selection.", p)

    tooltip = [
        alt.Tooltip("region:N", title="Region"),
        alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
        alt.Tooltip("total_profit:Q", title="Profit", format=MONEY),
        alt.Tooltip("profit_margin_pct:Q", title="Margin %", format=PERCENT),
        alt.Tooltip("total_orders:Q", title="Orders", format=","),
    ]
    base = alt.Chart(df).encode(
        y=alt.Y("region:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=12)),
        x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
    )
    bars = base.mark_bar(color=p.blue, height=20, cornerRadiusEnd=4).encode(tooltip=tooltip)
    # Four bars, so every one can carry its value without becoming noise. The
    # label repeats its bar's tooltip: a pointer crossing from the bar onto the
    # text beside it should not make the tooltip blink out.
    labels = base.mark_text(
        align="left", dx=6, color=p.ink_secondary, fontSize=11, font=FONT
    ).encode(text=alt.Text("total_revenue:Q", format=MONEY), tooltip=tooltip)
    return _style(alt.layer(bars, labels).properties(height=height), p)


# --- Customers -----------------------------------------------------------

def rfm_heatmap(
    df: pd.DataFrame, height: int = 320, mode: str | None = None
) -> alt.Chart:
    """Recency x frequency grid, shaded by revenue.

    A grid of magnitude, so: sequential hue, and the customer count printed in
    each cell. The label colour flips by cell luminance so it always clears
    contrast against its own fill.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No customers in this selection.", p)

    tooltip = [
        alt.Tooltip("r_score:O", title="Recency score"),
        alt.Tooltip("f_score:O", title="Frequency score"),
        alt.Tooltip("example_segment:N", title="Typical segment"),
        alt.Tooltip("customers:Q", title="Customers", format=","),
        alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
    ]
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
    # The 2px gap between cells is drawn in the surface colour, so it follows
    # the theme too -- a fixed light stroke would glow on the dark page.
    cells = base.mark_rect(stroke=p.surface, strokeWidth=2, cornerRadius=4).encode(
        color=alt.Color(
            "revenue:Q",
            title="Revenue",
            scale=alt.Scale(range=list(p.sequential)),
            legend=alt.Legend(format="$,.0s", gradientLength=180),
        ),
        tooltip=tooltip,
    )
    midpoint = df["revenue"].max() * 0.55 if not df.empty else 0
    # The flip is always against the cell's own fill. On the light ramp the
    # high-revenue cells are the dark ones and want surface-coloured text; on
    # the dark ramp they are the light ones and want ink. Same comparison,
    # opposite pair.
    high, low = (
        (p.surface, p.ink_secondary) if p.mode == "light" else (p.surface, p.ink)
    )
    labels = base.mark_text(fontSize=11, font=FONT).encode(
        text=alt.Text("customers:Q", format=","),
        color=alt.condition(alt.datum.revenue > midpoint, alt.value(high), alt.value(low)),
        tooltip=tooltip,
    )
    return _style(alt.layer(cells, labels).properties(height=height), p)


# --- Products ------------------------------------------------------------

def pareto_curve(
    df: pd.DataFrame, height: int = 300, mode: str | None = None
) -> alt.Chart:
    """Cumulative share of revenue by product rank.

    Deliberately *not* the textbook Pareto combo chart: bars of revenue against
    a cumulative percentage line needs two y-scales, and the alignment between
    them is arbitrary. The cumulative curve alone is the part that answers the
    question, and the ranked table beside it carries the per-product revenue.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No products in this selection.", p)

    x = alt.X("rank:Q", title="Products, ranked by revenue")
    y = alt.Y(
        "cumulative_pct:Q",
        title="Cumulative share of revenue",
        axis=alt.Axis(format=".0f", values=[0, 20, 40, 60, 80, 100]),
        scale=alt.Scale(domain=[0, 100]),
    )
    line = (
        alt.Chart(df)
        .mark_line(strokeWidth=2, color=p.blue, strokeJoin="round", strokeCap="round")
        .encode(x=x, y=y)
    )
    area = (
        alt.Chart(df)
        .mark_area(color=p.blue, opacity=0.10)
        .encode(x=x, y=alt.Y("cumulative_pct:Q", scale=alt.Scale(domain=[0, 100])))
    )
    # A single reference line, solid hairline -- the 80% mark is the one value
    # a reader looks for on this chart.
    rule = (
        alt.Chart(pd.DataFrame({"y": [80]}))
        .mark_rule(color=p.ink_muted, strokeWidth=1)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])))
    )
    label = (
        alt.Chart(pd.DataFrame({"y": [80], "t": ["80% of revenue"]}))
        .mark_text(align="left", dx=6, dy=-6, color=p.ink_muted, fontSize=11, font=FONT)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])), text="t:N")
    )
    # The curve flattens to near-horizontal on the right, where the ranks are
    # densest: without the crosshair, "which product is this?" means landing on
    # a 2px stroke.
    hover = _crosshair(
        p,
        data=df,
        x=x,
        field="rank",
        tooltip=[
            alt.Tooltip("rank:Q", title="Rank"),
            alt.Tooltip("product_name:N", title="Product"),
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
            alt.Tooltip("cumulative_pct:Q", title="Cumulative %", format=PERCENT),
        ],
        y=y,
    )
    return _style(alt.layer(area, line, rule, label, *hover).properties(height=height), p)


def _hit_bands(df: pd.DataFrame, field: str, default_width: float = 5.0) -> pd.DataFrame:
    """Add the right-hand edge of each bucket, for a full-band hit area.

    The width is read off the data rather than assumed, so re-bucketing the
    query cannot silently leave gaps between the bands.
    """
    data = df.copy()
    steps = data[field].sort_values().diff().dropna()
    positive = steps[steps > 0]
    width = float(positive.min()) if not positive.empty else default_width
    data["band_end"] = data[field] + width
    return data


def discount_margin(
    df: pd.DataFrame, height: int = 300, mode: str | None = None
) -> alt.Chart:
    """Profit margin by discount depth, with a zero-margin reference rule.

    The value has a sign, so the colour job is diverging: blue above zero, red
    below, meeting at a neutral baseline. This is the one chart in the app where
    colour carries polarity rather than identity or magnitude.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No order lines in this selection.", p)

    tooltip = [
        alt.Tooltip("discount_pct:Q", title="Discount band start (%)", format=".0f"),
        alt.Tooltip("margin_pct:Q", title="Margin %", format=PERCENT),
        alt.Tooltip("revenue:Q", title="Revenue", format=MONEY),
        alt.Tooltip("profit:Q", title="Profit", format=MONEY),
        alt.Tooltip("order_lines:Q", title="Order lines", format=","),
    ]
    x = alt.X(
        "discount_pct:Q",
        title="Discount applied (%)",
        axis=alt.Axis(format=".0f", labelAngle=0),
        scale=alt.Scale(nice=False, padding=12),
    )
    base = alt.Chart(df).encode(
        x=x,
        y=alt.Y("margin_pct:Q", title="Profit margin (%)", axis=alt.Axis(format=".0f")),
    )
    bars = base.mark_bar(width=14, cornerRadiusEnd=4).encode(
        color=alt.condition(alt.datum.margin_pct >= 0, alt.value(p.blue), alt.value(p.red)),
        tooltip=tooltip,
    )
    zero = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color=p.axis, strokeWidth=1)
        .encode(y="y:Q")
    )
    # The bars are 14px wide on purpose -- they read as a distribution -- but
    # 14px is under the ~24px minimum for a pointer target. So the hit area is
    # widened without widening the mark: an invisible full-height band covering
    # the whole discount bucket, carrying the same tooltip.
    hit = (
        alt.Chart(_hit_bands(df, "discount_pct"))
        .mark_rect(fill=p.surface, fillOpacity=0)
        .encode(x=x, x2="band_end:Q", tooltip=tooltip)
    )
    return _style(alt.layer(bars, zero, hit).properties(height=height), p)


def category_heatmap(
    df: pd.DataFrame, height: int = 340, mode: str | None = None
) -> alt.Chart:
    """Revenue by category x sub-category.

    Seventeen sub-categories is well past the point where colour can carry
    identity, so the grid carries it: position names the cell, and the single
    hue carries magnitude.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No products in this selection.", p)

    return _style(
        alt.Chart(df)
        .mark_rect(stroke=p.surface, strokeWidth=2, cornerRadius=4)
        .encode(
            x=alt.X("category:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
            y=alt.Y("sub_category:N", title=None, sort="-x"),
            color=alt.Color(
                "total_revenue:Q",
                title="Revenue",
                scale=alt.Scale(range=list(p.sequential)),
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
        .properties(height=height),
        p,
    )


def top_products_bars(
    df: pd.DataFrame, height: int = 340, mode: str | None = None
) -> alt.Chart:
    """Top products by revenue, coloured by category.

    Three categories, so colour can carry identity here -- with an explicit
    domain, so a category filter never repaints the survivors.
    """
    p = palette(mode)
    if df.empty:
        return _empty("No products in this selection.", p)

    return _style(
        alt.Chart(df)
        .mark_bar(height=16, cornerRadiusEnd=4)
        .encode(
            y=alt.Y("product_name:N", title=None, sort="-x", axis=alt.Axis(labelLimit=280)),
            x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
            color=alt.Color(
                "category:N",
                title=None,
                scale=alt.Scale(domain=CATEGORY_ORDER, range=p.category_colors),
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
        .properties(height=height),
        p,
    )


def segment_revenue_bars(
    df: pd.DataFrame, height: int = 240, mode: str | None = None
) -> alt.Chart:
    """Revenue by RFM segment: one measure, one hue, values direct-labelled."""
    p = palette(mode)
    if df.empty:
        return _empty("No customers in this selection.", p)

    tooltip = [
        alt.Tooltip("rfm_segment:N", title="Segment"),
        alt.Tooltip("customer_count:Q", title="Customers", format=","),
        alt.Tooltip("total_revenue:Q", title="Revenue", format=MONEY),
        alt.Tooltip("avg_customer_value:Q", title="Avg lifetime value", format=MONEY),
    ]
    base = alt.Chart(df).encode(
        y=alt.Y("rfm_segment:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=12)),
        x=alt.X("total_revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0s")),
    )
    bars = base.mark_bar(color=p.blue, height=20, cornerRadiusEnd=4).encode(tooltip=tooltip)
    labels = base.mark_text(
        align="left", dx=6, color=p.ink_secondary, fontSize=11, font=FONT
    ).encode(text=alt.Text("total_revenue:Q", format=MONEY), tooltip=tooltip)
    return _style(alt.layer(bars, labels).properties(height=height), p)
