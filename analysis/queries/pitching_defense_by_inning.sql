-- SQL query to analyze pitching defense by inning
-- This query aggregates strikes, balls, and balls in play for each pitcher by inning
CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.view_pitching_counts_by_inning_2025` AS
SELECT
    player_name AS pitcher_name,
    pitcher AS pitcher_id,
    inning,
    COUNT(*) AS total_pitches,
    COUNTIF(type = 'S') AS total_strikes,
    COUNTIF(type = 'B') AS total_balls,
    COUNTIF(type = 'X') AS ball_in_play,
    ROUND(COUNTIF(type = 'S') / COUNT(*) , 3) AS strike_rate,
    ROUND(COUNTIF(type = 'B') / COUNT(*) , 3) AS ball_rate,
    ROUND(COUNTIF(type = 'X') / COUNT(*) , 3) AS bip_rate
FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
WHERE player_name IS NOT NULL
GROUP BY pitcher_name, pitcher_id, inning
ORDER BY pitcher_name, inning


-- pitch type, pitch speed, and pitch spin rate by inning
CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.view_pitch_type_quality_by_inning_2025` AS
SELECT
    player_name AS pitcher_name,
    pitcher AS pitcher_id,
    inning,
    pitch_name,
    COUNT(*) AS total_pitches,
    ROUND(AVG(release_speed), 2) AS avg_release_speed,
    ROUND(AVG(release_spin_rate), 2) AS avg_spin_rate,
    -- pitch type ratio
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY player_name, inning), 3) AS pitch_type_ratio
FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
WHERE player_name IS NOT NULL
    AND pitch_name IS NOT NULL
    AND release_speed IS NOT NULL
    AND release_spin_rate IS NOT NULL
GROUP BY pitcher_name, pitcher_id, inning, pitch_name
ORDER BY pitcher_name, pitcher_id, inning, pitch_name