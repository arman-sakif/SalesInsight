"""Unit tests for the synthetic-data retention policy.

These run against a throwaway in-memory table rather than the warehouse, so
they assert the rule itself: a year of generated history is kept, and the
Kaggle baseline is never eligible for deletion no matter how old it is.
"""
from datetime import date, timedelta

import duckdb
import pytest

from ingestion.synthetic_generator import RETAIN_DAYS, prune_synthetic

TODAY = date.today()


def _syn_row(days_ago: int) -> tuple[str, str]:
    """A synthetic row as the generator writes it: SYN- prefix, ISO date."""
    day = TODAY - timedelta(days=days_ago)
    return (f"SYN-{day:%Y%m%d}-0001", day.isoformat())


@pytest.fixture
def conn():
    """An in-memory stand-in for raw.raw_orders with the two columns pruned on."""
    conn = duckdb.connect()
    conn.execute("CREATE SCHEMA raw")
    conn.execute("CREATE TABLE raw.raw_orders (row_id VARCHAR, order_date VARCHAR)")
    yield conn
    conn.close()


def _insert(conn, rows):
    conn.executemany("INSERT INTO raw.raw_orders VALUES (?, ?)", rows)


def _remaining(conn) -> set[str]:
    return {row[0] for row in conn.execute("SELECT row_id FROM raw.raw_orders").fetchall()}


def test_retention_window_is_one_year():
    assert RETAIN_DAYS == 365


def test_prunes_synthetic_rows_past_the_window(conn):
    _insert(conn, [_syn_row(400), _syn_row(500), _syn_row(10)])

    assert prune_synthetic(conn) == 2
    assert _remaining(conn) == {_syn_row(10)[0]}


def test_never_prunes_the_kaggle_baseline(conn):
    """Kaggle rows are years past any cutoff and stored as M/D/YYYY."""
    _insert(conn, [("1", "11/8/2016"), ("2", "6/12/2014"), _syn_row(400)])

    assert prune_synthetic(conn) == 1
    assert _remaining(conn) == {"1", "2"}


def test_keeps_rows_exactly_on_the_cutoff(conn):
    _insert(conn, [_syn_row(RETAIN_DAYS), _syn_row(RETAIN_DAYS + 1)])

    assert prune_synthetic(conn) == 1
    assert _remaining(conn) == {_syn_row(RETAIN_DAYS)[0]}


def test_is_a_noop_when_all_history_is_recent(conn):
    rows = [_syn_row(0), _syn_row(7)]
    _insert(conn, rows)

    assert prune_synthetic(conn) == 0
    assert _remaining(conn) == {row[0] for row in rows}


def test_retain_days_is_configurable(conn):
    _insert(conn, [_syn_row(45), _syn_row(15)])

    assert prune_synthetic(conn, retain_days=30) == 1
    assert _remaining(conn) == {_syn_row(15)[0]}
