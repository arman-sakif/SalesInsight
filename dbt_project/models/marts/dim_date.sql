with date_spine as (
    select
        unnest(
            generate_series(
                '2016-01-01'::date,
                current_date,
                interval '1 day'
            )
        )::date as date_day
),

enriched as (
    select
        date_day,
        year(date_day)                                      as year,
        month(date_day)                                     as month,
        day(date_day)                                       as day,
        quarter(date_day)                                   as quarter,
        dayofweek(date_day)                                 as day_of_week,
        dayname(date_day)                                   as day_name,
        monthname(date_day)                                 as month_name,
        weekofyear(date_day)                                as week_of_year,
        case when dayofweek(date_day) in (0, 6)
            then true else false
        end                                                 as is_weekend,
        strftime(date_day, '%Y-%m')                         as year_month
    from date_spine
)

select * from enriched