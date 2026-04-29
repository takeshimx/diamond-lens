{{ config(
    materialized='table',
    alias='mart_pitcher_tto_velo_spin',
    description='Pitcher performance and fastball quality metrics by times through the order (TTO)',
    tags=['pitcher_performance']
) }}

WITH pa_agg AS (
  SELECT
    s.pitcher,
    s.game_year                          AS season,
    LEAST(s.n_thruorder_pitcher, 3)      AS tto,
    COUNT(*)                             AS pa,
    SUM(CASE WHEN s.events IN ('single','double','triple','home_run') THEN 1 ELSE 0 END) AS hits,
    ROUND(
      SAFE_DIVIDE(
        SUM(CASE WHEN s.events IN ('single','double','triple','home_run') THEN 1 ELSE 0 END),
        NULLIF(SUM(s.woba_denom), 0)
      ), 3
    )                                    AS baa,
    ROUND(AVG(
      CASE WHEN s.woba_denom = 1 THEN s.estimated_woba_using_speedangle END
    ), 3)                                AS xwoba_against
  FROM {{ ref('statcast_master') }} s
  WHERE
    s.events IS NOT NULL
    AND s.game_type            = 'R'
    AND s.n_thruorder_pitcher IS NOT NULL
    AND s.n_thruorder_pitcher  > 0
  GROUP BY s.pitcher, s.game_year, tto
),

fb_agg AS (
  SELECT
    s.pitcher,
    s.game_year                          AS season,
    LEAST(s.n_thruorder_pitcher, 3)      AS tto,
    COUNT(*)                             AS pitch_count,
    ROUND(AVG(s.release_speed),     1)   AS avg_velo,
    ROUND(AVG(s.release_spin_rate), 0)   AS avg_spin
  FROM {{ ref('statcast_master') }} s
  WHERE
    s.pitch_type IN ('FF', 'SI', 'FC', 'FS', 'FA', 'FT')
    AND s.release_speed       IS NOT NULL
    AND s.release_spin_rate   IS NOT NULL
    AND s.game_type            = 'R'
    AND s.n_thruorder_pitcher IS NOT NULL
    AND s.n_thruorder_pitcher  > 0
  GROUP BY s.pitcher, s.game_year, tto
)

SELECT
  pa.pitcher,
  dst.full_name  AS pitcher_name,
  dst.team_abbr  AS team,
  pa.season,
  pa.tto,
  pa.pa,
  pa.hits,
  pa.baa,
  pa.xwoba_against,
  fb.pitch_count,
  fb.avg_velo,
  fb.avg_spin
FROM pa_agg pa
LEFT JOIN fb_agg fb
  ON pa.pitcher = fb.pitcher AND pa.season = fb.season AND pa.tto = fb.tto
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
  ON pa.pitcher = dst.mlb_id AND pa.season = dst.season
WHERE dst.full_name IS NOT NULL
