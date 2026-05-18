with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

enriched as (
    select
        o.row_id,
        o.order_id,
        o.order_date,
        o.ship_date,
        o.ship_mode,
        date_diff('day', o.order_date, o.ship_date)  as days_to_ship,
        o.customer_id,
        o.customer_name,
        o.segment,
        o.country,
        o.city,
        o.state,
        o.postal_code,
        o.region,
        o.product_id,
        p.product_name,
        p.category,
        p.sub_category,
        o.sales_amount,
        o.quantity,
        o.discount,
        o.profit,
        round(o.profit / nullif(o.sales_amount, 0) * 100, 2)  as profit_margin_pct,
        round(o.sales_amount / nullif(o.quantity, 0), 2)       as avg_unit_price,
        o.is_synthetic,
        year(o.order_date)                                     as order_year,
        month(o.order_date)                                    as order_month,
        dayofweek(o.order_date)                                as order_day_of_week
    from orders o
    left join products p on o.product_id = p.product_id
    left join customers c on o.customer_id = c.customer_id
)

select * from enriched