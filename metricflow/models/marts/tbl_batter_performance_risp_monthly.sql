-- dbt model
{{ config(
    materialized='table',
    description='Batter performance statistics at RISP (Runners In Scoring Position) by month',
    tags=['batter_performance', 'risp', 'monthly'],
    alias='tbl_batter_performance_risp_monthly',
    enabled=True
)}}
SELECT
    game_year,
    EXTRACT(MONTH FROM game_date) AS game_month,
    batter_name,
    batter_id,
    -- Number of hits at RISP
    COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS hits_at_risp,
    
    -- Number of each type of hit at RISP
    COUNTIF(events = 'home_run') AS home_runs_at_risp,
    COUNTIF(events = 'double') AS doubles_at_risp,
    COUNTIF(events = 'triple') AS triples_at_risp,
    COUNTIF(events = 'single') AS singles_at_risp,
    
    -- Number of at bats at RISP
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS at_bats_at_risp,
    
    -- BA at RISP
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits at RISP
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf') -- total at bats at RISP
    )), 3
    ) AS batting_average_at_risp,

    -- SLG at RISP
    ROUND(SAFE_DIVIDE(
        (COUNTIF(events = 'single') * 1) + 
        (COUNTIF(events = 'double') * 2) + 
        (COUNTIF(events = 'triple') * 3) + 
        (COUNTIF(events = 'home_run') * 4), -- total bases at RISP
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- total at bats at RISP
    ), 3) AS slugging_percentage_at_risp
FROM
    {{ ref('int_statcast_risp_events') }}
GROUP BY game_year, EXTRACT(MONTH FROM game_date), batter_name, batter_id
ORDER BY game_year ASC, EXTRACT(MONTH FROM game_date) ASC, batter_name ASC