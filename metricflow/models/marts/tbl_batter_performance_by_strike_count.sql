{{ config(
    materialized='table',
    description='Batter performance statistics by strike count',
    tags=['batter_performance', 'strike_count'],
    alias='tbl_batter_performance_by_strike_count',
    enabled=True
)}}

WITH processed_statcast_data AS (
SELECT
    game_date,
    game_year,
    batter_name,
    strikes,
    events,
    batter_id,
    game_type,
    pitcher_id,
    -- create batted results category based on events
    CASE
        WHEN events IN ('single', 'double', 'triple', 'home_run') THEN 'hit'
        WHEN events IN ('strikeout', 'field_out', 'strikeout_double_play', 'grounded_into_double_play',
                        'field_error', 'force_out', 'double_play', 'fielders_choice', 'fielders_choice_out') THEN 'out'
        WHEN events IN ('hit_by_pitch', 'walk', 'intent_walk') THEN 'bb_hbp'
        WHEN events IN ('sac_fly', 'sac_bunt') THEN 'sacrifice'
        WHEN events IS NULL THEN NULL
        ELSE 'other'
    END AS batted_results,
    -- create a flag for at-bat events
    CASE
        WHEN events IN ('single', 'double', 'triple', 'home_run', 'strikeout', 'field_out',
                        'strikeout_double_play', 'grounded_into_double_play', 'field_error',
                        'force_out', 'double_play', 'fielders_choice', 'fielders_choice_out') THEN TRUE
        ELSE FALSE
    END AS is_at_bat_event,
    -- create a flag for on-base events
    CASE
        WHEN events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk') THEN TRUE
        ELSE FALSE
    END AS is_on_base_event,
    -- create a flag for plate appearance events
    CASE
        WHEN events NOT IN ('catcher_interf', 'sac_bunt') THEN TRUE -- NOTE: these events are counted as PA but for OBP calulation we ignore them
        ELSE FALSE
    END AS is_event_for_obp_denominator
FROM
    {{ ref('fact_statcast_events') }}
WHERE events IS NOT NULL
    AND batter_name IS NOT NULL
)
SELECT
    game_year,
    batter_name,
    strikes AS strike_count, -- each strike count 0, 1, 2
    COUNTIF(batted_results = 'hit') AS total_hits,
    COUNTIF(is_at_bat_event) AS total_at_bats, -- for batting average calculation
    COUNTIF(is_event_for_obp_denominator) AS total_plate_appearances_for_obp, -- for on-base percentage calculation
    -- batting average
    CASE
        WHEN COUNTIF(is_at_bat_event) = 0 THEN CAST(NULL AS FLOAT64)
        ELSE ROUND(SAFE_DIVIDE(COUNTIF(batted_results = 'hit'), COUNTIF(is_at_bat_event)), 3)
    END AS batting_average_at_strike_count, -- batting average is displayed with 3rd decimal place like 0.320
    -- on-base percentage
    CASE
        WHEN COUNTIF(is_event_for_obp_denominator) = 0 THEN CAST(NULL AS FLOAT64)
        ELSE ROUND(SAFE_DIVIDE(COUNTIF(is_on_base_event), COUNTIF(is_event_for_obp_denominator)), 3)
    END AS on_base_percentage_at_strike_count,
    -- slugging percentage
    CASE
        WHEN COUNTIF(is_at_bat_event) = 0 THEN CAST(NULL AS FLOAT64)
        ELSE ROUND(SAFE_DIVIDE(
            COUNTIF(events = 'single') + 
            COUNTIF(events = 'double') * 2 + 
            COUNTIF(events = 'triple') * 3 + 
            COUNTIF(events = 'home_run') * 4, 
            COUNTIF(is_at_bat_event)), 3)
    END AS slugging_percentage_at_strike_count,
    -- total bases for slugging
    (COUNTIF(events = 'single') + 
        COUNTIF(events = 'double') * 2 + 
        COUNTIF(events = 'triple') * 3 + 
        COUNTIF(events = 'home_run') * 4) AS total_bases_for_slugging,
    COUNTIF(events = 'home_run') AS total_home_runs,
    COUNTIF(events = 'single') AS total_singles,
    COUNTIF(events = 'double') AS total_doubles,
    COUNTIF(events = 'triple') AS total_triples,
    -- count of slugging percentage components
    COUNTIF(events IN ('home_run', 'double', 'triple')) AS total_extra_base_hits
FROM processed_statcast_data
WHERE batted_results IN ('hit', 'out', 'bb_hbp', 'sacrifice') -- only relevant batted results
GROUP BY game_year, batter_name, strikes
ORDER BY game_year ASC, batter_name ASC, strikes ASC