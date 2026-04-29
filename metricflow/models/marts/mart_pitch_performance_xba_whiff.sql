{{ config(
    materialized='table',
    alias='mart_pitch_performance_xba_whiff',
    description='Pitcher pitch performance metrics including xBA and whiff rate by pitch type',
    tags=['pitcher_performance']
) }}

SELECT
    s.pitcher,
    dst.full_name                                               AS player_name,
    dst.team_abbr                                               AS team,
    s.game_year,
    s.pitch_type,
    ANY_VALUE(s.pitch_name)                                     AS pitch_name,

    -- 投球数・使用率
    COUNT(*)                                                    AS pitch_count,
    SAFE_DIVIDE(
        COUNT(*),
        SUM(COUNT(*)) OVER (PARTITION BY s.pitcher, s.game_year)
    )                                                           AS usage_pct,

    -- Whiff% = 空振り / スイング数
    SAFE_DIVIDE(
        COUNTIF(s.description IN ('swinging_strike', 'swinging_strike_blocked')),
        COUNTIF(s.description IN (
            'swinging_strike', 'swinging_strike_blocked',
            'foul', 'foul_bunt', 'foul_tip',
            'hit_into_play', 'hit_into_play_no_out', 'hit_into_play_score',
            'missed_bunt'
        ))
    )                                                           AS whiff_pct,

    -- xBA = インプレー時の期待打率平均
    AVG(
        CASE WHEN s.estimated_ba_using_speedangle IS NOT NULL
             THEN s.estimated_ba_using_speedangle END
    )                                                           AS xba,

    -- 参考指標
    AVG(s.release_speed)                                        AS avg_speed,
    AVG(s.release_spin_rate)                                    AS avg_spin_rate

FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.pitcher = dst.mlb_id AND s.game_year = dst.season
WHERE s.pitch_type IS NOT NULL
  AND s.game_type  = 'R'
GROUP BY s.pitcher, player_name, team, s.game_year, s.pitch_type
HAVING pitch_count >= 30
