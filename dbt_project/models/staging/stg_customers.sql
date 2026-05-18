with source as (
    select * from {{ source('raw', 'raw_orders') }}
),

distinct_customers as (
    select distinct
        cast(customer_id as varchar)     as customer_id,
        cast(customer_name as varchar)   as customer_name,
        cast(segment as varchar)         as segment
    from source
    where customer_id is not null
)

select * from distinct_customers