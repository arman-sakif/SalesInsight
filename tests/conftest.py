"""Put the repo root on sys.path for the test session.

``mcp_server`` and ``ingestion`` are packaged into the wheel and resolve on
their own, but the Streamlit app in ``app/`` is not a distributable package --
it is a set of scripts Streamlit runs directly. Tests still need to import
``app.queries``, so the root goes on the path here rather than adding a
package layout the app itself has no use for.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# --- Reading Vega-Lite specs ---------------------------------------------
#
# Shared by test_charts.py (builders, directly) and test_app_pages.py (the
# specs a rendered page actually emitted), so they live here rather than in
# whichever module needed them first.

# Marks a pointer can plausibly land on. A `line` is 2px of stroke and a bare
# `rule` is 1px: a tooltip hung on either is not reachable unless a
# nearest-point selection is doing the work of finding it.
POINTER_TARGETS = {"bar", "rect", "geoshape", "arc", "point", "circle", "square", "area"}


def layers(spec: dict) -> list[dict]:
    """Flatten a Vega-Lite spec into its leaf (single-mark) specs."""
    if "layer" in spec:
        return [leaf for child in spec["layer"] for leaf in layers(child)]
    return [spec]


def mark_type(layer: dict) -> str:
    mark = layer.get("mark")
    return mark.get("type", "") if isinstance(mark, dict) else (mark or "")


def tooltip_marks(spec: dict) -> set[str]:
    """The mark types that actually carry a tooltip encoding."""
    return {
        mark_type(layer)
        for layer in layers(spec)
        if "tooltip" in layer.get("encoding", {})
    }


def has_nearest_hover(spec: dict) -> bool:
    """True if some layer binds a nearest-point selection to the pointer."""
    for layer in layers(spec) + [spec]:
        for param in layer.get("params", []):
            select = param.get("select")
            if isinstance(select, dict) and select.get("nearest"):
                return True
    return False


def is_placeholder(spec: dict) -> bool:
    """The "no data in this selection" panel: one text mark, nothing to hover."""
    leaves = layers(spec)
    return len(leaves) == 1 and mark_type(leaves[0]) == "text" and not tooltip_marks(spec)


def hover_is_reachable(spec: dict) -> bool:
    """Can a reader get a tooltip without hitting a hairline?

    Either a tooltip sits on a mark with real area, or a nearest-point
    selection finds the value for them.
    """
    carrying = tooltip_marks(spec)
    if not carrying:
        return False
    return bool(carrying & POINTER_TARGETS) or has_nearest_hover(spec)
