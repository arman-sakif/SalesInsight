"""Read-only DuckDB connection helper for the MCP server."""
import duckdb
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "warehouse.db"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the warehouse.

    read_only=True lets the MCP server query safely even while other
    processes (dbt, ingestion) hold the file, and prevents any accidental
    writes from tool calls.
    """
    return duckdb.connect(str(DB_PATH), read_only=True)


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