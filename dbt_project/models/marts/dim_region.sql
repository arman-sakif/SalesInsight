with orders as (
    select * from {{ ref('stg_orders') }}
),

regions as (
    select
        state,
        region,
        country,
        max(city)         as city,
        max(postal_code)  as postal_code
    from orders
    where state is not null
    group by state, region, country
)

select * from regions