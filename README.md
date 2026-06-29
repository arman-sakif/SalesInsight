# SalesInsight — AI-Powered Sales Intelligence Platform

> **Status: In Progress** — Data pipeline, semantic model, and Power BI dashboard complete. MCP server and web app coming soon.

A portfolio project demonstrating end-to-end data engineering, semantic modelling, and AI integration skills. Built entirely with free and open-source tools.

---

## What's Built So Far

| Layer | Status | Tools |
|---|---|---|
| Data ingestion pipeline | ✅ Complete | Python, kagglehub, DuckDB |
| Synthetic data generator | ✅ Complete | Python, Faker, NumPy |
| dbt transformation pipeline | ✅ Complete | dbt Core, dbt-duckdb |
| Star schema (marts layer) | ✅ Complete | DuckDB |
| Power BI semantic model | ✅ Complete | Power BI Desktop |
| Power BI dashboard | ✅ Complete | Power BI Desktop |
| MCP server | 🔜 Coming soon | Python, Anthropic MCP SDK |
| Streamlit web app | 🔜 Coming soon | Streamlit |
| GitHub Actions CI/CD | 🔜 Coming soon | GitHub Actions |

---

## Tech Stack

- **Warehouse:** DuckDB (local, file-based)
- **Transformations:** dbt Core with dbt-duckdb adapter
- **Dashboard:** Power BI Desktop
- **Package management:** uv
- **Language:** Python 3.12

---

## Data Pipeline Architecture

Kaggle Superstore (historical)     Synthetic Generator (daily)
         │                                    │
         └──────────────┬────────────────────┘
                        │
                        ▼
             Ingestion Layer (Python)
                        │
                        ▼
             DuckDB — Raw Schema
                        │
                        ▼
             dbt Core Transformations
             ├── Staging layer (views)
             ├── Intermediate layer (views)
             │   └── RFM customer segmentation
             └── Marts layer (tables)
                 ├── fact_sales
                 ├── dim_customer
                 ├── dim_product
                 ├── dim_date
                 └── dim_region
                        │
                        ▼
             Power BI Semantic Model
             └── 16 DAX measures

---

## Data

- **Source:** [Kaggle Sample Superstore](https://www.kaggle.com/datasets/konstantinognev/sample-superstorecsv)
- **Historical rows:** 9,994 real orders (2014–2017)
- **Synthetic rows:** Generated daily using statistical distributions from real data
- **Total rows:** 10,000+

---

## dbt Models

### Staging
| Model | Description |
|---|---|
| `stg_orders` | Cleaned and typed orders with date parsing and synthetic flag |
| `stg_customers` | Distinct customers with segment |
| `stg_products` | Distinct products deduplicated by product ID |

### Intermediate
| Model | Description |
|---|---|
| `int_orders_enriched` | Orders joined with products, with derived metrics (profit margin, days to ship) |
| `int_customer_segments` | RFM scored customers with segment labels (Champions, Loyal, At Risk, Lost) |

### Marts
| Model | Description |
|---|---|
| `fact_sales` | One row per order line, central fact table |
| `dim_customer` | One row per customer with RFM segment |
| `dim_product` | One row per product with category hierarchy |
| `dim_date` | Date spine from 2014 to today with calendar attributes |
| `dim_region` | One row per region (West, East, Central, South) |

---

## Power BI Semantic Model

- 4 active relationships (star schema)
- 16 DAX measures across revenue, profit, customers, time intelligence, and shipping
- 5 calculated columns
- Time intelligence: MTD, YTD, vs Prior Month, vs Prior Year

### Dashboard Preview

The semantic model powers a four-page Power BI report. Each page targets a different analytical question while sharing the same star schema and DAX measures.

**Executive Summary** — Headline KPIs (total revenue, total profit, gross profit margin, total orders), a rolling 52-week revenue and profit-margin trend, revenue split by customer segment, and a top-customers table.

![Executive Summary](docs/screenshots/executive_summary.png)

**Regional Sales Summary** — Shipping performance by region, revenue mapped by state, a region → category → sub-category revenue breakdown, and revenue ranked by region.

![Regional Sales Summary](docs/screenshots/regional_summary.png)

**Product Intelligence** — Revenue vs. profit by order size, a profit-margin vs. revenue scatter by sub-category, revenue by category, revenue by sub-category, and a product performance table.

![Product Intelligence](docs/screenshots/product_intelligence.png)

**Customer Analytics** — Revenue vs. profit by order size, a business-segment vs. RFM-segment matrix, customer distribution by RFM segment, a frequency-vs-spend value map, and a top-customers table with recency.

![Customer Analytics](docs/screenshots/customer_analytics.png)

---

## How to Run Locally

**Prerequisites:** Python 3.12+, uv, git

```bash
# Clone the repo
git clone https://github.com/arman-sakif/SalesInsight.git
cd SalesInsight

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Add your KAGGLE_USERNAME and KAGGLE_KEY to .env

# Run ingestion
uv run python ingestion/kaggle_loader.py
uv run python ingestion/synthetic_generator.py

# Run dbt transformations
cd dbt_project
uv run dbt build
cd ..

# Export to Parquet for Power BI
uv run python ingestion/export_parquet.py
```

---

## Project Background

Built as a portfolio project following completion of a Master of Applied Computing (Artificial Intelligence) at the University of Windsor. Demonstrates skills in data engineering, semantic modelling, BI development, and AI integration.

---

## Coming Soon

- MCP server exposing business metrics as AI-queryable tools
- Streamlit web app with embedded dashboard and AI chat interface
- GitHub Actions CI/CD with daily automated data refresh
- Public dashboard via Power BI Service or alternative

---

*Built by [Arman Sakif](https://github.com/arman-sakif)*