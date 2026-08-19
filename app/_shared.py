"""Shared helpers for the Streamlit app.

Every business metric here goes through the same query functions the MCP server
registers (in ``mcp_server/tools``), so the web dashboard, the AI tools, and
Power BI all read one dbt-built semantic layer in DuckDB. Chart-shaped cuts that
no tool answers -- time series, geography, Pareto -- come from ``app.queries``,
which reads the same marts. The ``st.cache_data`` wrappers below exist only to
avoid re-opening the read-only DuckDB connection on every widget interaction.

The filter panel is the other thing this module owns. It is rendered once, from
one place, for every page: a filter that appears on a page must actually reach
every query on it, and the surest way to guarantee that is to stop each page
from inventing its own widgets.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure the repo root is importable so ``mcp_server`` resolves even when the
# app is launched from a context that doesn't put the root on sys.path
# (e.g. Streamlit Community Cloud).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app import queries
from app.queries import ERA_HISTORICAL, ERA_RECENT, to_frame
from mcp_server.tools.customers import get_rfm_segments, get_top_customers
from mcp_server.tools.metrics import METRIC_DEFINITIONS, explain_metric, query_metric
from mcp_server.tools.products import (
    get_category_breakdown,
    get_discount_impact,
    get_product_performance,
)
from mcp_server.tools.regions import revenue_by_region

CATEGORIES = ["Furniture", "Office Supplies", "Technology"]
RFM_SEGMENTS = ["Champions", "Loyal Customers", "Potential Loyalists", "At Risk", "Lost"]

# Widget keys, shared across pages so a selection survives navigation.
_KEY_PERIOD = "flt_period"
_KEY_REGIONS = "flt_regions"
_KEY_CATEGORIES = "flt_categories"
_KEY_SUBCATEGORIES = "flt_subcategories"
_KEY_SEGMENTS = "flt_segments"
_KEY_TOP_N = "flt_top_n"
_ALL_KEYS = (
    _KEY_PERIOD,
    _KEY_REGIONS,
    _KEY_CATEGORIES,
    _KEY_SUBCATEGORIES,
    _KEY_SEGMENTS,
    _KEY_TOP_N,
)


@dataclass(frozen=True)
class Filters:
    """The active filter selection.

    Tuples rather than lists so the whole thing stays hashable and can be passed
    straight into an ``st.cache_data`` function.
    """

    period: str = "all_time"
    period_label: str = "All time"
    regions: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    sub_categories: tuple[str, ...] = ()
    segments: tuple[str, ...] = ()
    top_n: int = 10
    shown: tuple[str, ...] = field(default=())

    @property
    def category(self) -> str | None:
        """The single-category argument ``get_product_performance`` still takes."""
        return self.categories[0] if len(self.categories) == 1 else None

    def describe(self) -> list[str]:
        """Human-readable chips for the filters that are actually narrowing."""
        chips = [self.period_label]
        for label, values in (
            ("Region", self.regions),
            ("Category", self.categories),
            ("Sub-category", self.sub_categories),
            ("Segment", self.segments),
        ):
            if values:
                shown = ", ".join(values[:3])
                if len(values) > 3:
                    shown += f" +{len(values) - 3}"
                chips.append(f"{label}: {shown}")
        return chips


# --- Page chrome ---------------------------------------------------------

def page_setup(title: str, icon: str = "📊") -> None:
    """Apply consistent page config and header."""
    st.set_page_config(page_title=f"SalesInsight — {title}", page_icon=icon, layout="wide")
    st.title(f"{icon} {title}")


def filter_caption(filters: Filters) -> None:
    """Show the active filter set under the page title.

    A dashboard that silently filters is worse than one that doesn't filter at
    all -- the reader has no way to know which slice they are looking at once
    they have scrolled past the sidebar.
    """
    st.caption("Showing:  " + "  ·  ".join(filters.describe()))


# --- The filter panel ----------------------------------------------------

def _carry_over() -> None:
    """Keep filter selections alive across page navigation.

    Streamlit discards the state of widgets that were not rendered on the last
    run, which in a multipage app means every sidebar selection resets when you
    switch pages. Re-committing the keys on each run is the documented way to
    opt out of that cleanup.
    """
    for key in _ALL_KEYS:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def _reset() -> None:
    for key in _ALL_KEYS:
        st.session_state.pop(key, None)


def sidebar_filters(
    *,
    categories: bool = False,
    sub_categories: bool = False,
    segments: bool = False,
    top_n: int | None = None,
) -> Filters:
    """Render the sidebar filter panel and return the selection.

    Period and region are on every page because every query on every page
    accepts them. The rest are opt-in per page: a slicer is only rendered where
    it reaches the panels below it, so nothing on screen is a no-op.
    """
    _carry_over()
    period_options = cached_periods()

    with st.sidebar:
        st.subheader("Filters")
        period_label = st.selectbox(
            "Period",
            list(period_options),
            key=_KEY_PERIOD,
            help="Built from the periods that actually have orders in them.",
        )
        selected_regions = st.multiselect(
            "Region",
            cached_filter_values("region"),
            key=_KEY_REGIONS,
            placeholder="All regions",
        )

        selected_categories: list[str] = []
        if categories:
            selected_categories = st.multiselect(
                "Category", CATEGORIES, key=_KEY_CATEGORIES, placeholder="All categories"
            )

        selected_subcategories: list[str] = []
        if sub_categories:
            options = cached_sub_categories(tuple(selected_categories))
            # Drop any sub-category the category filter just excluded, so the
            # two selectors cannot contradict each other.
            if _KEY_SUBCATEGORIES in st.session_state:
                st.session_state[_KEY_SUBCATEGORIES] = [
                    value for value in st.session_state[_KEY_SUBCATEGORIES] if value in options
                ]
            selected_subcategories = st.multiselect(
                "Sub-category",
                options,
                key=_KEY_SUBCATEGORIES,
                placeholder="All sub-categories",
            )

        selected_segments: list[str] = []
        if segments:
            selected_segments = st.multiselect(
                "RFM segment", RFM_SEGMENTS, key=_KEY_SEGMENTS, placeholder="All segments"
            )

        n = top_n or 10
        if top_n is not None:
            n = st.slider("Top N", min_value=5, max_value=50, value=top_n, step=5, key=_KEY_TOP_N)

        st.button("Reset filters", on_click=_reset, width="stretch")
        st.divider()
        st.caption(
            "Every panel on this page reads the filters above. "
            "Figures come from the same dbt semantic layer as the Power BI "
            "report and the MCP AI tools."
        )

    return Filters(
        period=period_options[period_label],
        period_label=period_label,
        regions=tuple(selected_regions),
        categories=tuple(selected_categories),
        sub_categories=tuple(selected_subcategories),
        segments=tuple(selected_segments),
        top_n=n,
    )


# --- Formatting ----------------------------------------------------------

def money(value) -> str:
    return "—" if value is None else f"${float(value):,.0f}"


def compact_money(value) -> str:
    """Auto-compacted currency for stat tiles: $4.2M, $12.9K."""
    if value is None:
        return "—"
    value = float(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= limit:
            return f"${value / limit:,.1f}{suffix}"
    return f"${value:,.0f}"


def format_metric(name: str, value) -> str:
    if value is None:
        return "—"
    if name == "gross_profit_margin":
        return f"{float(value):.1f}%"
    if name in {"total_revenue", "total_profit", "average_order_value"}:
        return compact_money(value) if name != "average_order_value" else money(value)
    return f"{int(value):,}"


MONEY_COL = "$%,.0f"
PERCENT_COL = "%.1f%%"
COUNT_COL = "%,d"


def money_column(label: str, **kwargs):
    return st.column_config.NumberColumn(label, format=MONEY_COL, **kwargs)


def percent_column(label: str, **kwargs):
    return st.column_config.NumberColumn(label, format=PERCENT_COL, **kwargs)


def count_column(label: str, **kwargs):
    return st.column_config.NumberColumn(label, format=COUNT_COL, **kwargs)


def share_column(label: str, max_value: float):
    """A share-of-total bar, for the one column where relative size is the point."""
    return st.column_config.ProgressColumn(
        label, format=MONEY_COL, min_value=0, max_value=float(max_value or 1)
    )


def table(df: pd.DataFrame, column_config: dict, height: int | None = None) -> None:
    """A formatted, index-free table.

    Every chart in this app has a table beside or beneath it. That is not
    decoration: two hues in the palette sit below a 3:1 contrast ratio against
    the page, and the rule for those is that the values stay reachable without
    relying on colour.
    """
    # `height` must be omitted rather than passed as None -- Streamlit rejects
    # None outright instead of treating it as "auto".
    extra = {"height": height} if height is not None else {}
    st.dataframe(
        df,
        column_config=column_config,
        hide_index=True,
        width="stretch",
        **extra,
    )


# --- KPI tiles -----------------------------------------------------------

def kpi_row(metric_names: list[str], filters: Filters, per_row: int = 3) -> None:
    """Headline metrics with period-over-period deltas.

    The comparison window is the equally-long period immediately before the
    selection, and it is measured with the *same* metric SQL -- the prior window
    is passed back through ``query_metric`` as a date range rather than being
    recomputed here. Where no comparable prior window exists (all-time, or a
    window that lands in the gap between the historical and synthetic data), the
    tile shows no delta rather than a misleading zero.
    """
    previous = queries.previous_period(filters.period)
    columns = st.columns(per_row)

    for i, name in enumerate(metric_names):
        current = cached_metric(name, filters.period, filters.regions)["value"]
        prior = (
            cached_metric(name, previous, filters.regions)["value"] if previous else None
        )
        delta = _delta(name, current, prior)
        with columns[i % per_row]:
            with st.container(border=True):
                st.metric(
                    METRIC_DEFINITIONS[name]["label"],
                    format_metric(name, current),
                    delta=delta,
                    help=METRIC_DEFINITIONS[name]["description"],
                )

    if previous:
        label = query_metric("total_revenue", previous)["period"]
        st.caption(f"Deltas compare against the preceding window: {label}.")
    elif filters.period != "all_time":
        st.caption(
            "No comparable prior window has data, so deltas are hidden. "
            "The dataset is Superstore history (2014–2017) plus a rolling "
            "synthetic feed, with a gap between them."
        )


def _delta(name: str, current, prior) -> str | None:
    """Percentage change, or percentage points for a metric already in percent."""
    if current is None or prior in (None, 0):
        return None
    current, prior = float(current), float(prior)
    if name == "gross_profit_margin":
        return f"{current - prior:+.1f} pp"
    return f"{(current - prior) / abs(prior) * 100:+.1f}%"


# --- Cached wrappers -----------------------------------------------------
#
# Tuples in, lists out: the tool layer takes lists, but st.cache_data needs
# hashable arguments, so the Filters dataclass carries tuples and the
# conversion happens in one place here.

def _listify(values: tuple[str, ...] | None) -> list[str] | None:
    return list(values) if values else None


@st.cache_data(ttl=600, show_spinner=False)
def cached_periods() -> dict[str, str]:
    return queries.available_periods()


@st.cache_data(ttl=600, show_spinner=False)
def cached_filter_values(column: str) -> list[str]:
    return queries.filter_values(column)


@st.cache_data(ttl=600, show_spinner=False)
def cached_sub_categories(categories: tuple[str, ...]) -> list[str]:
    return queries.sub_categories(_listify(categories))


@st.cache_data(ttl=600, show_spinner=False)
def cached_metric(name: str, period: str, regions: tuple[str, ...] = ()) -> dict:
    return query_metric(name, period, _listify(regions))


@st.cache_data(ttl=600, show_spinner=False)
def metric_explanation(name: str) -> dict:
    return explain_metric(name)


@st.cache_data(ttl=600, show_spinner=False)
def top_customers(n: int, period: str, regions: tuple[str, ...], segments: tuple[str, ...]):
    return get_top_customers(n, period, _listify(regions), _listify(segments))


@st.cache_data(ttl=600, show_spinner=False)
def rfm_segments(period: str, regions: tuple[str, ...]):
    return get_rfm_segments(period, _listify(regions))


@st.cache_data(ttl=600, show_spinner=False)
def region_revenue(period: str, regions: tuple[str, ...]):
    return revenue_by_region(period, _listify(regions))


@st.cache_data(ttl=600, show_spinner=False)
def product_performance(
    category: str | None,
    n: int,
    period: str,
    regions: tuple[str, ...],
    sub_categories: tuple[str, ...],
):
    return get_product_performance(
        category, n, period, _listify(regions), _listify(sub_categories)
    )


@st.cache_data(ttl=600, show_spinner=False)
def category_breakdown(period: str, regions: tuple[str, ...], categories: tuple[str, ...]):
    return get_category_breakdown(period, _listify(regions), _listify(categories))


@st.cache_data(ttl=600, show_spinner=False)
def discount_impact(period: str, regions: tuple[str, ...], categories: tuple[str, ...]):
    return get_discount_impact(period, _listify(regions), _listify(categories))


@st.cache_data(ttl=600, show_spinner=False)
def timeseries(
    grain: str,
    period: str,
    regions: tuple[str, ...],
    era: str | None,
    rolling_window: int = 7,
):
    return queries.revenue_timeseries(grain, period, _listify(regions), era, rolling_window)


@st.cache_data(ttl=600, show_spinner=False)
def state_revenue(period: str, regions: tuple[str, ...]):
    return queries.revenue_by_state(period, _listify(regions))


@st.cache_data(ttl=600, show_spinner=False)
def rfm_matrix(period: str, regions: tuple[str, ...]):
    return queries.rfm_matrix(period, _listify(regions))


@st.cache_data(ttl=600, show_spinner=False)
def pareto(period: str, regions: tuple[str, ...], categories: tuple[str, ...], limit: int):
    return queries.product_pareto(period, _listify(regions), _listify(categories), limit)


@st.cache_data(ttl=600, show_spinner=False)
def discount_bins(period: str, regions: tuple[str, ...], categories: tuple[str, ...]):
    return queries.discount_margin_bins(period, _listify(regions), _listify(categories))


__all__ = [
    "CATEGORIES",
    "ERA_HISTORICAL",
    "ERA_RECENT",
    "RFM_SEGMENTS",
    "METRIC_DEFINITIONS",
    "Filters",
    "page_setup",
    "filter_caption",
    "sidebar_filters",
    "kpi_row",
    "table",
    "to_frame",
    "money",
    "compact_money",
    "format_metric",
    "money_column",
    "percent_column",
    "count_column",
    "share_column",
    "cached_metric",
    "metric_explanation",
    "top_customers",
    "rfm_segments",
    "region_revenue",
    "product_performance",
    "category_breakdown",
    "discount_impact",
    "timeseries",
    "state_revenue",
    "rfm_matrix",
    "pareto",
    "discount_bins",
]
