{{ config(
    materialized='table',
    alias='mart_pitcher_risp_performance',
    description='Pitcher performance metrics in RISP vs non-RISP situations',
    tags=['pitcher_performance']
) }}

SELECT
  s.pitcher,
  dst.full_name AS pitcher_name,
  dst.team_abbr AS team,
  s.game_year   AS season,
  CASE
    WHEN s.on_2b != 0 OR s.on_3b != 0 THEN 'risp'
    ELSE 'non_risp'
  END AS situation,

  -- サンプルサイズ
  COUNT(*) AS pa,
  COUNTIF(s.events IN ('single', 'double', 'triple', 'home_run')) AS hits,
  COUNTIF(s.events = 'home_run') AS home_runs,

  -- BAA（被打率）
  ROUND(SAFE_DIVIDE(
    COUNTIF(s.events IN ('single', 'double', 'triple', 'home_run')),
    COUNTIF(s.events NOT IN ('walk', 'intent_walk', 'hit_by_pitch', 'sac_fly', 'sac_bunt', 'catcher_interf'))
  ), 3) AS baa,

  -- xwOBA
  ROUND(AVG(CASE WHEN s.woba_denom = 1 THEN s.estimated_woba_using_speedangle END), 3) AS xwoba,

  -- K%
  ROUND(SAFE_DIVIDE(
    COUNTIF(s.events IN ('strikeout', 'strikeout_double_play')),
    COUNT(*)
  ), 3) AS k_pct,

  -- BB%（故意四球除く）
  ROUND(SAFE_DIVIDE(
    COUNTIF(s.events = 'walk'),
    COUNT(*)
  ), 3) AS bb_pct,

  -- Hard Hit%
  ROUND(SAFE_DIVIDE(
    COUNTIF(s.launch_speed IS NOT NULL AND s.launch_speed >= 95),
    COUNTIF(s.events NOT IN ('walk', 'intent_walk', 'hit_by_pitch', 'catcher_interf', 'strikeout', 'strikeout_double_play'))
  ), 3) AS hard_hit_pct

FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
  ON s.pitcher = dst.mlb_id AND s.game_year = dst.season
WHERE
  s.game_type = 'R'
  AND s.events IS NOT NULL
  AND s.events NOT IN (
    'truncated_pa',
    'caught_stealing_2b', 'caught_stealing_3b', 'caught_stealing_home',
    'pickoff_1b', 'pickoff_2b', 'pickoff_3b',
    'stolen_base_2b', 'stolen_base_3b', 'stolen_base_home'
  )
GROUP BY
  s.pitcher, pitcher_name, team, s.game_year, situation
