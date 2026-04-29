-- dbt model
{{ config(
    materialized='table',
    description="Pitcher performance statistics by inning",
    alias='tbl_pitching_performance_by_inning',
    tags=['pitching_performance', 'inning'],
    enabled=True
) }}
WITH inning_stats AS (
    SELECT
        game_year,
        CONCAT(SPLIT(pitcher_name, ', ')[OFFSET(1)], ' ', SPLIT(pitcher_name, ', ')[OFFSET(0)]) AS pitcher_name,
        pitcher_id,
        inning,
        events,
        COUNT(events) AS count -- count of each event type per inning
    FROM
        {{ ref('fact_statcast_events') }}
    WHERE description IS NOT NULL
    AND events IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5
    -- ORDER BY
    --     game_year ASC, pitcher_name, inning ASC, events
)
SELECT
    game_year,
    pitcher_name,
    pitcher_id,
    inning,
    -- sum of all hits allowed per inning
    SUM(CASE WHEN events IN ('single', 'double', 'triple', 'home_run') THEN count ELSE 0 END) AS hits_allowed,
    --sum of all non-hit events per inning
    SUM(CASE WHEN events IN ('strikeout', 'field_out', 'strikeout_double_play', 'grounded_into_double_play',
        'field_error', 'force_out', 'double_play', 'fielders_choice', 'fielders_choice_out') THEN count ELSE 0 END) AS outs_recorded,
    -- calculate batting average against (BAA) as hits allowed divided by total events excluding some non-hitting events
    ROUND(SAFE_DIVIDE(
        SUM(CASE WHEN events IN ('single', 'double', 'triple', 'home_run') THEN count ELSE 0 END),
        SUM(CASE WHEN events IS NOT NULL AND events NOT IN ('hit_by_pitch', 'walk', 'sac_fly', 'sac_bunt', 'catcher_interf') THEN count ELSE 0 END)
    ), 3) AS batting_average_against,
    -- numerator for OBP Against (被出塁率): hits + walks + hit by pitch
    SUM(CASE WHEN events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch') THEN count ELSE 0 END) AS obp_numerator, 
    -- denominator for OBP Against: PA excluding catcher interference and running interference (打席 (Plate Appearances) - 打撃妨害/走塁妨害)
    SUM(CASE WHEN events IS NOT NULL AND events NOT IN ('catcher_interf') THEN count ELSE 0 END) AS obp_denominator,
    -- numerator for SLG Against (被長打率): singles + 2*double + 3*triple + 4*home_run
    SUM(CASE WHEN events = 'single' THEN count ELSE 0 END) +
    SUM(CASE WHEN events = 'double' THEN count * 2 ELSE 0 END) +
    SUM(CASE WHEN events = 'triple' THEN count * 3 ELSE 0 END) +
    SUM(CASE WHEN events = 'home_run' THEN count * 4 ELSE 0 END) AS slg_numerator,
    -- denominator for SLG Against: At-Bats excluding some non-hitting events
    SUM(CASE WHEN events IS NOT NULL AND events NOT IN ('hit_by_pitch', 'walk', 'sac_fly', 'sac_bunt', 'catcher_interf') THEN count ELSE 0 END) AS slg_denominator,
    -- calculate OPS against as the sum of OBP and SLG
    ROUND(
        SAFE_DIVIDE(
            SUM(CASE WHEN events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch') THEN count ELSE 0 END), 
            SUM(CASE WHEN events IS NOT NULL AND events NOT IN ('catcher_interf') THEN count ELSE 0 END)
            ) -- OBP Against
        +
        SAFE_DIVIDE(
            SUM(CASE WHEN events = 'single' THEN count ELSE 0 END) + SUM(CASE WHEN events = 'double' THEN count * 2 ELSE 0 END) 
            + SUM(CASE WHEN events = 'triple' THEN count * 3 ELSE 0 END) + SUM(CASE WHEN events = 'home_run' THEN count * 4 ELSE 0 END), 
            SUM(CASE WHEN events IS NOT NULL AND events NOT IN ('hit_by_pitch', 'walk', 'sac_fly', 'sac_bunt', 'catcher_interf') THEN count ELSE 0 END)
            ) -- SLG Against
    , 3) AS ops_against,
    -- calculate number of home runs allowed per inning
    SUM(CASE WHEN events = 'home_run' THEN count ELSE 0 END) AS home_runs_allowed,
    -- calculate number of hits allowed per inning other than home runs
    SUM(CASE WHEN events IN ('single', 'double', 'triple') THEN count ELSE 0 END) AS non_home_run_hits_allowed,
    -- calculate number of walks and hit by pitches per inning
    SUM(CASE WHEN events IN ('walk', 'hit_by_pitch') THEN count ELSE 0 END) AS free_passes
FROM inning_stats
GROUP BY 1, 2, 3, 4
ORDER BY
    game_year ASC, pitcher_name, inning ASC