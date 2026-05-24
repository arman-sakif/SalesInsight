with orders as (
    select * from {{ ref('stg_orders') }}
),

regions as (
    select
        region,
        country,
        count(distinct state)   as state_count,
        count(distinct city)    as city_count
    from orders
    where region is not null
    group by region, country
)

select * from regions