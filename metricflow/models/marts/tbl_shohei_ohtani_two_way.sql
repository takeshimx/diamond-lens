-- tbl model
{{ config(
    materialized='table',
    description='Shohei Ohtani two-way player statistics',
    alias='tbl_shohei_ohtani_two_way',
    tags=['shohei_ohtani', 'two_way', 'batting_performance'],
    enabled=True
)}}
WITH OhtaniGames AS (
    SELECT
        game_year,
        EXTRACT(MONTH FROM game_date) AS game_month,
        game_date,
        batter_name,
        batter_id,
        LEAD(game_date, 1) OVER (PARTITION BY batter_id ORDER BY game_date ASC) AS next_game_date_for_batter,
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS hits,
        COUNTIF(events = 'home_run') AS home_runs,
        COUNTIF(events = 'double') AS doubles,
        COUNTIF(events = 'triple') AS triples,
        COUNTIF(events = 'single') AS singles,
        -- Walks and HBP
        COUNTIF(events IN ('walk', 'hit_by_pitch', 'intent_walk')) AS walks_and_hbp,
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS at_bats,
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')) AS numerator_for_obp,
        COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf')) AS denominator_for_obp,
        
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
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- at-bats
        ), 3) AS slugging_percentage,

        -- OPS
        ROUND(
        (
            ROUND(SAFE_DIVIDE(
            COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
            COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3)
        ) + 
        (
            ROUND(SAFE_DIVIDE(
            (COUNTIF(events = 'single') * 1) + 
            (COUNTIF(events = 'double') * 2) + 
            (COUNTIF(events = 'triple') * 3) + 
            (COUNTIF(events = 'home_run') * 4),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3)
        )
        , 3) AS on_base_plus_slugging
    FROM
        {{ ref('fact_statcast_events') }}
    WHERE events IS NOT NULL
        AND batter_name = "Shohei Ohtani"
    GROUP BY 
        game_year, 
        EXTRACT(MONTH FROM game_date),
        game_date,
        batter_name,
        batter_id
    ORDER BY 
        game_year ASC, 
        EXTRACT(MONTH FROM game_date) ASC,
        game_date
),
OhtaniPitchingDates AS (
    SELECT
      game_date AS sp_date -- date when Shohei Ohtani was a starting pitcher
    FROM
        {{ ref('fact_statcast_events') }}
    WHERE events IS NOT NULL
      AND pitcher_id = 660271
    GROUP BY game_date
    ORDER BY game_date ASC
)
SELECT
    og.batter_id AS batter_mlb_id,
    opd.sp_date AS pitching_game_date,
    og.game_date AS pitching_game_batting_date,
    -- stats on starting pithing date
    og.hits,
    og.home_runs,
    og.triples,
    og.doubles,
    og.singles,
    og.walks_and_hbp,
    og.at_bats,
    og.numerator_for_obp,
    og.denominator_for_obp,
    og.batting_average,
    og.on_base_percentage,
    og.slugging_percentage,
    og.on_base_plus_slugging,
    -- stats on following game date
    og.next_game_date_for_batter,
    next_game_stats.hits AS next_game_hits,
    next_game_stats.home_runs AS next_game_home_runs,
    next_game_stats.triples AS next_game_triples,
    next_game_stats.doubles AS next_game_doubles,
    next_game_stats.singles AS next_game_singles,
    next_game_stats.walks_and_hbp AS next_game_walks_and_hbp,
    next_game_stats.at_bats AS next_game_at_bats,
    next_game_stats.numerator_for_obp AS next_game_numerator_for_obp,
    next_game_stats.denominator_for_obp AS next_game_denominator_for_obp,
    next_game_stats.batting_average AS next_game_batting_average,
    next_game_stats.on_base_percentage AS next_game_on_base_percentage,
    next_game_stats.slugging_percentage AS next_game_slugging_percentage,
    next_game_stats.on_base_plus_slugging AS next_game_on_base_plus_slugging
FROM OhtaniPitchingDates opd
JOIN OhtaniGames og ON opd.sp_date = og.game_date
-- JOIN for retrieving next game stats
LEFT JOIN OhtaniGames AS next_game_stats
    ON og.batter_id = next_game_stats.batter_id
    AND og.next_game_date_for_batter = next_game_stats.game_date
ORDER BY opd.sp_date

