"""Read-only DuckDB connection helper.

Two modes, chosen automatically:

* **Local / full pipeline** — when ``data/warehouse.db`` exists, open it
  read-only. This is what the MCP server and local Streamlit use, and it
  stays consistent with dbt and ingestion (which hold the single writer lock).
* **Deployment fallback** — when the DuckDB file is absent (e.g. Streamlit
  Community Cloud, which only has the committed repo), build an in-memory
  connection and register the Parquet marts in ``data/parquet`` as views in
  the ``main`` schema. Every query in ``tools/`` references ``main.<table>``,
  so it works unchanged against either source.
"""
import duckdb
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "warehouse.db"
PARQUET_DIR = ROOT_DIR / "data" / "parquet"

# Marts exported by ingestion/export_parquet.py, registered as views in the
# Parquet fallback so `main.<name>` resolves.
_PARQUET_TABLES = [
    "fact_sales",
    "dim_customer",
    "dim_product",
    "dim_date",
    "dim_region",
]


def _connect_parquet() -> duckdb.DuckDBPyConnection:
    """In-memory connection with the Parquet marts registered as views."""
    conn = duckdb.connect()  # in-memory, default schema is `main`
    for table in _PARQUET_TABLES:
        path = (PARQUET_DIR / f"{table}.parquet").as_posix()
        conn.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{path}')")
    return conn


def get_connection() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the warehouse, or a Parquet-backed one.

    read_only=True (when using the DuckDB file) lets this query safely even
    while other processes hold the file, and prevents accidental writes from
    tool calls.
    """
    if DB_PATH.exists():
        return duckdb.connect(str(DB_PATH), read_only=True)
    return _connect_parquet()


def run_query(sql: str, params: list | None = None) -> list[dict]:
    """Run a SELECT and return rows as a list of dicts."""
    conn = get_connection()
    try:
        if params:
            result = conn.execute(sql, params)
        else:
            result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()
