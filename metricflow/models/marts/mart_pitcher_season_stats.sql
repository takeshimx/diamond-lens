{{ config(
    materialized='table',
    alias='mart_pitcher_season_stats',
    description='Pitcher season aggregate stats with percentile ranks: ERA/FIP/WHIP/K9/BB9/SwStr%/HardHit%/Barrel%',
    tags=['pitcher_performance', 'season']
) }}

WITH pa_level AS (
  SELECT
    s.pitcher,
    s.game_pk,
    s.game_year,
    s.batter,
    s.inning,
    s.inning_topbot,
    s.at_bat_number,
    s.on_1b, s.on_2b, s.on_3b,
    s.events,
    s.des,
    s.woba_value,
    s.woba_denom,
    s.estimated_woba_using_speedangle,
    s.launch_speed,
    s.launch_angle,

    CASE
      WHEN s.events = 'field_error'             THEN TRUE
      WHEN LOWER(s.des) LIKE '%throwing error%' THEN TRUE
      WHEN LOWER(s.des) LIKE '%fielding error%' THEN TRUE
      ELSE FALSE
    END AS is_error_pa,

    CASE
      WHEN s.events IN (
        'strikeout', 'field_out', 'force_out',
        'sac_fly', 'sac_bunt', 'fielders_choice_out', 'fielders_choice'
      ) THEN 1
      WHEN s.events IN (
        'grounded_into_double_play', 'double_play',
        'strikeout_double_play', 'sac_fly_double_play', 'sac_bunt_double_play'
      ) THEN 2
      WHEN s.events = 'triple_play' THEN 3
      ELSE 0
    END AS outs_this_pa,

    (s.post_bat_score - s.bat_score) AS runs_this_pa

  FROM {{ ref('statcast_master') }} s
  WHERE
    s.events IS NOT NULL
    AND s.game_type = 'R'
),

error_runner_ids AS (
  SELECT DISTINCT
    game_pk, inning, inning_topbot,
    batter AS error_runner_id
  FROM pa_level
  WHERE is_error_pa = TRUE
),

pa_with_error_context AS (
  SELECT
    p.*,
    (
      CASE WHEN e1.error_runner_id IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN e2.error_runner_id IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN e3.error_runner_id IS NOT NULL THEN 1 ELSE 0 END
    ) AS error_runners_on_base
  FROM pa_level p
  LEFT JOIN error_runner_ids e1
    ON p.game_pk = e1.game_pk AND p.inning = e1.inning
    AND p.inning_topbot = e1.inning_topbot AND p.on_1b = e1.error_runner_id
  LEFT JOIN error_runner_ids e2
    ON p.game_pk = e2.game_pk AND p.inning = e2.inning
    AND p.inning_topbot = e2.inning_topbot AND p.on_2b = e2.error_runner_id
  LEFT JOIN error_runner_ids e3
    ON p.game_pk = e3.game_pk AND p.inning = e3.inning
    AND p.inning_topbot = e3.inning_topbot AND p.on_3b = e3.error_runner_id
),

pa_with_runs AS (
  SELECT
    *,
    CASE
      WHEN is_error_pa AND runs_this_pa > 0 THEN runs_this_pa
      ELSE LEAST(runs_this_pa, error_runners_on_base)
    END AS unearned_runs,
    GREATEST(0,
      runs_this_pa - CASE
        WHEN is_error_pa AND runs_this_pa > 0 THEN runs_this_pa
        ELSE LEAST(runs_this_pa, error_runners_on_base)
      END
    ) AS earned_runs
  FROM pa_with_error_context
),

pitch_level AS (
  SELECT
    pitcher,
    game_year,
    description
  FROM {{ ref('statcast_master') }}
  WHERE game_type = 'R'
),

