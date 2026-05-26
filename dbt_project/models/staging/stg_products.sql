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
),

corrected as (
    select
        product_id,
        case
            when category not in ('Furniture', 'Office Supplies', 'Technology')
            then category
            else product_name
        end                              as product_name,
        case
            when category not in ('Furniture', 'Office Supplies', 'Technology')
            then sub_category
            else category
        end                              as category,
        case
            when category not in ('Furniture', 'Office Supplies', 'Technology')
            then product_name
            else sub_category
        end                              as sub_category
    from distinct_products
)

select * from corrected