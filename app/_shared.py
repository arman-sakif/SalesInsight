"""Shared helpers for the Streamlit app.

Every data access here reuses the same query functions the MCP server
registers (in ``mcp_server/tools``), so the web dashboard, the AI tools,
and Power BI all read from the one dbt-built semantic layer in DuckDB.
The thin ``st.cache_data`` wrappers below just avoid re-opening the
read-only DuckDB connection on every widget interaction.
"""
from decimal import Decimal

import pandas as pd
import streamlit as st

from mcp_server.tools.customers import get_rfm_segments, get_top_customers
from mcp_server.tools.metrics import METRIC_DEFINITIONS, explain_metric, query_metric
from mcp_server.tools.products import (
    get_category_breakdown,
    get_discount_impact,
    get_product_performance,
)
from mcp_server.tools.regions import revenue_by_region

# Period options shared across pages. Maps the label shown in the UI to the
# ``period`` argument the tool functions expect.
PERIOD_OPTIONS = {
    "All time": "all_time",
    "This year": "this_year",
    "Last year": "last_year",
    "2017": "2017",
    "2016": "2016",
    "2015": "2015",
    "2014": "2014",
}

CATEGORIES = ["Furniture", "Office Supplies", "Technology"]


def page_setup(title: str, icon: str = "📊") -> None:
    """Apply consistent page config and header."""
    st.set_page_config(page_title=f"SalesInsight — {title}", page_icon=icon, layout="wide")
    st.title(f"{icon} {title}")


def period_selector(key: str = "period") -> str:
    """Render a period dropdown in the sidebar and return the tool-arg value."""
    label = st.sidebar.selectbox("Period", list(PERIOD_OPTIONS.keys()), key=key)
    return PERIOD_OPTIONS[label]


def _to_float(value):
    """DuckDB returns Decimals; convert for display and charting."""
    return float(value) if isinstance(value, Decimal) else value


def to_frame(rows: list[dict]) -> pd.DataFrame:
    """Turn a list-of-dicts tool result into a display-ready DataFrame."""
    df = pd.DataFrame(rows)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].map(_to_float)
    return df


def money(value) -> str:
    value = _to_float(value)
    return "—" if value is None else f"${value:,.0f}"


# --- Cached wrappers around the MCP tool functions ------------------------

@st.cache_data(ttl=600, show_spinner=False)
def metric(name: str, period: str) -> dict:
    return query_metric(name, period)


@st.cache_data(ttl=600, show_spinner=False)
def metric_explanation(name: str) -> dict:
    return explain_metric(name)


@st.cache_data(ttl=600, show_spinner=False)
def top_customers(n: int, period: str) -> list[dict]:
    return get_top_customers(n, period)


@st.cache_data(ttl=600, show_spinner=False)
def rfm_segments() -> list[dict]:
    return get_rfm_segments()


@st.cache_data(ttl=600, show_spinner=False)
def region_revenue(period: str) -> list[dict]:
    return revenue_by_region(period)


@st.cache_data(ttl=600, show_spinner=False)
def product_performance(category: str | None, n: int) -> list[dict]:
    return get_product_performance(category, n)


@st.cache_data(ttl=600, show_spinner=False)
def category_breakdown() -> list[dict]:
    return get_category_breakdown()


@st.cache_data(ttl=600, show_spinner=False)
def discount_impact() -> list[dict]:
    return get_discount_impact()


__all__ = [
    "PERIOD_OPTIONS",
    "CATEGORIES",
    "METRIC_DEFINITIONS",
    "page_setup",
    "period_selector",
    "to_frame",
    "money",
    "metric",
    "metric_explanation",
    "top_customers",
    "rfm_segments",
    "region_revenue",
    "product_performance",
    "category_breakdown",
    "discount_impact",
]
