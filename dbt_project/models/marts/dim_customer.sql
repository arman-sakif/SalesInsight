with customers as (
    select * from {{ ref('stg_customers') }}
),

rfm as (
    select * from {{ ref('int_customer_segments') }}
),

joined as (
    select
        c.customer_id,
        c.customer_name,
        c.segment,
        r.frequency,
        r.monetary,
        r.recency_days,
        r.last_order_date,
        r.r_score,
        r.f_score,
        r.m_score,
        r.rfm_total,
        r.rfm_segment
    from customers c
    left join rfm r on c.customer_id = r.customer_id
)

select * from joined