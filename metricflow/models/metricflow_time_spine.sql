{{ config(materialized='table') }}

select date_day
from unnest(
    generate_date_array(date '2019-01-01', current_date(), interval 1 day)
) as date_day
