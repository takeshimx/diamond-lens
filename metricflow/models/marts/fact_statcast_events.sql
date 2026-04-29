-- dbt model for combining Statcast data from 2021 to 2025 with player names
{{ config(
    materialized='view',
    alias='fact_statcast_events',
)}}
SELECT
  src.pitch_type,
  src.game_date,
  src.player_name AS pitcher_name,
  src.batter AS batter_id,
  src.pitcher AS pitcher_id,
  dim.full_name AS batter_name,
  src.events,
  src.game_type,
  src.hit_location,
  src.balls,
  src.strikes,
  src.game_year,
  src.release_speed,
  src.release_pos_x,
  src.release_pos_z,
  src.pfx_x,
  src.pfx_z,
  src.plate_x,
  src.plate_z,
  src.description,
  src.type,
  src.inning,
  src.zone,
  COALESCE(src.on_1b, 0) AS on_1b,
  COALESCE(src.on_2b, 0) AS on_2b,
  COALESCE(src.on_3b, 0) AS on_3b,
  src.hit_distance_sc,
  src.launch_speed,
  src.launch_angle,
  src.woba_value,
  src.launch_speed_angle,
  src.pitch_number,
  src.at_bat_number,
  src.delta_home_win_exp,
  src.delta_run_exp,
  src.bat_speed,
  src.game_pk,
  src.swing_length,
  src.pitch_name,
  src.p_throws,
  src.home_score,
  src.away_score,
  src.des,
  src.stand
FROM
  {{ ref('statcast_master') }} AS src
LEFT JOIN
  {{ source('mlb_raw_data', 'dim_players_latest') }} AS dim
ON
  src.batter = dim.mlbid
WHERE src.game_type = 'R'