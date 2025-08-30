
CORE_SPLITS_METRICS_QUERY = """
  -- Number of hits
  COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS hits,

  -- Number of each type of hit
  COUNTIF(events = 'home_run') AS homeruns,
  COUNTIF(events = 'double') AS doubles,
  COUNTIF(events = 'triple') AS triples,
  COUNTIF(events = 'single') AS singles,

  -- Number of BBs
  COUNTIF(events in ('hit_by_pitch', 'walk', 'intent_walk')) AS bb_hbp,

  -- Number of strikeouts
  COUNTIF(events = 'strikeout') AS so,

  -- Number of at bats
  COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS ab,

  -- BA
  ROUND(SAFE_DIVIDE(
    COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf') -- total at bats
  )), 3
  ) AS avg,

  -- OBP
  ROUND(SAFE_DIVIDE(
      COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
      COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
  ), 3) AS obp,

  -- SLG
  ROUND(SAFE_DIVIDE(
    (COUNTIF(events = 'single') * 1) + 
    (COUNTIF(events = 'double') * 2) + 
    (COUNTIF(events = 'triple') * 3) + 
    (COUNTIF(events = 'home_run') * 4), -- total bases
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) -- total at bats
  ), 3) AS slg,

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
  ), 3) AS ops,
  -- Number of batting events
  COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa')) AS hitting_events,
  -- Launch angle
  ROUND(SAFE_DIVIDE(
    SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN launch_angle ELSE NULL END),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
  ), 3) AS launch_angle,
  -- Exit velocity
  ROUND(SAFE_DIVIDE(
    SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN launch_speed ELSE NULL END),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
  ), 3) AS exit_velocity,
  -- Bat speed
  ROUND(SAFE_DIVIDE(
    SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN bat_speed ELSE NULL END),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
  ), 3) AS bat_speed,
  -- Swing length
  ROUND(SAFE_DIVIDE(
    SUM(CASE WHEN events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa') THEN swing_length ELSE NULL END),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt', 'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'))
  ), 3) AS swing_length,
  -- Hard Hit count
  COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95) AS hard_hit_count,
  COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout')) AS denominator_for_hard_hit_rate,
  -- Hard Hit rate
  ROUND(SAFE_DIVIDE(
    COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout'))
  ), 3) AS hard_hit_rate,
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
  ) AS barrels_count,
  -- total batted balls, only considering valid events with inplay
  COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'strikeout', 'strikeout_double_play', 'truncated_pa')) AS total_batted_balls,
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
  ), 3) AS barrels_rate,
  -- strikeouts rate
  ROUND(SAFE_DIVIDE(
    COUNTIF(events = 'strikeout'),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
  ), 3) AS strikeout_rate,
  -- Swinging strike count
  COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked')) AS swinging_strike_count,
  -- Swinging strike rate
  ROUND(SAFE_DIVIDE(
    COUNTIF(description IN ('swinging_strike', 'swinging_strike_blocked')),
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
  ), 3) AS swinging_strike_rate,
  -- RBI
  SUM(
    -- CASE 1: for home run, 1 rbi for himself first
    CASE
        WHEN events = 'home_run' THEN 1
        ELSE 0
    END
    -- CASE 2: Count 'scores', and adding up
    + ARRAY_LENGTH(REGEXP_EXTRACT_ALL(des, r'scores\.'))
    ) AS rbi
"""