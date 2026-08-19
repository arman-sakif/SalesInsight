"""End-to-end tests for the Streamlit pages, via Streamlit's own test harness.

``AppTest`` executes a page script the way the server does and exposes the
elements it produced, so these catch two classes of bug that unit tests over the
query layer cannot:

* a page that raises at import or render time (a bad keyword argument, a column
  renamed in one place and not another) -- the app would be a stack trace in the
  browser while every underlying query still passed its own tests;
* a slicer that renders but doesn't reach the panels beneath it. That was the
  actual defect this redesign set out to fix, so it is asserted here at the UI
  level rather than trusted.

These are slower than the query tests -- each run executes a whole page against
DuckDB -- but there are only a handful of them.
"""
import json
from pathlib import Path

import conftest
import pytest
from streamlit.testing.v1 import AppTest

from app import charts

# AppTest resolves a relative path against the file that calls it, so page
# paths are absolute -- otherwise they would be looked up under tests/.
_APP = Path(__file__).resolve().parent.parent / "app"

PAGES = [
    "streamlit_app.py",
    "pages/1_Customer_Intelligence.py",
    "pages/2_Regional_Performance.py",
    "pages/3_Product_Intelligence.py",
    "pages/4_Trends.py",
]

TIMEOUT = 180


def _run(page: str, **state) -> AppTest:
    at = AppTest.from_file(str(_APP / page), default_timeout=TIMEOUT)
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, f"{page} raised: {[str(e.value) for e in at.exception]}"
    return at


def _charts(at: AppTest) -> list:
    return [
        element
        for element in at.main
        if hasattr(element, "proto")
        and element.proto.__class__.__name__ == "VegaLiteChart"
    ]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_error(page):
    at = _run(page)
    assert at.title, f"{page} rendered no title"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_has_charts_and_a_table_view(page):
    """Two hues in the palette sit below 3:1 contrast against the page, so the
    rule for them is that values stay reachable without relying on colour."""
    at = _run(page)
    assert _charts(at), f"{page} rendered no charts"
    assert at.dataframe, f"{page} rendered no table view"


@pytest.mark.parametrize("page", PAGES)
def test_no_page_uses_the_old_default_bar_chart(page):
    """Every chart is an explicit spec from app/charts.py, on a validated
    palette -- not a bare st.bar_chart.

    Either palette counts: the app now draws in the viewer's theme, and which
    one a test run lands in depends on what ``st.context.theme`` reports. What
    is asserted is that the spec carries *a* palette of ours, not Vega's
    defaults.
    """
    at = _run(page)
    blues = {charts.LIGHT.blue, charts.DARK.blue}
    ramps = {charts.LIGHT.sequential[0], charts.DARK.sequential[0]}
    for chart in _charts(at):
        spec = chart.proto.spec
        assert any(hex_[1:] in spec for hex_ in blues | ramps)


@pytest.mark.parametrize("page", PAGES)
def test_period_filter_reaches_the_page(page):
    """A period that selects different rows must produce a different render.

    Comparing whole chart specs catches the case this redesign existed to fix:
    the slicer moved, the caption changed, and the numbers underneath did not.
    """
    all_time = _run(page, flt_period="All time")
    year = _run(page, flt_period="2016")

    specs_all = [c.proto.spec for c in _charts(all_time)]
    specs_year = [c.proto.spec for c in _charts(year)]
    assert specs_all != specs_year, f"{page}: changing the period changed nothing"


@pytest.mark.parametrize("page", PAGES)
def test_region_filter_reaches_the_page(page):
    unfiltered = _run(page)
    west = _run(page, flt_regions=["West"])
    assert [c.proto.spec for c in _charts(unfiltered)] != [
        c.proto.spec for c in _charts(west)
    ], f"{page}: the region filter changed nothing"


def test_period_filter_moves_the_headline_kpis():
    """The specific regression: KPI tiles that ignore the slicer above them."""
    all_time = _run("streamlit_app.py", flt_period="All time")
    year = _run("streamlit_app.py", flt_period="2016")
    assert [m.value for m in all_time.metric] != [m.value for m in year.metric]


def test_kpis_show_a_delta_when_a_prior_window_exists():
    at = _run("streamlit_app.py", flt_period="2016")
    assert any(m.delta for m in at.metric), "no KPI showed a period-over-period delta"


def test_kpis_hide_deltas_rather_than_faking_them_for_all_time():
    """All-time has no predecessor, so a delta would have to be invented."""
    at = _run("streamlit_app.py", flt_period="All time")
    assert not any(m.delta for m in at.metric)


def test_product_page_period_filter_reaches_the_discount_panel():
    """get_discount_impact was one of the four all-time-only tools, and the
    discount panel is the one that silently ignored the slicer entirely."""
    page = "pages/3_Product_Intelligence.py"
    all_time = _run(page, flt_period="All time")
    year = _run(page, flt_period="2016")

    def discount_table(at):
        return [df.value.to_dict() for df in at.dataframe][-1]

    assert discount_table(all_time) != discount_table(year)


def test_filters_are_reported_on_the_page():
    """The active slice has to be visible once you scroll past the sidebar."""
    at = _run("streamlit_app.py", flt_period="2016", flt_regions=["West"])
    captions = " ".join(c.value for c in at.caption)
    assert "2016" in captions and "West" in captions


@pytest.mark.parametrize("page", PAGES)
def test_charts_carry_a_reachable_tooltip(page):
    """A value must be readable at the mark, not only in the table.

    "Somewhere in the spec there is the word tooltip" is not the assertion:
    that passed for a line chart whose only tooltip sat on a 2px stroke, which
    is exactly the defect this test was meant to catch. So each chart on the
    page has to put its tooltip on a mark with area, or bind a nearest-point
    selection that finds the value for the reader.
    """
    at = _run(page)
    for chart in _charts(at):
        spec = json.loads(chart.proto.spec)
        if conftest.is_placeholder(spec):
            continue  # an empty panel has no value to read
        assert conftest.hover_is_reachable(spec), (
            f"{page}: a chart's only tooltip is on "
            f"{sorted(conftest.tooltip_marks(spec))} with no nearest-point hover"
        )


def test_empty_selection_explains_itself_instead_of_erroring():
    """The Trends page's recent panel has nothing to draw for a 2016 selection."""
    at = _run("pages/4_Trends.py", flt_period="2016")
    assert at.info, "an empty panel rendered nothing useful"
    assert any("Last 30 days" in i.value or "recent" in i.value.lower() for i in at.info)
