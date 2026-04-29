{{ config(
    materialized='table',
    alias='mart_pitcher_era_by_inning',
    description='Pitcher ERA statistics aggregated by inning',
    tags=['pitcher_performance', 'era']
) }}

SELECT
  game_year,
  pitcher,
  pitcher_name,
  pitcher_team,
  inning,
  SUM(outs_this_pa)                                AS total_outs,
  ROUND(SUM(outs_this_pa) / 3.0, 1)               AS innings_pitched,
  SUM(runs_this_pa)                                AS runs_allowed,
  SUM(earned_runs)                                 AS earned_runs,
  CASE WHEN SUM(outs_this_pa) = 0 THEN NULL
    ELSE ROUND(SUM(earned_runs) / (SUM(outs_this_pa) / 3.0) * 9, 2)
  END AS era_by_inning
FROM {{ ref('int_pitcher_pa_with_runs') }}
GROUP BY game_year, pitcher, pitcher_name, pitcher_team, inning
ORDER BY game_year, pitcher_name, inning
