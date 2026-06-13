import duckdb
import pandas as pd
import numpy as np
from faker import Faker
from pathlib import Path
from datetime import date, timedelta
import random

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "warehouse.db"

SHIP_MODES = ["Second Class", "Standard Class", "First Class", "Same Day"]
SHIP_MODE_WEIGHTS = [0.30, 0.50, 0.15, 0.05]

SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SEGMENT_WEIGHTS = [0.52, 0.30, 0.18]

REGIONS = ["West", "East", "Central", "South"]
REGION_WEIGHTS = [0.32, 0.28, 0.22, 0.18]

REGION_STATES = {
    "West":    ["California", "Washington", "Oregon", "Nevada", "Arizona"],
    "East":    ["New York", "Pennsylvania", "Ohio", "Virginia", "Florida"],
    "Central": ["Texas", "Illinois", "Michigan", "Indiana", "Wisconsin"],
    "South":   ["North Carolina", "Georgia", "Tennessee", "Alabama", "Kentucky"],
}

def load_reference_data(conn) -> dict:
    """Load existing customers, products and stats from real data."""
    print("Loading reference data from raw.raw_orders...")

    customers = conn.execute("""
        SELECT DISTINCT customer_id, customer_name, segment
        FROM raw.raw_orders
    """).fetchdf()

    products = conn.execute("""
        SELECT DISTINCT product_id, product_name, category, sub_category
        FROM raw.raw_orders
    """).fetchdf()

    stats = conn.execute("""
        SELECT
            category,
            AVG(CAST(sales AS DOUBLE))     AS avg_sales,
            STDDEV(CAST(sales AS DOUBLE))  AS std_sales,
            AVG(CAST(discount AS DOUBLE))  AS avg_discount,
            AVG(CAST(quantity AS INTEGER)) AS avg_quantity
        FROM raw.raw_orders
        GROUP BY category
    """).fetchdf()

    return {
        "customers": customers,
        "products": products,
        "stats": stats,
    }




def generate_orders(ref: dict, n_orders: int, target_date: date) -> pd.DataFrame:
    """Generate n_orders synthetic orders for a given date."""
    customers = ref["customers"]
    products  = ref["products"]
    stats     = ref["stats"]

    rows = []
    for i in range(n_orders):
        # Sample a customer and product
        customer = customers.sample(1).iloc[0]
        product  = products.sample(1).iloc[0]

        # Look up stats for this product's category
        cat_stats = stats[stats["category"] == product["category"]]
        if cat_stats.empty:
            avg_sales, std_sales, avg_discount, avg_qty = 100, 50, 0.1, 2
        else:
            avg_sales    = float(cat_stats["avg_sales"].iloc[0])
            std_sales    = float(cat_stats["std_sales"].iloc[0])
            avg_discount = float(cat_stats["avg_discount"].iloc[0])
            avg_qty      = float(cat_stats["avg_quantity"].iloc[0])

        # Generate realistic values
        quantity = max(1, int(np.random.poisson(avg_qty)))
        sales    = max(1.0, round(np.random.normal(avg_sales, std_sales), 2))
        discount = round(min(max(np.random.normal(avg_discount, 0.05), 0), 0.5), 2)
        profit = round(sales * (np.random.uniform(0.05, 0.35) - discount), 2)

        region = random.choices(REGIONS, REGION_WEIGHTS)[0]
        state  = random.choice(REGION_STATES[region])
        city   = fake.city()

        order_date    = target_date
        ship_days     = random.choices([2, 3, 5, 7], [0.15, 0.30, 0.40, 0.15])[0]
        ship_date     = order_date + timedelta(days=ship_days)

        rows.append({
            "row_id":        f"SYN-{target_date.strftime('%Y%m%d')}-{i+1:04d}",
            "order_id":      f"SYN-{fake.bothify('??-####-######').upper()}",
            "order_date":    order_date.strftime("%Y-%m-%d"),
            "ship_date":     ship_date.strftime("%Y-%m-%d"),
            "ship_mode":     random.choices(SHIP_MODES, SHIP_MODE_WEIGHTS)[0],
            "customer_id":   customer["customer_id"],
            "customer_name": customer["customer_name"],
            "segment":       customer["segment"],
            "country":       "United States",
            "city":          city,
            "state":         state,
            "postal_code":   fake.postcode(),
            "region":        region,
            "product_id":    product["product_id"],
            "product_name":  product["product_name"],
            "category":      product["category"],
            "sub_category":  product["sub_category"],
            "sales":         sales,
            "quantity":      quantity,
            "discount":      discount,
            "profit":        profit,
        })

    return pd.DataFrame(rows)


def migrate_schema(conn) -> None:
    """Ensure row_id is VARCHAR to support both real and synthetic IDs."""
    col_type = conn.execute("""
        SELECT data_type 
        FROM information_schema.columns
        WHERE table_schema = 'raw'
        AND table_name = 'raw_orders'
        AND column_name = 'row_id'
    """).fetchone()[0]

    if col_type != "VARCHAR":
        print("Migrating row_id column to VARCHAR...")
        conn.execute("""
            ALTER TABLE raw.raw_orders 
            ALTER COLUMN row_id TYPE VARCHAR
        """)
        print("Migration done.")


def append_to_duckdb(df: pd.DataFrame, conn) -> None:
    """Append synthetic orders to raw.raw_orders."""
    migrate_schema(conn)
    conn.execute("INSERT INTO raw.raw_orders SELECT * FROM df")
    print(f"Inserted {len(df):,} synthetic rows")


def run(days_back: int = 0, n_orders: int = None):
    """
    Generate synthetic orders.
    days_back=0 means today, days_back=1 means yesterday, etc.
    n_orders defaults to a random realistic daily volume.
    """
    target_date = date.today() - timedelta(days=days_back)
    if n_orders is None:
        n_orders = random.randint(50, 150)

    print(f"Generating {n_orders} synthetic orders for {target_date}...")

    conn = duckdb.connect(str(DB_PATH))
    ref  = load_reference_data(conn)
    df   = generate_orders(ref, n_orders, target_date)
    append_to_duckdb(df, conn)

    total = conn.execute("SELECT COUNT(*) FROM raw.raw_orders").fetchone()[0]
    print(f"Total rows in raw.raw_orders: {total:,}")
    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()