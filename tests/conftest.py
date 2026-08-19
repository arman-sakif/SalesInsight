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
