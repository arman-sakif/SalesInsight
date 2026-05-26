with source as (
    select * from {{ source('raw', 'raw_orders') }}
),

cleaned as (
    select
        cast(row_id as varchar)                    as row_id,
        cast(order_id as varchar)                  as order_id,
        case
            when order_date like '%/%'
            then strptime(order_date, '%m/%d/%Y')::date
            else cast(order_date as date)
        end                                        as order_date,
        case
            when ship_date like '%/%'
            then strptime(ship_date, '%m/%d/%Y')::date
            else cast(ship_date as date)
        end                                        as ship_date,
        cast(ship_mode as varchar)                 as ship_mode,
        cast(customer_id as varchar)               as customer_id,
        cast(customer_name as varchar)             as customer_name,
        cast(segment as varchar)                   as segment,
        cast(country as varchar)                   as country,
        cast(city as varchar)                      as city,
        cast(state as varchar)                     as state,
        cast(postal_code as varchar)               as postal_code,
        cast(region as varchar)                    as region,
        cast(product_id as varchar)                as product_id,
        case
            when cast(category as varchar)
                not in ('Furniture', 'Office Supplies', 'Technology')
            then cast(category as varchar)
            else cast(product_name as varchar)
        end                                        as product_name,
        case
            when cast(category as varchar)
                not in ('Furniture', 'Office Supplies', 'Technology')
            then cast(sub_category as varchar)
            else cast(category as varchar)
        end                                        as category,
        case
            when cast(category as varchar)
                not in ('Furniture', 'Office Supplies', 'Technology')
            then cast(product_name as varchar)
            else cast(sub_category as varchar)
        end                                        as sub_category,
        cast(sales as decimal(10, 2))              as sales_amount,
        cast(quantity as integer)                  as quantity,
        cast(discount as decimal(5, 2))            as discount,
        cast(profit as decimal(10, 2))             as profit,
        case
            when row_id like 'SYN-%' then true
            else false
        end                                        as is_synthetic
    from source
    where order_id is not null
)

select * from cleaned