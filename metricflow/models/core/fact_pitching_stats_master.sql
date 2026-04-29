-- dbt model to create a master table for pitching statistics with player information
{{ config(
    materialized='table',
    description='Master table for pitching statistics with player information',
    tags=['pitching_stats', 'master'],
    alias='fact_pitching_stats_master',
    enabled=True
)}}
SELECT
  a.*,
  b.mlb_id as mlbid,
  b.* EXCEPT(mlb_id, fangraphs_id, team, league),
FROM {{ ref('fact_pitching_stats') }} a
LEFT JOIN {{ source('mlb_raw_data', 'dim_players') }} b ON a.idfg = b.fangraphs_id
WHERE b.fangraphs_id IS NOT NULL