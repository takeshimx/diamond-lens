{{ config(
    materialized='table',
    alias='mart_batter_xwoba_zone',
    description='Batter wOBA and xwOBA by strike zone location, pitch hand, and RISP situation',
    tags=['batter_performance']
) }}

SELECT
    s.batter,
    dst.full_name                           AS player_name,
    dst.team_abbr                           AS team,
    s.game_year,
    s.p_throws,
    s.stand,
    ROUND(s.plate_x / 0.5) * 0.5           AS zone_x,
    ROUND(s.plate_z / 0.5) * 0.5           AS zone_z,
    (COALESCE(s.on_2b, 0) > 0 OR COALESCE(s.on_3b, 0) > 0) AS is_risp,
    COUNT(*)                                AS pa_count,
    ROUND(
        SAFE_DIVIDE(SUM(s.woba_value), SUM(s.woba_denom)), 3
    )                                       AS woba,
    ROUND(
        AVG(CASE WHEN s.estimated_woba_using_speedangle IS NOT NULL
                 THEN s.estimated_woba_using_speedangle END), 3
    )                                       AS xwoba_contact,
    COUNT(CASE WHEN s.estimated_woba_using_speedangle IS NOT NULL
               THEN 1 END)                  AS contact_count
FROM {{ ref('statcast_master') }} s
LEFT JOIN {{ source('mlb_raw_data', 'dim_player_season_teams') }} dst
    ON s.batter = dst.mlb_id AND s.game_year = dst.season
WHERE
    s.woba_denom  = 1
    AND s.plate_x IS NOT NULL
    AND s.plate_z IS NOT NULL
    AND s.game_type = 'R'
GROUP BY
    s.batter, player_name, team, s.game_year,
    s.p_throws, s.stand, zone_x, zone_z, is_risp
HAVING pa_count >= 3
