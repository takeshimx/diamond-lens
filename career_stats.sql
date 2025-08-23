WITH career_stats_from_statcast AS (
    SELECT
        batter_name,
        batter_id,
        -- Number of hits
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS career_hits,
        -- Number of each type of hit
        COUNTIF(events = 'home_run') AS career_homeruns,
        COUNTIF(events = 'double') AS career_doubles,
        COUNTIF(events = 'triple') AS career_triples,
        COUNTIF(events = 'single') AS career_singles,

        -- Number of strikeouts
        COUNTIF(events = 'strikeout') AS career_so,

        -- Number of at bats
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS career_ab,

        -- BA
        ROUND(SAFE_DIVIDE(
            COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- total at bats
        ), 3
        ) AS career_batting_average,

        -- OBP
        ROUND(SAFE_DIVIDE(
            COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
            COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3) AS career_on_base_percentage,

        -- SLG
        ROUND(SAFE_DIVIDE(
            (COUNTIF(events = 'single') * 1) + 
            (COUNTIF(events = 'double') * 2) + 
            (COUNTIF(events = 'triple') * 3) + 
            (COUNTIF(events = 'home_run') * 4), -- total bases
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- total at bats
        ), 3) AS career_slugging_percentage,

        -- OPS
        ROUND(SAFE_DIVIDE(
            COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
            COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3) +
        ROUND(SAFE_DIVIDE(
            (COUNTIF(events = 'single') * 1) + 
            (COUNTIF(events = 'double') * 2) + 
            (COUNTIF(events = 'triple') * 3) + 
            (COUNTIF(events = 'home_run') * 4), -- total bases
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- total at bats
        ), 3) AS career_on_base_plus_slugging,
        -- Number of batting events
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa')) AS career_hitting_events,
        -- Launch angle
        ROUND(SAFE_DIVIDE(
            SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN launch_angle ELSE NULL END),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
        ), 3) AS career_launch_angle,
        -- Exit velocity
        ROUND(SAFE_DIVIDE(
            SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN launch_speed ELSE NULL END),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
        ), 3) AS career_exit_velocity,
        -- Bat speed
        ROUND(SAFE_DIVIDE(
            SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN bat_speed ELSE NULL END),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
        ), 3) AS career_bat_speed,
        -- Swing length
        ROUND(SAFE_DIVIDE(
            SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN swing_length ELSE NULL END),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
        ), 3) AS career_swing_length,
        -- Hard Hit count
        COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95) AS career_hard_hit_count,
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout')) AS career_denominator_for_hard_hit_rate,
        -- Hard Hit rate
        ROUND(SAFE_DIVIDE(
            COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout'))
        ), 3) AS career_hard_hit_rate,
        -- barrels
        COUNTIF(
            -- launch speed >= 98
            launch_speed IS NOT NULL AND launch_speed >= 98
            AND
            (
                -- launch angle condition by launch speed
                (launch_speed = 98 AND launch_angle BETWEEN 26 AND 30) OR
                (launch_speed = 99 AND launch_angle BETWEEN 25 AND 31) OR
                (launch_speed = 100 AND launch_angle BETWEEN 25 AND 31) OR
                (launch_speed = 101 AND launch_angle BETWEEN 24 AND 32) OR
                (launch_speed = 102 AND launch_angle BETWEEN 24 AND 33) OR
                (launch_speed = 103 AND launch_angle BETWEEN 23 AND 34) OR
                (launch_speed = 104 AND launch_angle BETWEEN 23 AND 34) OR
                (launch_speed = 105 AND launch_angle BETWEEN 22 AND 35) OR
                (launch_speed >= 106 AND launch_angle BETWEEN 5 AND 50)
            )
        ) AS career_barrels_count,
        -- total batted balls, only considering valid events with inplay
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'strikeout', 'strikeout_double_play', 'truncated_pa')) AS career_total_batted_balls,
        -- barrels rate
        ROUND(SAFE_DIVIDE(
            COUNTIF(
            launch_speed IS NOT NULL AND launch_speed >= 98
            AND
            (
                -- launch angle condition by launch speed
                (launch_speed = 98 AND launch_angle BETWEEN 26 AND 30) OR
                (launch_speed = 99 AND launch_angle BETWEEN 25 AND 31) OR
                (launch_speed = 100 AND launch_angle BETWEEN 25 AND 31) OR
                (launch_speed = 101 AND launch_angle BETWEEN 24 AND 32) OR
                (launch_speed = 102 AND launch_angle BETWEEN 24 AND 33) OR
                (launch_speed = 103 AND launch_angle BETWEEN 23 AND 34) OR
                (launch_speed = 104 AND launch_angle BETWEEN 23 AND 34) OR
                (launch_speed = 105 AND launch_angle BETWEEN 22 AND 35) OR
                (launch_speed >= 106 AND launch_angle BETWEEN 5 AND 50)
            )
            ),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
        ), 3) AS career_barrels_rate,
        -- strikeouts rate
        ROUND(SAFE_DIVIDE(
            COUNTIF(events = 'strikeout'),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3) AS career_strikeout_rate,
        -- Swinging strike count
        COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked')) AS career_swinging_strike_count,
        -- Swinging strike rate
        ROUND(SAFE_DIVIDE(
            COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked')),
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
        ), 3) AS career_swinging_strike_rate
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.tbl_statcast_2021_2025_master`
    WHERE events IS NOT NULL
        AND game_type = "R"
        AND batter_name IS NOT NULL
        AND batter_id IS NOT NULL
    GROUP BY
        batter_name, batter_id
    ORDER BY
        batter_name ASC
)
SELECT
    a.*,
    COALESCE(SUM(b.pa), 0) AS career_plate_appearances,
    COALESCE(SUM(b.g), 0) AS career_games,
    COALESCE(SUM(b.r), 0) AS career_runs,
    COALESCE(SUM(b.rbi), 0) AS career_rbi,
    COALESCE(SUM(b.bb), 0) AS career_walks,
    COALESCE(SUM(b.ibb), 0) AS career_intent_walks,
    COALESCE(SUM(b.hbp), 0) AS career_hit_by_pitch,
    COALESCE(SUM(b.sb), 0) AS career_stolen_bases,
    COALESCE(SUM(b.war), 0) AS career_war,
    MIN(b.season) AS career_first_season,
    MAX(b.season) AS career_current_season,
    CASE 
        WHEN MIN(b.season) IS NOT NULL AND MAX(b.season) IS NOT NULL 
        THEN MAX(b.season) - MIN(b.season) + 1 
        ELSE NULL 
    END AS career_year_of_service,
    -- last team
    ARRAY_AGG(b.team ORDER BY b.season DESC LIMIT 1)[OFFSET(0)] AS career_last_team
FROM career_stats_from_statcast a
RIGHT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_with_risp` b
ON a.batter_id = b.mlbid
GROUP BY
    a.batter_name, 
    a.batter_id,
    a.career_hits,
    a.career_homeruns,
    a.career_doubles,
    a.career_triples,
    a.career_singles,
    a.career_so,
    a.career_ab,
    a.career_batting_average,
    a.career_on_base_percentage,
    a.career_slugging_percentage,
    a.career_on_base_plus_slugging,
    a.hitting_events_by_pitch_type,
    a.career_launch_angle,
    a.career_exit_velocity,
    a.career_bat_speed,
    a.career_swing_length,
    a.career_hard_hit_count,
    a.career_denominator_for_hard_hit_rate,
    a.career_hard_hit_rate,
    a.career_barrels_count,
    a.career_total_batted_balls,
    a.career_barrels_rate,
    a.career_strikeout_rate,
    a.career_swinging_strike_count,
    a.career_swinging_strike_rate