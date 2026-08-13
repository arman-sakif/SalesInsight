import argparse
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
    print("Downloading dataset from Kaggle...")
    path = kagglehub.dataset_download(DATASET)
    csv_files = list(Path(path).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {path}")
    dest = RAW_DIR / "superstore.csv"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(csv_files[0], dest)
    print(f"Saved to {dest}")
    return dest

def local_dataset() -> Path:
    """Return the committed CSV, skipping the Kaggle download.

    CI has no Kaggle credentials, so the workflows rebuild the raw layer from
    the snapshot committed at data/raw/superstore.csv.
    """
    dest = RAW_DIR / "superstore.csv"
    if not dest.exists():
        raise FileNotFoundError(
            f"No local CSV at {dest}. Run without --local to download it from Kaggle."
        )
    print(f"Using local CSV at {dest}")
    return dest

def load_to_duckdb(csv_path: Path) -> None:
    print("Loading into DuckDB...")
    df = pd.read_csv(csv_path, encoding="latin-1")
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    print(f"Rows loaded: {len(df):,}")
    print(f"Columns: {list(df.columns)}")
    conn = duckdb.connect(str(DB_PATH))
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.raw_orders")
    conn.execute("CREATE TABLE raw.raw_orders AS SELECT * FROM df")
    count = conn.execute("SELECT COUNT(*) FROM raw.raw_orders").fetchone()[0]
    print(f"raw.raw_orders created with {count:,} rows")
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the Superstore CSV into DuckDB raw schema.")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use the committed data/raw/superstore.csv instead of downloading from Kaggle.",
    )
    args = parser.parse_args()

    csv_path = local_dataset() if args.local else download_dataset()
    load_to_duckdb(csv_path)
    print("Done.")