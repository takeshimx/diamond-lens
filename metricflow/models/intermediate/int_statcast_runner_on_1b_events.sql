{{ config(
    materialized='view',
    description='Statcast events with runner on 1st base only - no other runners'
) }}

SELECT *
FROM {{ ref('fact_statcast_events') }}
WHERE events IS NOT NULL
  AND (on_1b != 0 AND on_2b = 0 AND on_3b = 0)
