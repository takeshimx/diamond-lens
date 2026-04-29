{{ config(
    materialized='view',
    description='Pitcher PA-level data with earned/unearned run classification'
) }}

WITH pa_level AS (
  SELECT
    s.game_pk,
    s.game_year,
    s.pitcher,
    dst.full_name   AS pitcher_name,
    dst.team_abbr   AS pitcher_team,
    s.batter,
    s.stand,
    s.inning,
    s.inning_topbot,
    s.at_bat_number,
    s.outs_when_up,
    s.on_1b, s.on_2b, s.on_3b,
    s.bat_score,
    s.post_bat_score,
    (s.post_bat_score - s.bat_score) AS runs_this_pa,
    s.events,
    s.des,

    CASE
      WHEN s.events = 'field_error'                    THEN TRUE
      WHEN LOWER(s.des) LIKE '%throwing error%'        THEN TRUE
      WHEN LOWER(s.des) LIKE '%fielding error%'        THEN TRUE
      ELSE FALSE
    END AS is_error_pa,

    CASE
      WHEN s.events IN (
        'strikeout', 'field_out', 'force_out',
        'sac_fly', 'sac_bunt', 'fielders_choice_out',
        'other_out',
        'caught_stealing_2b', 'caught_stealing_3b', 'caught_stealing_home',
        'pickoff_1b', 'pickoff_2b', 'pickoff_3b',
        'pickoff_caught_stealing_2b', 'pickoff_caught_stealing_3b'
      ) THEN 1
      WHEN s.events IN (
        'grounded_into_double_play', 'double_play',
        'strikeout_double_play', 'sac_fly_double_play', 'sac_bunt_double_play'
      ) THEN 2
      WHEN s.events = 'triple_play' THEN 3
      ELSE 0
    END AS outs_this_pa

  FROM {{ ref('statcast_master') }} s
  LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.pitcher = dst.mlb_id
   AND s.game_year = dst.season

  WHERE s.events IS NOT NULL
),

error_runner_ids AS (
  SELECT DISTINCT game_pk, inning, inning_topbot, batter AS error_runner_id
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
)

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
