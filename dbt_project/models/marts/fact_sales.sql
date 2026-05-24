with orders as (
    select * from {{ ref('int_orders_enriched') }}
)

select
    row_id                                        as order_line_id,
    order_id,
    order_date,
    ship_date,
    ship_mode,
    days_to_ship,
    customer_id,
    product_id,
    region,
    state,
    city,
    sales_amount,
    quantity,
    discount,
    profit,
    profit_margin_pct,
    avg_unit_price,
    order_year,
    order_month,
    order_day_of_week,
    is_synthetic
from orders