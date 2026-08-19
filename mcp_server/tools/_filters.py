"""Shared SQL filter helpers for the tool layer.

Every tool that accepts a ``period`` or ``regions`` argument builds its WHERE
clause here. Before this module the period logic was copy-pasted into three
modules with three slightly different signatures, and four of the eight tools
had no period support at all -- which made the dashboard's Period slicer a
silent no-op on the panels those tools fed. One implementation keeps the
dashboard, the AI tools, and Power BI agreeing on what "this year" means.

Predicates are returned without the ``WHERE`` keyword so callers can combine
them with ``where_clause()``. Literal values are never interpolated: filters
that carry user- or model-supplied values emit ``?`` placeholders and hand the
values back for DuckDB to bind.
"""
from datetime import date

# Fixed-vocabulary periods, in the order the UI offers them. Anything else that
# looks like a 4-digit year is treated as that year; everything else falls back
# to all-time rather than erroring, so a bad argument from a model degrades to
# a wider answer instead of a failure.
PERIOD_LABELS = {
    "all_time": "All time",
    "this_year": "This year",
    "last_year": "Last year",
    "last_30_days": "Last 30 days",
    "last_90_days": "Last 90 days",
}


def period_predicate(period: str = "all_time", alias: str = "") -> tuple[str, str]:
    """Return a SQL predicate restricting fact rows to ``period``, and its label.

    Args:
        period: 'all_time', 'this_year', 'last_year', 'last_30_days',
            'last_90_days', or a 4-digit year like '2016'.
        alias: Table alias qualifying the fact columns (e.g. 'f' in a join).
            Empty for single-table queries.

    Returns:
        ``(predicate, label)`` where an empty predicate means no filtering.
    """
    prefix = f"{alias}." if alias else ""
    period = (period or "all_time").strip()

    if period == "this_year":
        return f"{prefix}order_year = YEAR(CURRENT_DATE)", PERIOD_LABELS["this_year"]
    if period == "last_year":
        return f"{prefix}order_year = YEAR(CURRENT_DATE) - 1", PERIOD_LABELS["last_year"]
    # Rolling windows read order_date directly rather than order_year: they are
    # what the synthetic rolling window exists to exercise, and they routinely
    # straddle a year boundary.
    if period == "last_30_days":
        return f"{prefix}order_date >= CURRENT_DATE - INTERVAL 30 DAY", PERIOD_LABELS["last_30_days"]
    if period == "last_90_days":
        return f"{prefix}order_date >= CURRENT_DATE - INTERVAL 90 DAY", PERIOD_LABELS["last_90_days"]
    if period.isdigit() and len(period) == 4:
        return f"{prefix}order_year = {int(period)}", f"Year {period}"
    if period.startswith(RANGE_PREFIX):
        bounds = parse_range(period)
        if bounds:
            lo, hi = bounds
            return (
                f"{prefix}order_date BETWEEN DATE '{lo}' AND DATE '{hi}'",
                f"{lo:%-d %b %Y} to {hi:%-d %b %Y}" if _SUPPORTS_DASH_FORMAT
                else f"{lo.isoformat()} to {hi.isoformat()}",
            )
    return "", PERIOD_LABELS["all_time"]


# An explicit window, used for the period-over-period KPI deltas: the prior
# window has no name in the preset vocabulary, and routing it through the same
# `period` argument means the delta is computed by the same metric SQL as the
# headline figure rather than by a second definition of "revenue".
RANGE_PREFIX = "range:"

# strftime("%-d") is POSIX-only; Windows spells it "%#d". Rather than branch on
# the platform, fall back to ISO dates where the padding-strip is unsupported.
try:
    date(2026, 1, 5).strftime("%-d %b %Y")
    _SUPPORTS_DASH_FORMAT = True
except ValueError:  # pragma: no cover - platform dependent
    _SUPPORTS_DASH_FORMAT = False


def range_period(lo: date, hi: date) -> str:
    """Build the period argument for an explicit inclusive date window."""
    return f"{RANGE_PREFIX}{lo.isoformat()}:{hi.isoformat()}"


def parse_range(period: str) -> tuple[date, date] | None:
    """Parse a ``range:<iso>:<iso>`` period, or None if it isn't one.

    The dates are round-tripped through ``date.fromisoformat`` and re-serialised
    before they reach SQL, so only a real ISO date can ever be interpolated --
    this is the one predicate that embeds a literal rather than binding it.
    """
    if not period.startswith(RANGE_PREFIX):
        return None
    try:
        lo_raw, hi_raw = period[len(RANGE_PREFIX):].split(":")
        lo, hi = date.fromisoformat(lo_raw), date.fromisoformat(hi_raw)
    except ValueError:
        return None
    return (lo, hi) if lo <= hi else (hi, lo)


def period_label(period: str = "all_time") -> str:
    """The human-readable label for a period, without building a predicate."""
    return period_predicate(period)[1]


def in_predicate(column: str, values, params: list) -> str:
    """Return ``column IN (?, ?, ...)`` and append the values to ``params``.

    Returns an empty predicate for ``None`` or an empty selection, so "nothing
    ticked" means "no filter" rather than "no rows" -- which is how a
    multi-select slicer reads to a stakeholder.
    """
    if not values:
        return ""
    if isinstance(values, str):
        values = [values]
    values = list(values)
    params.extend(values)
    placeholders = ", ".join("?" for _ in values)
    return f"{column} IN ({placeholders})"


def where_clause(*predicates: str) -> str:
    """Join non-empty predicates into a WHERE clause (empty string if none)."""
    kept = [p for p in predicates if p]
    return "WHERE " + " AND ".join(kept) if kept else ""
