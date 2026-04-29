-- dbt model
{{ config(
    materialized='table',
    descrption='This table contains batting statistics for players with runners in scoring position (RISP) aggregated by season.',
    tags=['batting_stats', 'risp'],
    alias='fact_batting_stats_with_risp',
    enabled=True
)}}
WITH season_risp AS (
    SELECT
        game_year,
        batter_name,
        batter_id,
        SUM(hits_at_risp) AS hits_at_risp,
        SUM(singles_at_risp) AS singles_at_risp,
        SUM(doubles_at_risp) AS doubles_at_risp,
        SUM(triples_at_risp) AS triples_at_risp,
        SUM(home_runs_at_risp) AS home_runs_at_risp,
        SUM(at_bats_at_risp) AS at_bats_at_risp,
        ROUND(SAFE_DIVIDE(
            SUM(hits_at_risp),
            SUM(at_bats_at_risp)
        ), 3) AS batting_average_at_risp,
        ROUND(SAFE_DIVIDE(
            (SUM(singles_at_risp) * 1) + 
            (SUM(doubles_at_risp) * 2) + 
            (SUM(triples_at_risp) * 3) + 
            (SUM(home_runs_at_risp) * 4),
            SUM(at_bats_at_risp)
        ), 3) AS slugging_percentage_at_risp
    FROM 
        {{ ref('tbl_batter_performance_risp_monthly') }}
    GROUP BY game_year, batter_name, batter_id
)
SELECT
    a.*,
    b.* EXCEPT(mlb_id, fangraphs_id, team, league),
    c.game_year,
    c.batter_id AS mlbId,
    c.hits_at_risp,
    c.singles_at_risp,
    c.doubles_at_risp,
    c.triples_at_risp,
    c.home_runs_at_risp,
    c.at_bats_at_risp,
    c.batting_average_at_risp,
    c.slugging_percentage_at_risp
FROM {{ ref('fact_batting_stats_master') }} a
LEFT JOIN {{ source('mlb_raw_data', 'dim_players') }} b ON a.idfg = b.fangraphs_id
LEFT JOIN season_risp c ON b.mlb_id = c.batter_id AND a.season = c.game_year
WHERE b.fangraphs_id IS NOT NULL
ORDER BY c.game_year ASC