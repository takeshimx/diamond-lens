{{ config(
    materialized='table',
    alias='mart_pitcher_era_by_game',
    description='Pitcher ERA statistics aggregated by game',
    tags=['pitcher_performance', 'era']
) }}

SELECT
  game_year,
  game_pk,
  pitcher,
  pitcher_name,
  pitcher_team,
  SUM(outs_this_pa)                                AS total_outs,
  ROUND(SUM(outs_this_pa) / 3.0, 1)               AS innings_pitched,
  SUM(runs_this_pa)                                AS runs_allowed,
  SUM(earned_runs)                                 AS earned_runs,
  CASE WHEN SUM(outs_this_pa) = 0 THEN NULL
    ELSE ROUND(SUM(earned_runs) / (SUM(outs_this_pa) / 3.0) * 9, 2)
  END AS era
FROM {{ ref('int_pitcher_pa_with_runs') }}
GROUP BY game_year, game_pk, pitcher, pitcher_name, pitcher_team
ORDER BY game_pk, pitcher_name
