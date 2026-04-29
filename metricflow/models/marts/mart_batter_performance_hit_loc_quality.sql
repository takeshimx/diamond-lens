{{ config(
    materialized='table',
    alias='mart_batter_performance_hit_loc_quality',
    description='Batter hit location and quality metrics including pull/center/oppo rates by pitch hand',
    tags=['batter_performance']
) }}

WITH base AS (
    SELECT
        s.batter,
        dst.full_name   AS player_name,
        dst.team_abbr   AS team,
        s.game_year,
        s.stand,
        s.p_throws,
        CASE
            WHEN s.hc_x < 100  THEN 'Left'
            WHEN s.hc_x <= 155 THEN 'Center'
            ELSE                    'Right'
        END                                         AS hit_direction,
        s.bb_type,
        COUNT(*)                                    AS hit_count,
        ROUND(AVG(s.launch_speed),              1)  AS avg_exit_velocity,
        ROUND(AVG(s.estimated_ba_using_speedangle), 3) AS avg_xba
    FROM {{ ref('statcast_master') }} s
    LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
        ON s.batter = dst.mlb_id AND s.game_year = dst.season
    WHERE s.bb_type   IS NOT NULL
      AND s.hc_x      IS NOT NULL
      AND s.game_type = 'R'
    GROUP BY
        s.batter, player_name, team,
        s.game_year, s.stand, s.p_throws,
        hit_direction, s.bb_type
)

SELECT
    b.*,

    -- 全BIP合計（p_throws単位）
    SUM(hit_count) OVER (PARTITION BY batter, game_year, p_throws)
        AS total_bip,

    -- bb_type の方向内構成比（積み上げ棒グラフ用）
    SAFE_DIVIDE(
        hit_count,
        SUM(hit_count) OVER (PARTITION BY batter, game_year, p_throws, hit_direction)
    )   AS type_pct_in_dir,

    -- Pull% / Center% / Oppo%（stand考慮）
    SAFE_DIVIDE(
        SUM(CASE
            WHEN (stand = 'R' AND hit_direction = 'Left')
              OR (stand = 'L' AND hit_direction = 'Right')
            THEN hit_count ELSE 0
        END) OVER (PARTITION BY batter, game_year, p_throws),
        SUM(hit_count) OVER (PARTITION BY batter, game_year, p_throws)
    )   AS pull_pct,

    SAFE_DIVIDE(
        SUM(CASE WHEN hit_direction = 'Center' THEN hit_count ELSE 0 END)
            OVER (PARTITION BY batter, game_year, p_throws),
        SUM(hit_count) OVER (PARTITION BY batter, game_year, p_throws)
    )   AS center_pct,

    SAFE_DIVIDE(
        SUM(CASE
            WHEN (stand = 'R' AND hit_direction = 'Right')
              OR (stand = 'L' AND hit_direction = 'Left')
            THEN hit_count ELSE 0
        END) OVER (PARTITION BY batter, game_year, p_throws),
        SUM(hit_count) OVER (PARTITION BY batter, game_year, p_throws)
    )   AS oppo_pct

FROM base b
ORDER BY batter, game_year, p_throws, hit_direction, bb_type
