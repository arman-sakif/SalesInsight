with orders as (
    select * from {{ ref('stg_orders') }}
),

rfm_base as (
    select
        customer_id,
        customer_name,
        segment,
        count(distinct order_id)                 as frequency,
        sum(sales_amount)                        as monetary,
        max(order_date)                          as last_order_date,
        date_diff('day', max(order_date), current_date) as recency_days
    from orders
    group by customer_id, customer_name, segment
),

rfm_scored as (
    select
        *,
        ntile(4) over (order by recency_days asc)  as r_score,
        ntile(4) over (order by frequency desc)    as f_score,
        ntile(4) over (order by monetary desc)     as m_score
    from rfm_base
),

rfm_labelled as (
    select
        customer_id,
        customer_name,
        segment,
        frequency,
        round(monetary, 2)                        as monetary,
        recency_days,
        last_order_date,
        r_score,
        f_score,
        m_score,
        (r_score + f_score + m_score)             as rfm_total,
        case
            when (r_score + f_score + m_score) >= 10 then 'Champions'
            when (r_score + f_score + m_score) >= 8  then 'Loyal Customers'
            when (r_score + f_score + m_score) >= 6  then 'Potential Loyalists'
            when (r_score + f_score + m_score) >= 4  then 'At Risk'
            else 'Lost'
        end                                       as rfm_segment
    from rfm_scored
)

select * from rfm_labelled