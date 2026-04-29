{{ config(
    materialized='view',
    description='Statcast events with runners in scoring position (RISP) - 2nd or 3rd base occupied'
) }}

SELECT *
FROM {{ ref('fact_statcast_events') }}
WHERE events IS NOT NULL
  AND (on_2b != 0 OR on_3b != 0)