pitcher_agg AS (
  SELECT
    pitcher,
    game_year,

    COUNT(DISTINCT game_pk)                                                AS g,
    COUNT(DISTINCT CASE WHEN inning = 1 THEN game_pk END)                  AS gs,
    COUNT(*)                                                               AS bf,
    SUM(outs_this_pa)                                                      AS total_outs,
    SUM(earned_runs)                                                       AS total_earned_runs,

    COUNTIF(events IN ('single', 'double', 'triple', 'home_run'))          AS h,
    COUNTIF(events = 'home_run')                                           AS hr,
    COUNTIF(events IN ('walk', 'intent_walk'))                             AS bb,
    COUNTIF(events = 'hit_by_pitch')                                       AS hbp,
    COUNTIF(events IN ('strikeout', 'strikeout_double_play'))              AS so,

    ROUND(SAFE_DIVIDE(
      SUM(COALESCE(estimated_woba_using_speedangle, woba_value)),
      SUM(woba_denom)
    ), 3)                                                                   AS xwoba_against,

    ROUND(SAFE_DIVIDE(
      COUNTIF(launch_speed >= 95),
      COUNTIF(launch_speed IS NOT NULL)
    ), 3)                                                                   AS hardhitpct,

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
    ), 3)                                                                   AS barrelpct

  FROM pa_with_runs
  GROUP BY pitcher, game_year
),

pitch_agg AS (
  SELECT
    pitcher,
    game_year,
    COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked'))  AS swstr_count,
    COUNT(*)                                                                 AS total_pitches
  FROM pitch_level
  GROUP BY pitcher, game_year
),

combined AS (
  SELECT
    p.*,

    ROUND(p.total_outs / 3.0, 1)                                           AS ip,

    CASE WHEN p.total_outs = 0 THEN NULL
      ELSE ROUND(p.total_earned_runs / (p.total_outs / 3.0) * 9, 2)
    END                                                                    AS era,

    -- FIP: IP < 10 (30 outs) は小サンプルのため NULL
    CASE WHEN p.total_outs < 30 THEN NULL
      ELSE ROUND(
        (13 * p.hr + 3 * (p.bb + p.hbp) - 2 * p.so)
        / (p.total_outs / 3.0)
        + 3.10,
        2)
    END                                                                    AS fip,

    ROUND(SAFE_DIVIDE(p.bb + p.h, p.total_outs / 3.0), 2)                 AS whip,
    ROUND(SAFE_DIVIDE(p.so * 9.0, p.total_outs / 3.0), 2)                 AS k_9,
    ROUND(SAFE_DIVIDE(p.bb * 9.0, p.total_outs / 3.0), 2)                 AS bb_9,
    ROUND(SAFE_DIVIDE(p.so, p.bf), 3)                                      AS kpct,
    ROUND(SAFE_DIVIDE(p.bb, p.bf), 3)                                      AS bbpct,
    ROUND(SAFE_DIVIDE(p.so - p.bb, p.bf), 3)                              AS k_minus_bbpct,
    ROUND(SAFE_DIVIDE(pa.swstr_count, pa.total_pitches), 3)                AS swstrpct

  FROM pitcher_agg p
  LEFT JOIN pitch_agg pa USING (pitcher, game_year)
),

with_ranks AS (
  SELECT
    *,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY era        ASC)   AS era_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY whip       ASC)   AS whip_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY fip        ASC)   AS fip_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY k_9        DESC)  AS k_9_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY bb_9       ASC)   AS bb_9_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY so         DESC)  AS so_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY hardhitpct ASC)   AS hardhitpct_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY barrelpct  ASC)   AS barrelpct_rank,
    PERCENT_RANK() OVER (PARTITION BY game_year ORDER BY swstrpct   DESC)  AS swstrpct_rank
  FROM combined
  WHERE bf >= 10
)

SELECT
  r.pitcher,
  dst.full_name                                                            AS player_name,
  dst.team_abbr                                                            AS team,
  r.game_year                                                              AS season,
  r.g,
  r.gs,
  r.bf,
  r.ip,
  r.so,
  r.bb,
  r.hbp,
  r.hr,
  r.h,
  r.era,          r.era_rank,
  r.fip,          r.fip_rank,
  r.whip,         r.whip_rank,
  r.k_9,          r.k_9_rank,
  r.bb_9,         r.bb_9_rank,
  r.so_rank,
  r.xwoba_against,
  r.hardhitpct,   r.hardhitpct_rank,
  r.barrelpct,    r.barrelpct_rank,
  r.swstrpct,     r.swstrpct_rank

FROM with_ranks r
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
  ON r.pitcher   = dst.mlb_id
 AND r.game_year = dst.season

ORDER BY r.game_year DESC, r.era ASC
