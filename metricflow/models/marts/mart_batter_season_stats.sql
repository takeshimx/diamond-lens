{{ config(
    materialized='table',
    alias='mart_batter_season_stats',
    description='Batter season aggregate stats with percentile ranks: AVG/OBP/SLG/OPS/wOBA/xwOBA/wRC+/HardHit%/Barrel%/SwStr%/RISP',
    tags=['batter_performance', 'season']
) }}

WITH pa_level AS (
  SELECT
    batter,
    game_year,
    game_pk,
    events,
    des,
    woba_value,
    woba_denom,
    estimated_woba_using_speedangle,
    launch_speed,
    launch_angle,
    on_2b,
    on_3b
  FROM {{ ref('statcast_master') }}
  WHERE
    events IS NOT NULL
    AND game_type = 'R'
),

pitch_level AS (
  SELECT
    batter,
    game_year,
    description
  FROM {{ ref('statcast_master') }}
  WHERE game_type = 'R'
),

batter_agg AS (
  SELECT
    batter,
    game_year,

    COUNT(DISTINCT game_pk)                                               AS g,
    COUNT(*)                                                              AS pa,

    COUNTIF(events NOT IN (
      'walk', 'intent_walk', 'hit_by_pitch',
      'sac_fly', 'sac_bunt', 'catcher_interf'
    ))                                                                    AS ab,

    COUNTIF(events IN ('single', 'double', 'triple', 'home_run'))         AS h,
    COUNTIF(events = 'home_run')                                          AS hr,
    COUNTIF(events IN ('walk', 'intent_walk'))                            AS bb,
    COUNTIF(events IN ('strikeout', 'strikeout_double_play'))             AS so,

    SUM(
      ARRAY_LENGTH(REGEXP_EXTRACT_ALL(des, r'scores\.'))
      + IF(REGEXP_CONTAINS(des, r'\bhomers\b'), 1, 0)
    )                                                                     AS rbi,

    ROUND(SAFE_DIVIDE(
      COUNTIF(events IN ('single', 'double', 'triple', 'home_run')),
      COUNTIF(events NOT IN (
        'walk', 'intent_walk', 'hit_by_pitch',
        'sac_fly', 'sac_bunt', 'catcher_interf'
      ))
    ), 3)                                                                 AS avg,

    ROUND(SAFE_DIVIDE(
      COUNTIF(events IN (
        'single', 'double', 'triple', 'home_run',
        'walk', 'intent_walk', 'hit_by_pitch'
      )),
      COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3)                                                                 AS obp,

    ROUND(SAFE_DIVIDE(
      COUNTIF(events = 'single')    * 1 +
      COUNTIF(events = 'double')    * 2 +
      COUNTIF(events = 'triple')    * 3 +
      COUNTIF(events = 'home_run')  * 4,
      COUNTIF(events NOT IN (
        'walk', 'intent_walk', 'hit_by_pitch',
        'sac_fly', 'sac_bunt', 'catcher_interf'
      ))
    ), 3)                                                                 AS slg,

    ROUND(SAFE_DIVIDE(
      SUM(woba_value),
      SUM(woba_denom)
    ), 3)                                                                 AS woba,

    ROUND(SAFE_DIVIDE(
      SUM(COALESCE(estimated_woba_using_speedangle, woba_value)),
      SUM(woba_denom)
    ), 3)                                                                 AS xwoba,

    ROUND(SAFE_DIVIDE(
      COUNTIF(launch_speed >= 95),
      COUNTIF(launch_speed IS NOT NULL)
    ), 3)                                                                 AS hardhitpct,

    ROUND(SAFE_DIVIDE(
      COUNTIF(
        launch_speed IS NOT NULL AND launch_speed >= 98
        AND (
          (launch_speed = 98  AND launch_angle BETWEEN 26 AND 30) OR
          (launch_speed = 99  AND launch_angle BETWEEN 25 AND 31) OR
          (launch_speed = 100 AND launch_angle BETWEEN 25 AND 31) OR
          (launch_speed = 101 AND launch_angle BETWEEN 24 AND 32) OR
          (launch_speed = 102 AND launch_angle BETWEEN 24 AND 33) OR
          (launch_speed = 103 AND launch_angle BETWEEN 23 AND 34) OR
          (launch_speed = 104 AND launch_angle BETWEEN 23 AND 34) OR
          (launch_speed = 105 AND launch_angle BETWEEN 22 AND 35) OR
          (launch_speed >= 106 AND launch_angle BETWEEN 5  AND 50)
        )
      ),
      COUNTIF(events NOT IN (
        'walk', 'intent_walk', 'hit_by_pitch',
        'strikeout', 'strikeout_double_play'
      ))
    ), 3)                                                                 AS barrelpct,

    ROUND(SAFE_DIVIDE(
      COUNTIF(
        (on_2b > 0 OR on_3b > 0)
        AND events IN ('single', 'double', 'triple', 'home_run')
      ),
      COUNTIF(
        (on_2b > 0 OR on_3b > 0)
        AND events NOT IN (
          'walk', 'intent_walk', 'hit_by_pitch',
          'sac_fly', 'sac_bunt', 'catcher_interf'
        )
      )
    ), 3)                                                                 AS risp_avg

  FROM pa_level
  GROUP BY batter, game_year
),

runs_raw AS (
  SELECT
    game_year,
    REGEXP_EXTRACT_ALL(des, r'(\S+)\s+scores\.') AS scorers
  FROM {{ ref('statcast_master') }}
  WHERE game_type = 'R'
    AND des IS NOT NULL
),

runs_unnested AS (
  SELECT game_year, scorer
  FROM runs_raw, UNNEST(scorers) AS scorer
),

runs_agg AS (
  SELECT
    dst.mlb_id                                                            AS batter,
    ru.game_year,
    COUNT(*)                                                              AS runner_runs
  FROM runs_unnested ru
  JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON ru.game_year = dst.season
   AND LOWER(ru.scorer) = LOWER(REGEXP_EXTRACT(dst.full_name, r'(\S+)$'))
  GROUP BY dst.mlb_id, ru.game_year
),

swstr_agg AS (
  SELECT
    batter,
    game_year,
    COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked')) AS swstr_count,
    COUNT(*)                                                               AS total_pitches
  FROM pitch_level
  GROUP BY batter, game_year
),

-- FanGraphs Guts! 定数（シーズン終了後に更新が必要）
fg_constants AS (
  SELECT * FROM UNNEST([
    STRUCT(2021 AS season, 1.176  AS woba_scale, 0.1142 AS lg_r_per_pa, 0.320 AS lg_woba),
    STRUCT(2022 AS season, 1.166  AS woba_scale, 0.1109 AS lg_r_per_pa, 0.308 AS lg_woba),
    STRUCT(2023 AS season, 1.157  AS woba_scale, 0.1125 AS lg_r_per_pa, 0.318 AS lg_woba),
    STRUCT(2024 AS season, 1.242  AS woba_scale, 0.1170 AS lg_r_per_pa, 0.310 AS lg_woba),
    STRUCT(2025 AS season, 1.232  AS woba_scale, 0.1182 AS lg_r_per_pa, 0.313 AS lg_woba),
    STRUCT(2026 AS season, 1.265  AS woba_scale, 0.1177 AS lg_r_per_pa, 0.320 AS lg_woba)
  ])
),

league_agg AS (
  SELECT
    game_year,
    ROUND(SAFE_DIVIDE(SUM(woba_value), SUM(woba_denom)), 4)              AS lg_woba_actual
  FROM pa_level
  GROUP BY game_year
),

combined AS (
  SELECT
    b.*,
    ROUND(b.obp + b.slg, 3)                                              AS ops,
    ROUND(SAFE_DIVIDE(sw.swstr_count, sw.total_pitches), 3)              AS swstrpct,
    COALESCE(rn.runner_runs, 0) + b.hr                                   AS runs,

    ROUND(
      SAFE_DIVIDE(
        (b.woba - COALESCE(lg.lg_woba_actual, fc.lg_woba)) / fc.woba_scale
          + fc.lg_r_per_pa * (2 - COALESCE(pf.pf_1yr, 100) / 100.0),
        fc.lg_r_per_pa
      ) * 100,
      1
    )                                                                     AS wrc_plus

  FROM batter_agg b
  LEFT JOIN swstr_agg sw USING (batter, game_year)
  LEFT JOIN runs_agg rn USING (batter, game_year)
  LEFT JOIN league_agg lg USING (game_year)
  LEFT JOIN fg_constants fc ON b.game_year = fc.season
  LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst_pf
    ON b.batter = dst_pf.mlb_id AND b.game_year = dst_pf.season
  LEFT JOIN {{ source('mlb_raw_data', 'dim_park_factors') }} pf
    ON dst_pf.team_abbr = pf.team AND b.game_year = pf.season
),

with_ranks AS (
  SELECT
    *,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY avg)           AS avg_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY obp)           AS obp_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY slg)           AS slg_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY ops)           AS ops_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY hr)            AS hr_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY rbi)           AS rbi_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY bb)            AS bb_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY so DESC)       AS so_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY woba)          AS woba_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY hardhitpct)    AS hardhitpct_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY barrelpct)     AS barrelpct_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY swstrpct DESC) AS swstrpct_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY runs)          AS runs_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY risp_avg)      AS risp_avg_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY wrc_plus)      AS wrc_plus_rank
  FROM combined
  WHERE pa >= 10
)

SELECT
  r.batter,
  dst.full_name                                                          AS player_name,
  dst.team_abbr                                                          AS team,
  r.game_year                                                            AS season,
  r.g,
  r.pa,
  r.ab,
  r.h,
  r.hr,
  r.rbi,
  r.runs,       r.runs_rank,
  r.bb,
  r.so,
  r.avg,        r.avg_rank,
  r.risp_avg,   r.risp_avg_rank,
  r.obp,        r.obp_rank,
  r.slg,        r.slg_rank,
  r.ops,        r.ops_rank,
  r.woba,       r.woba_rank,
  r.xwoba,
  r.hr_rank,
  r.rbi_rank,
  r.bb_rank,
  r.so_rank,
  r.hardhitpct, r.hardhitpct_rank,
  r.barrelpct,  r.barrelpct_rank,
  r.swstrpct,   r.swstrpct_rank,
  r.wrc_plus,   r.wrc_plus_rank

FROM with_ranks r
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
  ON r.batter    = dst.mlb_id
 AND r.game_year = dst.season

ORDER BY r.game_year DESC, r.woba DESC
