"""Unit tests for the Altair builders in ``app/charts.py``.

The page tests in ``test_app_pages.py`` run whole Streamlit scripts against
DuckDB, which is the right level for "does the slicer reach this panel" but a
slow and indirect place to ask "is this chart readable". These take the builders
directly with small frames, so every chart can be checked in both themes without
a warehouse anywhere near it.
"""
import json

import pandas as pd
import pytest

from app import charts

MODES = ["light", "dark"]

_TIMESERIES = pd.DataFrame(
    {
        "period_start": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        "revenue": [10.0, 20.0, 15.0],
        "profit": [1.0, 2.0, 1.5],
        "orders": [3, 4, 5],
        "revenue_rolling": [10.0, 15.0, 15.0],
    }
)
_STATES = pd.DataFrame(
    {
        "state": ["Texas", "Ohio"],
        "region": ["Central", "East"],
        "revenue": [10.0, 4.0],
        "profit": [1.0, 0.4],
        "orders": [2, 1],
        "margin_pct": [10.0, 10.0],
    }
)
_REGIONS = pd.DataFrame(
    {
        "region": ["West", "East"],
        "total_revenue": [100.0, 80.0],
        "total_profit": [10.0, 8.0],
        "profit_margin_pct": [10.0, 10.0],
        "total_orders": [5, 4],
    }
)
_RFM = pd.DataFrame(
    {
        "r_score": [1, 4],
        "f_score": [1, 4],
        "customers": [2, 3],
        "revenue": [10.0, 90.0],
        "example_segment": ["Lost", "Champions"],
    }
)
_PARETO = pd.DataFrame(
    {
        "rank": [1, 2, 3],
        "product_name": ["a", "b", "c"],
        "category": ["Technology", "Furniture", "Technology"],
        "revenue": [9.0, 5.0, 1.0],
        "cumulative_pct": [60.0, 93.3, 100.0],
    }
)
_DISCOUNT = pd.DataFrame(
    {
        "discount_pct": [0.0, 5.0, 10.0],
        "margin_pct": [20.0, 5.0, -10.0],
        "revenue": [100.0, 50.0, 25.0],
        "profit": [20.0, 2.5, -2.5],
        "order_lines": [10, 5, 2],
    }
)
_MIX = pd.DataFrame(
    {
        "category": ["Technology", "Furniture"],
        "sub_category": ["Phones", "Chairs"],
        "total_revenue": [50.0, 20.0],
        "margin_pct": [12.0, 8.0],
        "avg_discount_pct": [5.0, 10.0],
    }
)
_PRODUCTS = pd.DataFrame(
    {
        "product_name": ["a", "b"],
        "category": ["Technology", "Furniture"],
        "sub_category": ["Phones", "Chairs"],
        "total_revenue": [50.0, 20.0],
        "total_profit": [5.0, 2.0],
        "avg_discount_pct": [5.0, 10.0],
    }
)
_SEGMENTS = pd.DataFrame(
    {
        "rfm_segment": ["Champions", "Lost"],
        "customer_count": [3, 7],
        "total_revenue": [90.0, 10.0],
        "avg_customer_value": [30.0, 1.4],
    }
)

# Every builder in the module, with a frame shaped the way its query returns.
BUILDERS = {
    "revenue_trend": lambda mode: charts.revenue_trend(_TIMESERIES, "day", mode=mode),
    "revenue_trend_no_rolling": lambda mode: charts.revenue_trend(
        _TIMESERIES.drop(columns=["revenue_rolling"]), "month", mode=mode
    ),
    "revenue_vs_profit": lambda mode: charts.revenue_vs_profit(_TIMESERIES, mode=mode),
    "state_choropleth": lambda mode: charts.state_choropleth(_STATES, mode=mode),
    "region_bars": lambda mode: charts.region_bars(_REGIONS, mode=mode),
    "rfm_heatmap": lambda mode: charts.rfm_heatmap(_RFM, mode=mode),
    "pareto_curve": lambda mode: charts.pareto_curve(_PARETO, mode=mode),
    "discount_margin": lambda mode: charts.discount_margin(_DISCOUNT, mode=mode),
    "category_heatmap": lambda mode: charts.category_heatmap(_MIX, mode=mode),
    "top_products_bars": lambda mode: charts.top_products_bars(_PRODUCTS, mode=mode),
    "segment_revenue_bars": lambda mode: charts.segment_revenue_bars(_SEGMENTS, mode=mode),
}


def _spec(chart) -> dict:
    return json.loads(json.dumps(chart.to_dict()))


def _text(chart) -> str:
    return json.dumps(chart.to_dict())


# --- Palette -------------------------------------------------------------

def test_an_unrecognised_theme_falls_back_to_light():
    """``st.context.theme`` reports nothing usable on a first paint, and a
    chart that raises there would take the page with it."""
    for mode in (None, "", "solarized", "DARK"):
        assert charts.palette(mode) is charts.LIGHT
    assert charts.palette("dark") is charts.DARK


def test_the_sequential_ramp_runs_the_other_way_in_dark_mode():
    """More revenue has to read as further from the page. On a light surface
    that is darker; on a dark one it is lighter."""
    assert charts.DARK.sequential == tuple(reversed(charts.LIGHT.sequential))
    assert charts.LIGHT.sequential[0] == charts.DARK.sequential[-1]


@pytest.mark.parametrize("name", list(BUILDERS))
@pytest.mark.parametrize("mode", MODES)
def test_every_chart_renders_in_both_themes(name, mode):
    spec = _spec(BUILDERS[name](mode))
    assert spec["config"]["view"]["fill"] == charts.palette(mode).surface


def _tokens(p: charts.Palette) -> set[str]:
    return set(p.categorical) | set(p.sequential) | {
        p.surface,
        p.ink,
        p.ink_secondary,
        p.ink_muted,
        p.grid,
        p.axis,
    }


# Only the hexes one palette has and the other does not. The two share more
# than they look like they do -- the light axis colour is the dark theme's
# secondary ink, the sequential ramp is the same ten steps in reverse, and slot
# 6 green is identical in both -- so a naive token-by-token comparison would
# fail on values that are supposed to appear in both specs.
LIGHT_ONLY = _tokens(charts.LIGHT) - _tokens(charts.DARK)
DARK_ONLY = _tokens(charts.DARK) - _tokens(charts.LIGHT)


@pytest.mark.parametrize("name", list(BUILDERS))
def test_no_chart_leaks_the_other_theme_s_hues(name):
    """The failure this guards against is a hardcoded hex left behind in one
    mark: it survives the theme switch and glows on the wrong background."""
    light, dark = _text(BUILDERS[name]("light")), _text(BUILDERS[name]("dark"))
    leaked_into_dark = sorted(hex_ for hex_ in LIGHT_ONLY if hex_ in dark)
    leaked_into_light = sorted(hex_ for hex_ in DARK_ONLY if hex_ in light)
    assert not leaked_into_dark, f"{name}: light-only hues in the dark spec: {leaked_into_dark}"
    assert not leaked_into_light, f"{name}: dark-only hues in the light spec: {leaked_into_light}"


@pytest.mark.parametrize("mode", MODES)
def test_an_empty_frame_explains_itself_in_either_theme(mode):
    spec = _spec(charts.revenue_trend(_TIMESERIES.iloc[0:0], mode=mode))
    assert spec["config"]["view"]["fill"] == charts.palette(mode).surface
    assert spec["mark"]["color"] == charts.palette(mode).ink_muted
