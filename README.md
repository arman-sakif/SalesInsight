# SalesInsight — AI-Powered Sales Intelligence Platform

[![CI](https://github.com/arman-sakif/SalesInsight/actions/workflows/ci.yml/badge.svg)](https://github.com/arman-sakif/SalesInsight/actions/workflows/ci.yml)
[![Refresh data](https://github.com/arman-sakif/SalesInsight/actions/workflows/refresh-data.yml/badge.svg)](https://github.com/arman-sakif/SalesInsight/actions/workflows/refresh-data.yml)

> **Status: In Progress** — Data pipeline, semantic model, Power BI dashboard, MCP server, Streamlit web app, and CI/CD complete.

### 🚀 [Live app → sales-insight-9011.streamlit.app](https://sales-insight-9011.streamlit.app/)

Explore the interactive four-page dashboard in your browser — no install required.

A portfolio project demonstrating end-to-end data engineering, semantic modelling, BI development, and AI integration. Built entirely with free and open-source tools.

---

## What's Built So Far

| Layer | Status | Tools |
|---|---|---|
| Data ingestion pipeline | ✅ Complete | Python, kagglehub, DuckDB |
| Synthetic data generator | ✅ Complete | Python, Faker, NumPy |
| dbt transformation pipeline | ✅ Complete | dbt Core, dbt-duckdb |
| Star schema (marts layer) | ✅ Complete | DuckDB |
| Power BI semantic model | ✅ Complete | Power BI Desktop |
| Power BI dashboard (4 pages) | ✅ Complete | Power BI Desktop |
| MCP server (8 AI tools) | ✅ Complete | Python, Anthropic MCP SDK |
| Streamlit web app (4 pages) | ✅ Complete | Streamlit |
| GitHub Actions CI/CD | ✅ Complete | GitHub Actions, pytest, ruff |

---

## Tech Stack

- **Warehouse:** DuckDB (local, file-based)
- **Transformations:** dbt Core with dbt-duckdb adapter
- **Dashboard:** Power BI Desktop
- **AI Integration:** Model Context Protocol (MCP) server, connected to Claude Desktop
- **Package management:** uv
- **Language:** Python 3.12

---

## Architecture

```
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
           ┌────────────┴────────────┐
           ▼                         ▼
   Power BI Semantic Model     MCP Server (Python)
   ├── 16 DAX measures         ├── 8 AI-queryable tools
   └── 4 report pages          └── Connected to Claude Desktop
```

---

## Data

- **Source:** [Kaggle Sample Superstore](https://www.kaggle.com/datasets/konstantinognev/sample-superstorecsv)
- **Historical rows:** 9,994 real orders (2014–2017)
- **Synthetic rows:** Generated daily using statistical distributions from real data
- **Data quality:** Staging layer corrects column-rotation issues in the source data with no data loss

---

## dbt Models

### Staging
| Model | Description |
|---|---|
| `stg_orders` | Cleaned and typed orders with date parsing, category correction, and synthetic flag |
| `stg_customers` | Distinct customers with segment |
| `stg_products` | Distinct products, deduplicated and category-corrected |

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

## MCP Server

A Model Context Protocol server that exposes the sales warehouse as AI-queryable tools. Connected to Claude Desktop, it lets you ask natural-language questions and get real answers from the live DuckDB warehouse — the same semantic layer the Power BI dashboard visualizes.

### Available Tools
| Tool | Description |
|---|---|
| `query_metric` | Query a core metric (revenue, profit, margin, orders, AOV, units, customers) |
| `explain_metric` | Explain what a metric means and how it's calculated |
| `get_top_customers` | Top N customers by revenue with RFM segment |
| `get_rfm_segments` | Customer distribution across RFM segments |
| `revenue_by_region` | Revenue, profit, and margin by region |
| `get_product_performance` | Top products, optionally filtered by category |
| `get_category_breakdown` | Revenue, margin, and average discount by category and sub-category |
| `get_discount_impact` | Discount-vs-margin analysis: revenue, margin, and profit by discount band |

### Example

> **You:** What's my total revenue and gross profit margin?
>
> **Claude:** *(calls `query_metric` twice)* Your total revenue is $2.34M with a gross profit margin of 13.3%.

Because the MCP tools query the exact tables dbt builds, the AI's answers stay consistent with the dashboard — one semantic layer, many interfaces.

---

## Web App (Streamlit)

A recruiter-facing web app that turns the same semantic layer into an interactive, four-page dashboard — no Power BI Desktop required. Each page reuses the exact MCP tool functions, so the web figures match the Power BI report and the AI answers.

**🚀 Live: [sales-insight-9011.streamlit.app](https://sales-insight-9011.streamlit.app/)** — deployed on Streamlit Community Cloud, serving the committed Parquet marts.

Run it locally with:

```bash
uv run streamlit run app/streamlit_app.py
```

**Executive Overview** — Headline KPIs (revenue, profit, margin, orders, AOV, customers), revenue by region, and an expandable metric glossary backed by `explain_metric`.

![Streamlit — Executive Overview](docs/screenshots/streamlit_home.png)

**Customer Intelligence** — Top-N customers by revenue with their RFM segment, plus the RFM segment distribution.

![Streamlit — Customer Intelligence](docs/screenshots/streamlit_customer_intelligence.png)

**Regional Performance** — Revenue, profit, and margin by region with summary tiles and comparative charts.

![Streamlit — Regional Performance](docs/screenshots/streamlit_regional_performance.png)

**Product Intelligence** — Top products by category, category/sub-category margins, and a discount-vs-margin analysis showing how margin erodes as discounts deepen.

![Streamlit — Product Intelligence](docs/screenshots/streamlit_Product_Intelligence.png)

---

## CI/CD (GitHub Actions)

Two workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | every pull request and push to `master` | Lints with ruff, rebuilds the warehouse from the committed CSV, runs `dbt build` (5 models + 23 data tests), exports the marts, and smoke-tests the MCP tools with pytest |
| `refresh-data.yml` | weekly cron + manual dispatch | Same pipeline, then commits the refreshed `data/parquet/*.parquet` back to `master`, which triggers a Streamlit Community Cloud redeploy |

Two details worth calling out:

- **No Kaggle credentials in CI.** `kaggle_loader.py --local` loads the CSV snapshot committed at `data/raw/superstore.csv` instead of re-downloading the dataset, so the workflows need no secrets.
- **The refresh regenerates rather than appends.** `warehouse.db` is gitignored, so each run starts from the raw CSV and generates a rolling window of synthetic orders through today (`synthetic_generator.py --days 7`). The hosted app therefore always shows data up to the last refresh.

### Retention

`synthetic_generator.py` applies a one-year retention policy after generating, so the warehouse keeps at most 365 days of generated history:

```bash
uv run python ingestion/synthetic_generator.py --days 7 --retain-days 365  # default
uv run python ingestion/synthetic_generator.py --days 0                    # prune only, generate nothing
uv run python ingestion/synthetic_generator.py --no-prune                  # generate without pruning
```

It deletes only rows with a `SYN-` prefix. The 2014–2017 Kaggle baseline is never pruned — it is the historical data the year-over-year views and RFM recency scores are built on, and a blanket cutoff would take all 9,994 rows of it.

The refresh runs weekly rather than daily on purpose: each run rewrites roughly 500 KB of binary Parquet, and daily commits would add ~190 MB of history a year. Change the cron in `refresh-data.yml` to `"0 6 * * *"` for a daily refresh.

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

# Test the MCP server in the MCP Inspector
uv run mcp dev mcp_server/server.py

# Launch the Streamlit web app
uv run streamlit run app/streamlit_app.py

# Run the checks CI runs
uv run ruff check .
uv run pytest
```

No Kaggle account? Skip the `.env` step and load the committed CSV snapshot instead:

```bash
uv run python ingestion/kaggle_loader.py --local
```

`synthetic_generator.py` appends one day of orders by default; pass `--days 7` to generate a week. It always appends to whatever is already in `raw.raw_orders`, so re-run `kaggle_loader.py --local` first if you want a clean rebuild rather than more history. It also prunes generated history older than a year on each run — see [Retention](#retention).

### Connecting the MCP Server to Claude Desktop

Add the following to your `claude_desktop_config.json` (adjust the paths to match your machine), then restart Claude Desktop:

```json
{
  "mcpServers": {
    "salesinsight": {
      "command": "C:\\Users\\<you>\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\path\\to\\SalesInsight",
        "run",
        "python",
        "-m",
        "mcp_server.server"
      ]
    }
  }
}
```

---

## Project Background

Built as a portfolio project following completion of a Master of Applied Computing (Artificial Intelligence) at the University of Windsor. Demonstrates skills in data engineering, semantic modelling, BI development, and AI integration.

---

## Coming Soon

- Bonus AI tools: natural-language-to-SQL, anomaly detection, executive summary generation, dbt lineage explainer
- Discount-vs-margin visual on the Power BI Product Intelligence page (the data and MCP tool are already in place)

---

*Author Info: [Arman Sakif](https://github.com/arman-sakif)*
