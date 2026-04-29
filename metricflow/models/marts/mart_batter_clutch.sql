{{ config(
    materialized='table',
    alias='mart_batter_clutch',
    description='Batting statistics in clutch situations: bases_loaded, risp, on_1b, no_runner',
    tags=['batter_performance', 'clutch']
) }}

WITH statcast AS (
  SELECT
    s.game_year,
    s.batter                                              AS batter_id,
    dst.full_name                                         AS batter_name,
    dst.team_abbr                                         AS team,
    CASE
      WHEN s.on_1b != 0 AND s.on_2b != 0 AND s.on_3b != 0  THEN 'bases_loaded'
      WHEN s.on_2b != 0 OR  s.on_3b != 0                    THEN 'risp'
      WHEN s.on_1b != 0                                      THEN 'on_1b'
      ELSE                                                        'no_runner'
    END                                                   AS situation_type,
    s.events,
    s.description,
    s.launch_angle,
    s.launch_speed,
    s.bat_speed,
    s.swing_length,
    s.woba_value,
    s.woba_denom,
    s.estimated_woba_using_speedangle                     AS xwoba_value,
    s.launch_speed >= 95                                  AS is_hard_hit,
    (s.launch_angle BETWEEN 8 AND 32
      AND s.launch_speed >= 98)                           AS is_barrel
  FROM {{ ref('statcast_master') }} s
  LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.batter = dst.mlb_id AND s.game_year = dst.season
  WHERE s.events IS NOT NULL
    AND dst.full_name IS NOT NULL
),

aggregated AS (
  SELECT
    game_year,
    batter_name,
    batter_id,
    team,
    situation_type,

    -- Volume
    COUNT(*)                                                            AS pa,
    COUNTIF(events IN ('single','double','triple','home_run'))          AS hits,
    COUNTIF(events = 'home_run')                                        AS homeruns,
    COUNTIF(events = 'double')                                          AS doubles,
    COUNTIF(events = 'triple')                                          AS triples,
    COUNTIF(events = 'single')                                          AS singles,
    COUNTIF(events IN ('walk','intent_walk','hit_by_pitch'))            AS bb_hbp,
    COUNTIF(events = 'strikeout')                                       AS so,
    COUNTIF(events NOT IN (
      'walk','intent_walk','hit_by_pitch',
      'sac_fly','sac_bunt','catcher_interf'
    ))                                                                  AS ab,

    -- wOBA / xwOBA
    ROUND(SAFE_DIVIDE(
      SUM(woba_value), SUM(woba_denom)),                          3)   AS woba,
    ROUND(SAFE_DIVIDE(
      SUM(xwoba_value), SUM(woba_denom)),                         3)   AS xwoba,

    -- Statcast metrics
    COUNT(CASE WHEN launch_speed IS NOT NULL THEN 1 END)                AS hitting_events,
    ROUND(AVG(launch_angle),   1)                                       AS avg_launch_angle,
    ROUND(AVG(launch_speed),   1)                                       AS avg_exit_velocity,
    ROUND(AVG(bat_speed),      1)                                       AS avg_bat_speed,
    ROUND(AVG(swing_length),   2)                                       AS avg_swing_length,
    COUNTIF(is_hard_hit)                                                AS hard_hit_count,
    COUNTIF(launch_speed IS NOT NULL)                                   AS denominator_for_hard_hit_rate,
    COUNTIF(is_barrel)                                                  AS barrels_count,
    COUNTIF(launch_speed IS NOT NULL)                                   AS total_batted_balls,
    COUNTIF(description IN (
      'swinging_strike','swinging_strike_blocked','foul_tip'
    ))                                                                  AS swinging_strike_count,
    COUNT(*)                                                            AS total_pitches

  FROM statcast
  GROUP BY game_year, batter_name, batter_id, team, situation_type
)

SELECT
  game_year,
  batter_name,
  batter_id,
  team,
  situation_type,

  -- Volume
  pa,
  hits,
  homeruns,
  doubles,
  triples,
  singles,
  bb_hbp,
  so,
  ab,

  -- Rate stats
  ROUND(SAFE_DIVIDE(hits, ab),                                      3) AS avg,
  ROUND(SAFE_DIVIDE(hits + bb_hbp, ab + bb_hbp),                   3) AS obp,
  ROUND(SAFE_DIVIDE(
    singles + doubles*2 + triples*3 + homeruns*4, ab),              3) AS slg,
  ROUND(
    SAFE_DIVIDE(hits + bb_hbp, ab + bb_hbp)
    + SAFE_DIVIDE(singles + doubles*2 + triples*3 + homeruns*4, ab),
    3)                                                                  AS ops,
  woba,
  xwoba,
  ROUND(SAFE_DIVIDE(bb_hbp, pa),                                    3) AS bb_rate,

  -- Statcast
  hitting_events,
  avg_launch_angle,
  avg_exit_velocity,
  avg_bat_speed,
  avg_swing_length,
  hard_hit_count,
  denominator_for_hard_hit_rate,
  ROUND(SAFE_DIVIDE(hard_hit_count, denominator_for_hard_hit_rate), 3) AS hard_hit_rate,
  barrels_count,
  total_batted_balls,
  ROUND(SAFE_DIVIDE(barrels_count, total_batted_balls),             3) AS barrels_rate,
  ROUND(SAFE_DIVIDE(so, pa),                                        3) AS strikeout_rate,
  swinging_strike_count,
  ROUND(SAFE_DIVIDE(swinging_strike_count, total_pitches),          3) AS swinging_strike_rate

FROM aggregated
ORDER BY game_year DESC, batter_name, situation_type
