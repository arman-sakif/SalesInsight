import duckdb
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "warehouse.db"
EXPORT_DIR = ROOT_DIR / "data" / "parquet"

TABLES = [
    "fact_sales",
    "dim_customer",
    "dim_product",
    "dim_date",
    "dim_region",
]

def export():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))

    for table in TABLES:
        out_path = EXPORT_DIR / f"{table}.parquet"
        conn.execute(f"""
            COPY (SELECT * FROM main.{table})
            TO '{out_path.as_posix()}'
            (FORMAT PARQUET)
        """)
        count = conn.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()[0]
        print(f"Exported {table} -> {out_path.name} ({count:,} rows)")

    conn.close()
    print("Done.")

if __name__ == "__main__":
    export()