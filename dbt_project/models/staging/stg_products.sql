with source as (
    select * from {{ source('raw', 'raw_orders') }}
),

distinct_products as (
    select
        cast(product_id as varchar)      as product_id,
        cast(product_name as varchar)    as product_name,
        cast(category as varchar)        as category,
        cast(sub_category as varchar)    as sub_category
    from source
    where product_id is not null
    qualify row_number() over (
        partition by product_id
        order by product_name
    ) = 1
)

select * from distinct_products