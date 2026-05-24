with products as (
    select * from {{ ref('stg_products') }}
)

select
    product_id,
    product_name,
    category,
    sub_category
from products