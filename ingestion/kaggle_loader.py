import os
import shutil
import duckdb
import kagglehub
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
DB_PATH = ROOT_DIR / "data" / "warehouse.db"
DATASET = "konstantinognev/sample-superstorecsv"

def download_dataset() -> Path:
    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print("Downloading dataset from Kaggle...")
    path = kagglehub.dataset_download(DATASET)
    print(f"kagglehub path: {path}")
    csv_files = list(Path(path).glob("*.csv"))
    print(f"CSV files found: {csv_files}")
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {path}")
    dest = RAW_DIR / "superstore.csv"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(csv_files[0], dest)
    print(f"Saved to {dest}")
    return dest

def load_to_duckdb(csv_path: Path) -> None:
    print(f"Reading CSV from {csv_path}")
    df = pd.read_csv(csv_path, encoding="latin-1")
    print(f"Rows loaded: {len(df):,}")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    print(f"Columns: {list(df.columns)}")
    print(f"Connecting to DuckDB at {DB_PATH}")
    conn = duckdb.connect(str(DB_PATH))
    print("Connected. Creating schema...")
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    print("Schema created. Writing table...")
    conn.execute("DROP TABLE IF EXISTS raw.raw_orders")
    conn.execute("CREATE TABLE raw.raw_orders AS SELECT * FROM df")
    count = conn.execute("SELECT COUNT(*) FROM raw.raw_orders").fetchone()[0]
    print(f"raw.raw_orders created with {count:,} rows")
    conn.close()
    print("Connection closed.")

if __name__ == "__main__":
    csv_path = download_dataset()
    load_to_duckdb(csv_path)
    print("Done.")