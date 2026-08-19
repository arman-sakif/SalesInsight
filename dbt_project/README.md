# dbt_project

The transformation layer for [SalesInsight](../README.md): DuckDB raw tables in,
a star schema out. Ten models across three layers, 23 data tests.

```bash
cd dbt_project     # dbt reads the project directory, so this cd is required
uv run dbt build   # 33 nodes: 10 models + 23 tests
uv run dbt docs generate && uv run dbt docs serve
```

`profiles.yml` is **committed here on purpose** so CI and fresh clones build
without machine-specific configuration. dbt reads the project directory before
`~/.dbt`, so this one wins locally too. It resolves `../data/warehouse.db`, or
`SALESINSIGHT_DB_PATH` if that is set. The profile name is `dbt_project`.

## Layers

| Layer | Models | Responsibility |
|---|---|---|
| `models/staging` | `stg_orders`, `stg_customers`, `stg_products` | Clean and conform: type dates, dedupe, repair the source's column-rotation defect |
| `models/intermediate` | `int_orders_enriched`, `int_customer_segments` | Business logic: derived metrics, and RFM scoring in SQL with `ntile(4)` |
| `models/marts` | `fact_sales`, `dim_customer`, `dim_product`, `dim_date`, `dim_region` | The star schema every consumer reads |

The marts are the contract. Power BI imports them as Parquet, the MCP server
queries them read-only, and the Streamlit app reads whichever of the two is
available — so a metric is defined once, here, rather than three times
downstream.

## Two things to know before editing

- **The staging layer repairs source data, and that repair must survive.** Rows
  whose `category` is not one of `Furniture` / `Office Supplies` /
  `Technology` have three columns rotated. `stg_orders.sql` and
  `stg_products.sql` correct it with CASE logic and drop nothing. Deleting that
  logic silently corrupts every downstream category cut.
- **`dim_date` starts 2014-01-01**, not 2016, because orders go back to 2014. A
  shorter spine leaves a blank date bucket in Power BI.

Full project context, including the pipeline order and the DuckDB single-writer
constraint, is in the [root README](../README.md).
