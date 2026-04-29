{{ config(
    materialized='table',
    alias='mart_batter_count_state_woba',
    description='Batter wOBA and xwOBA by count state (balls/strikes) and RISP situation',
    tags=['batter_performance']
) }}

SELECT
    s.batter,
    dst.full_name                   AS player_name,
    dst.team_abbr                   AS team,
    s.game_year,
    s.balls,
    s.strikes,
    (COALESCE(s.on_2b, 0) > 0 OR COALESCE(s.on_3b, 0) > 0) AS is_risp,
    COUNT(*)                        AS pa_count,
    ROUND(
        SAFE_DIVIDE(SUM(s.woba_value), SUM(s.woba_denom)), 3
    )                               AS woba,
    ROUND(
        AVG(CASE WHEN s.estimated_woba_using_speedangle IS NOT NULL
                 THEN s.estimated_woba_using_speedangle END), 3
    )                               AS xwoba_contact
FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.batter = dst.mlb_id AND s.game_year = dst.season
WHERE
    s.woba_denom  = 1
    AND s.balls   BETWEEN 0 AND 3
    AND s.strikes BETWEEN 0 AND 2
    AND s.game_type = 'R'
GROUP BY
    s.batter, player_name, team, s.game_year, s.balls, s.strikes, is_risp
