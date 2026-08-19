"""Unit tests for the shared SQL filter helpers.

These are pure string builders, so they are tested without touching DuckDB.
The behaviour that matters is the vocabulary (what counts as a valid period)
and the two safety rules: values are always bound as parameters, and an empty
selection means "no filter" rather than "no rows".
"""
import pytest

from mcp_server.tools._filters import (
    in_predicate,
    period_label,
    period_predicate,
    where_clause,
)


@pytest.mark.parametrize(
    "period,label",
    [
        ("all_time", "All time"),
        ("this_year", "This year"),
        ("last_year", "Last year"),
        ("last_30_days", "Last 30 days"),
        ("last_90_days", "Last 90 days"),
        ("2016", "Year 2016"),
    ],
)
def test_period_labels_are_stable(period, label):
    assert period_predicate(period)[1] == label
    assert period_label(period) == label


def test_all_time_produces_no_predicate():
    predicate, _ = period_predicate("all_time")
    assert predicate == ""
    assert where_clause(predicate) == ""


@pytest.mark.parametrize("period", ["", "  ", None, "nonsense", "20166", "16"])
def test_unrecognised_periods_fall_back_to_all_time(period):
    """A bad argument from a model should widen the answer, not error."""
    predicate, label = period_predicate(period)
    assert predicate == ""
    assert label == "All time"


def test_year_periods_are_parsed_as_integers():
    """The year reaches SQL as an int literal, so a crafted string cannot ride
    along into the query."""
    assert period_predicate("2016")[0] == "order_year = 2016"


def test_alias_qualifies_the_fact_columns():
    assert period_predicate("2016", alias="f")[0] == "f.order_year = 2016"
    assert "f.order_date" in period_predicate("last_30_days", alias="f")[0]


def test_rolling_windows_filter_on_the_date_not_the_year():
    """last_30_days routinely straddles a year boundary, so order_year is the
    wrong column for it."""
    for period in ("last_30_days", "last_90_days"):
        predicate = period_predicate(period)[0]
        assert "order_date" in predicate
        assert "order_year" not in predicate


def test_in_predicate_binds_values_as_parameters():
    params: list = []
    predicate = in_predicate("region", ["West", "East"], params)
    assert predicate == "region IN (?, ?)"
    assert params == ["West", "East"]


def test_in_predicate_accepts_a_bare_string():
    params: list = []
    assert in_predicate("p.category", "Technology", params) == "p.category IN (?)"
    assert params == ["Technology"]


@pytest.mark.parametrize("empty", [None, [], ()])
def test_empty_selection_means_no_filter(empty):
    """Nothing ticked in a multi-select reads as "all", not "none"."""
    params: list = []
    assert in_predicate("region", empty, params) == ""
    assert params == []


def test_where_clause_joins_only_non_empty_predicates():
    assert where_clause("a = 1", "", "b = 2") == "WHERE a = 1 AND b = 2"
    assert where_clause("", "") == ""
    assert where_clause() == ""
