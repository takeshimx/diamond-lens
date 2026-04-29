{{ config(
    materialized='table',
    alias='mart_pitch_performance_whiff_heatmap',
    description='Pitcher whiff rate heatmap by pitch type, zone location, and batter stand',
    tags=['pitcher_performance']
) }}

SELECT
    s.pitcher,
    dst.full_name   AS player_name,
    dst.team_abbr   AS team,
    s.game_year,
    s.pitch_type,
    ANY_VALUE(s.pitch_name)  AS pitch_name,
    s.stand,

    ROUND(s.plate_x / 0.5) * 0.5  AS zone_x,
    ROUND(s.plate_z / 0.5) * 0.5  AS zone_z,

    COUNT(*)                                                          AS total_pitches,

    COUNTIF(s.description IN ('swinging_strike','swinging_strike_blocked'))
                                                                      AS whiff_count,

    COUNTIF(s.description IN (
        'swinging_strike','swinging_strike_blocked',
        'foul','foul_bunt','foul_tip',
        'hit_into_play','hit_into_play_no_out','hit_into_play_score',
        'missed_bunt'
    ))                                                                AS swing_count,

    SAFE_DIVIDE(
        COUNTIF(s.description IN ('swinging_strike','swinging_strike_blocked')),
        COUNTIF(s.description IN (
            'swinging_strike','swinging_strike_blocked',
            'foul','foul_bunt','foul_tip',
            'hit_into_play','hit_into_play_no_out','hit_into_play_score',
            'missed_bunt'
        ))
    )                                                                 AS whiff_pct

FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.pitcher = dst.mlb_id AND s.game_year = dst.season

WHERE s.pitcher    IS NOT NULL
  AND s.plate_x    IS NOT NULL
  AND s.plate_z    IS NOT NULL
  AND s.pitch_type IS NOT NULL
  AND s.game_type  = 'R'

GROUP BY s.pitcher, player_name, team, s.game_year, s.pitch_type, s.stand, zone_x, zone_z
HAVING swing_count >= 3
