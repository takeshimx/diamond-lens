-- dbt model
{{ config(
    materialized='table',
    description='Monthly batter offensive statistics including hits, home runs, doubles, triples, batting average, on-base percentage, slugging percentage, and OPS.',
    alias='tbl_batter_offensive_stats_monthly',
    tags=['batter_performance', 'monthly'],
    enabled=True
) }}
SELECT
    game_year,
    EXTRACT(MONTH FROM game_date) AS game_month,
    batter_name,
    batter_id,
    COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS hits,
    COUNTIF(events = 'home_run') AS home_runs,
    COUNTIF(events = 'double') AS doubles,
    COUNTIF(events = 'triple') AS triples,
    COUNTIF(events = 'single') AS singles,
    -- Walks and HBP
    COUNTIF(events IN ('walk', 'hit_by_pitch', 'intent_walk')) AS walks_and_hbp,
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS at_bats,
    
    -- BA
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS batting_average,

    -- OBP
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
        COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS on_base_percentage,

    -- SLG
    ROUND(SAFE_DIVIDE(
        (COUNTIF(events = 'single') * 1) +
        (COUNTIF(events = 'double') * 2) +
        (COUNTIF(events = 'triple') * 3) +
        (COUNTIF(events = 'home_run') * 4),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS slugging_percentage,

    -- OPS
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
        COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) +
    ROUND(SAFE_DIVIDE(
        (COUNTIF(events = 'single') * 1) +
        (COUNTIF(events = 'double') * 2) +
        (COUNTIF(events = 'triple') * 3) +
        (COUNTIF(events = 'home_run') * 4),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS on_base_plus_slugging
FROM
    {{ ref('fact_statcast_events') }}
WHERE events IS NOT NULL
GROUP BY game_year, EXTRACT(MONTH FROM game_date), batter_name, batter_id
ORDER BY game_year ASC, EXTRACT(MONTH FROM game_date) ASC, batter_name ASC