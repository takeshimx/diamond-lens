{{ config(
    materialized='table',
    alias='mart_batter_pitch_type',
    description='Batter stats broken down by pitch type: AVG/OBP/SLG/OPS/HardHit/Barrel/SwStr per pitch type',
    tags=['batter_performance', 'pitch_type']
) }}

SELECT
  s.game_year,
  s.batter                                                                AS batter_id,
  dst.full_name                                                           AS batter_name,
  dst.team_abbr                                                           AS team,
  s.pitch_name,

  COUNTIF(s.events IN ('single', 'double', 'triple', 'home_run'))         AS hits_by_pitch_type,
  COUNTIF(s.events = 'home_run')                                          AS homeruns_by_pitch_type,
  COUNTIF(s.events = 'double')                                            AS doubles_by_pitch_type,
  COUNTIF(s.events = 'triple')                                            AS triples_by_pitch_type,
  COUNTIF(s.events = 'single')                                            AS singles_by_pitch_type,
  COUNTIF(s.events IN ('hit_by_pitch', 'walk', 'intent_walk'))            AS bb_hbp_by_pitch_type,
  COUNTIF(s.events = 'strikeout')                                         AS so_by_pitch_type,
  COUNTIF(s.events NOT IN (
    'hit_by_pitch', 'walk', 'intent_walk',
    'sac_fly', 'sac_bunt', 'catcher_interf'
  ))                                                                      AS ab_by_pitch_type,

  {{ calculate_batting_avg(suffix='_by_pitch_type') }},
  {{ calculate_obp(suffix='_by_pitch_type') }},
  {{ calculate_slg(suffix='_by_pitch_type') }},
  {{ calculate_ops(suffix='_by_pitch_type') }},

  COUNTIF(s.events NOT IN (
    'hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt',
    'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'
  ))                                                                      AS hitting_events_by_pitch_type,

  {{ avg_batted_ball_metric('launch_angle', 'launch_angle_by_pitch_type') }},
  {{ avg_batted_ball_metric('launch_speed', 'exit_velocity_by_pitch_type') }},
  {{ avg_batted_ball_metric('bat_speed',    'bat_speed_by_pitch_type') }},
  {{ avg_batted_ball_metric('swing_length', 'swing_length_by_pitch_type') }},

  COUNTIF(s.launch_speed IS NOT NULL AND s.launch_speed >= 95)            AS hard_hit_count_by_pitch_type,
  COUNTIF(s.events NOT IN (
    'hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout'
  ))                                                                      AS denominator_for_hard_hit_rate_by_pitch_type,
  {{ calculate_hard_hit_rate(suffix='_by_pitch_type') }},

  {{ calculate_barrels(suffix='_by_pitch_type') }},
  COUNTIF(s.events NOT IN (
    'hit_by_pitch', 'walk', 'intent_walk',
    'strikeout', 'strikeout_double_play', 'truncated_pa'
  ))                                                                      AS total_batted_balls_by_pitch_type,
  {{ calculate_barrel_rate(suffix='_by_pitch_type') }},

  ROUND(SAFE_DIVIDE(
    COUNTIF(s.events = 'strikeout'),
    COUNTIF(s.events NOT IN (
      'hit_by_pitch', 'walk', 'intent_walk',
      'sac_fly', 'sac_bunt', 'catcher_interf'
    ))
  ), 3)                                                                   AS strikeout_rate_by_pitch_type,

  COUNTIF(s.description IN ('swinging_strike', 'swinging_strike_blocked')) AS swinging_strike_count_by_pitch_type,
  ROUND(SAFE_DIVIDE(
    COUNTIF(s.description IN ('swinging_strike', 'swinging_strike_blocked')),
    COUNTIF(s.events NOT IN (
      'hit_by_pitch', 'walk', 'intent_walk',
      'sac_fly', 'sac_bunt', 'catcher_interf'
    ))
  ), 3)                                                                   AS swinging_strike_rate_by_pitch_type

FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
  ON s.batter = dst.mlb_id AND s.game_year = dst.season
WHERE
  s.events IS NOT NULL
  AND s.game_type = 'R'
  AND s.pitch_name IS NOT NULL
GROUP BY
  s.game_year, s.batter, batter_name, team, s.pitch_name
ORDER BY
  s.game_year ASC,
  batter_name ASC,
  s.pitch_name ASC
