-- Launch Angle Sweet Spot Analysis by Stadium
WITH stadium_stats AS (
    SELECT
        home_team,
        -- total hits
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS total_hits,
        -- total events,
        COUNT(*) AS total_events,
        -- hit rate
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) / COUNT(*) AS sweet_spot_ba
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
    WHERE launch_angle BETWEEN 20 AND 30
        AND events IS NOT NULL
    GROUP BY home_team
    HAVING total_events >= 500
),
ranked_stadiums AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (ORDER BY sweet_spot_ba DESC) AS rank_high,
        ROW_NUMBER() OVER (ORDER BY sweet_spot_ba ASC) AS rank_low
    FROM stadium_stats
)
SELECT
    home_team,
    total_hits,
    total_events,
    ROUND(sweet_spot_ba, 3) AS sweet_spot_ba,
    CASE
        WHEN rank_high <= 5 THEN 'Top 5'
        WHEN rank_low <=5 THEN 'Bottom 5'
    END AS category
FROM ranked_stadiums
WHERE rank_high <= 5 OR rank_low <= 5
ORDER BY sweet_spot_ba DESC


-- Platoon Advantage Effectiveness
-- platoon advantage when batter and pitcher have opposite handedness
-- 有利な対戦と不利な対戦でのwOBAの差を計算し、差が大きい順に上位20人を抽出。
-- 差が大きいということは、プラトーンアドバンテージの影響が大きいことを示すため、同じ利き手の投手に変更したほうが抑える効果が高い可能性がある。
WITH batter_matchups AS (
  SELECT
    batter,
    stand,
    p_throws,
    COUNT(*) AS pa_count,
    AVG(woba_value) AS avg_woba
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
  WHERE events IS NOT NULL
    AND woba_value IS NOT NULL
  GROUP BY batter, stand, p_throws
  HAVING pa_count >= 50
),
platoon_comparison AS (
    SELECT
        advantagous.batter,
        CONCAT(dim.first_name, ' ', dim.last_name) AS batter_name,
        advantagous.stand AS batter_stand,
        advantagous.avg_woba AS advantagous_woba,
        advantagous.pa_count AS advantagous_pa,
        disadvantagous.avg_woba AS disadvantagous_woba,
        disadvantagous.pa_count AS disadvantagous_pa,
        advantagous.avg_woba - disadvantagous.avg_woba AS platoon_advantage
    FROM batter_matchups AS advantagous
    INNER JOIN batter_matchups AS disadvantagous
        ON advantagous.batter = disadvantagous.batter
        AND advantagous.stand = disadvantagous.stand
    LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.dim_players` dim
        ON advantagous.batter = dim.mlb_id
    WHERE
        -- advantagous matchups
        (advantagous.stand = 'L' AND advantagous.p_throws = 'R'
        OR advantagous.stand = 'R' AND advantagous.p_throws = 'L')

        -- disadvantagous matchups
        AND (disadvantagous.stand = 'L' AND disadvantagous.p_throws = 'L'
        OR disadvantagous.stand = 'R' AND disadvantagous.p_throws = 'R')
)
SELECT *
FROM platoon_comparison
WHERE batter_name IS NOT NULL
ORDER BY platoon_advantage DESC
LIMIT 20



-- Pitcher Fatigue Indicator (Pitch Count within Game) [PENDING]
WITH all_pitches AS (
  SELECT 
    player_name,
    game_date,
    ROW_NUMBER() OVER (PARTITION BY game_date, player_name ORDER BY inning ASC, batter ASC, pitch_number ASC) AS pitch_count,
    pitch_name,
    release_speed,
    release_spin_rate
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025` 
    -- AND pitch_name IN ('4-Seam Fastball', 'Fastball')
  ORDER BY player_name, game_date, inning, batter, pitch_number
),
fastball AS (
  SELECT *
  FROM all_pitches
  WHERE pitch_name IN ('4-Seam Fastball', 'Fastball')
)
SELECT
  player_name,
  game_date,
  CASE
    WHEN pitch_count BETWEEN 1 AND 25 THEN '1-25'
    WHEN pitch_count BETWEEN 26 AND 50 THEN '26-50'
    WHEN pitch_count BETWEEN 51 AND 75 THEN '51-75'
    WHEN pitch_count BETWEEN 76 AND 100 THEN '76-100'
    ELSE '101+'
  END AS pitch_count_range,
  ROUND(AVG(release_speed), 3) AS avg_release_speed,
  ROUND(AVG(release_spin_rate), 3) AS avg_spin_rate,
  COUNT(*) AS pitch_count_in_range
FROM fastball
GROUP BY player_name, game_date, pitch_count_range
HAVING COUNT(*) >= 10
  

-- Multi-dimensional Pitcher Performance Analysis
WITH base AS (
    SELECT
        player_name,
        pitch_name,
        -- runners situation
        CASE
            WHEN (on_1b = 0 AND on_2b = 0 AND on_3b = 0) THEN 'no runner'
            WHEN (on_1b != 0 AND on_2b = 0 AND on_3b = 0) THEN 'runner on 1b'
            WHEN (on_1b = 0 AND on_2b != 0 AND on_3b = 0) THEN 'runner on 2b'
            WHEN (on_1b = 0 AND on_2b = 0 AND on_3b != 0) THEN 'runner on 3b'
            WHEN (on_1b != 0 AND on_2b != 0 AND on_3b = 0) THEN 'runners on 1b & 2b'
            WHEN (on_1b != 0 AND on_2b = 0 AND on_3b != 0) THEN 'runner on 1b & 3b'
            WHEN (on_1b = 0 AND on_2b != 0 AND on_3b != 0) THEN 'runner on 2b & 3b'
            ELSE 'bases loaded'
        END AS runner_situation,
        events
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
    WHERE events IS NOT NULL
        AND pitch_name IS NOT NULL
),
baa_stats AS (
    SELECT
        player_name,
        pitch_name,
        runner_situation,
        -- batting average against (BAA)
        ROUND(COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) / COUNT(*), 3) AS baa
    FROM base
    WHERE player_name IN (
        SELECT
        player_name
        FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
        GROUP BY 1
        HAVING COUNT(pitch_name) >= 100
    )
        AND pitch_name IN (
            SELECT
            pitch_name
            FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
            GROUP BY 1
            HAVING COUNT(pitch_name) >= 100
        )
    GROUP BY player_name, pitch_name, runner_situation
)
SELECT *,
    MAX(baa) OVER (PARTITION BY player_name) - MIN(baa) OVER (PARTITION BY player_name) AS baa_diff
FROM baa_stats
ORDER BY player_name, pitch_name, runner_situation


-- イニング進行による投手パフォーマンス劣化分析
WITH eligibele_pitchers AS (
  SELECT
    player_name,
    game_pk
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
  WHERE player_name IS NOT NULL
  GROUP BY 1, 2
  HAVING COUNT(DISTINCT inning) >= 5
), 
pitcher_stats AS (
  SELECT
    t1.player_name,
    t1.inning,
    AVG(woba_value) AS avg_woba_against,
    -- number of batters faced
    COUNT(DISTINCT t1.batter) AS batters_faced,
    -- strikeouts
    COUNTIF(events in ('strikeout', 'strikeout_double_play')) AS so_count
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025` t1
  JOIN eligibele_pitchers t2 ON t1.player_name = t2.player_name AND t1.game_pk = t2.game_pk
  WHERE t1.woba_value IS NOT NULL
    AND t1.events IS NOT NULL
  GROUP BY 1, 2
  HAVING COUNT(DISTINCT t1.batter) >= 30
),
combined_woba AS (
    SELECT
        player_name,
        -- early innings 1-2 woba
        AVG(CASE WHEN inning IN (1, 2) THEN avg_woba_against ELSE NULL END) AS early_woba,
        -- late innings 5- woba
        AVG(CASE WHEN inning >= 5 THEN avg_woba_against ELSE NULL END) AS late_woba,
        -- strikeout rate
        ROUND(SUM(CASE WHEN inning IN (1, 2) THEN so_count ELSE 0 END) / SUM(CASE WHEN inning IN (1, 2) THEN batters_faced ELSE 0 END) * 100, 2) AS early_so_rate
    FROM pitcher_stats
    GROUP BY player_name
)
SELECT
    player_name,
    late_woba - early_woba AS woba_diff_increase
FROM combined_woba
WHERE early_woba IS NOT NULL AND late_woba IS NOT NULL
ORDER BY woba_diff_increase DESC
LIMIT 10


-- カウント別投球戦略と成績相関
WITH pitch_counts_by_situation AS (
 SELECT
      player_name,
      pitch_name,
      -- カウント状況のエンコード（有利/不利を特定）
      CASE
        WHEN (balls = 0 AND strikes = 2) THEN '0-2'
        WHEN (balls = 1 AND strikes = 2) THEN '1-2'
        WHEN (balls = 0 AND strikes = 1) THEN '0-1'
        WHEN (balls = 3 AND strikes = 0) THEN '3-0'
        WHEN (balls = 3 AND strikes = 1) THEN '3-1'
        WHEN (balls = 2 AND strikes = 0) THEN '2-0'
        ELSE 'OTHER'
      END AS counts,
      
      -- 打率の計算に必要な統計量
      COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS total_hits,
      COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS total_abs,
      COUNT(*) AS pitch_counts
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
  WHERE player_name IS NOT NULL AND pitch_name IS NOT NULL
  GROUP BY 1, 2, 3
  HAVING pitch_counts >= 50
),
pitching_ratio_stats AS (
  SELECT
    *,
    -- batting average against (BAA)
    ROUND(SAFE_DIVIDE(total_hits, total_abs), 3) AS baa,
    -- pitch ratio by count situation
    pitch_counts / SUM(pitch_counts) OVER (PARTITION BY player_name, counts) AS pitch_ratio
  FROM pitch_counts_by_situation
  WHERE counts != 'OTHER' AND total_abs > 0
),
most_used_pitch AS (
  SELECT
    player_name,
    pitch_name,
    baa,
    pitch_ratio,
    -- most thrown pitch type at advantagous count situation
    RANK() OVER (PARTITION BY player_name ORDER BY pitch_counts DESC) AS rnk_usage
  FROM pitching_ratio_stats
  WHERE counts IN ('0-2', '1-2', '0-1')
)
SELECT
  player_name,
  pitch_name AS most_pitch_used,
  baa As baa_on_most_pitch_used
FROM most_used_pitch
WHERE rnk_usage = 1
ORDER BY baa ASC
LIMIT 15


-- 左右打者対応力分析
WITH pitcher_matchups AS (
  SELECT
    player_name AS pitcher_name,
    stand AS batter_stand,
    AVG(woba_value) AS avg_woba_against,
    AVG(iso_value) AS avg_iso_against,
    COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS at_bats
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
  WHERE events IS NOT NULL
    AND woba_value IS NOT NULL
    AND iso_value IS NOT NULL
  GROUP BY 1, 2
  HAVING at_bats >= 100
)
SELECT
  pitcher_name,
  -- wOBA
  MAX(CASE WHEN batter_stand = 'L' THEN avg_woba_against ELSE NULL END) AS woba_vs_lhb,
  MAX(CASE WHEN batter_stand = 'R' THEN avg_woba_against ELSE NULL END) AS woba_vs_rhb,
  -- ISO
  MAX(CASE WHEN batter_stand = 'L' THEN avg_iso_against ELSE NULL END) AS iso_vs_lhb,
  MAX(CASE WHEN batter_stand = 'R' THEN avg_iso_against ELSE NULL END) AS iso_vs_rhb,
  -- wOBA diff
  ABS(SUM(CASE WHEN batter_stand = 'L' THEN avg_woba_against ELSE 0 END) 
    - SUM(CASE WHEN batter_stand = 'R' THEN avg_woba_against ELSE 0 END)) AS woba_delta
FROM pitcher_matchups
GROUP BY 1
HAVING
  -- 左右両方のデータ（LHBとRHB）が存在する投手のみに最終フィルタリング
  COUNT(CASE WHEN batter_stand = 'L' THEN 1 ELSE NULL END) = 1
  AND COUNT(CASE WHEN batter_stand = 'R' THEN 1 ELSE NULL END) = 1
ORDER BY woba_delta ASC
LIMIT 10

-- プレッシャー場面での成績乖離分析
WITH game_situations AS (
  SELECT 
    batter AS batter_id,
    CASE
      -- High pressure situation (definition: RISP AND 2 outs AND score diff is less then 4)
      WHEN ((on_2b != 0 OR on_3b != 0) AND (outs_when_up = 2) AND (ABS(bat_score - fld_score) <= 3)) THEN 'High pressure'
      WHEN (on_2b != 0 OR on_3b != 0) THEN 'RISP' -- RISP
      WHEN (on_1b = 0 AND on_2b = 0 AND on_3b = 0) THEN 'No runner' -- no runner
      ELSE 'Other'
    END AS game_situation,
    COUNT(*) AS at_bats,
    -- BA
    ROUND(SAFE_DIVIDE(
      COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits
      COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf') -- total at bats
    )), 3
    ) AS batting_average,
    -- wOBA
    AVG(woba_value) AS avg_woba
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025`
  WHERE events IS NOT NULL
  GROUP BY 1, 2
  HAVING at_bats >= 10
),
eligible_batters AS (
  SELECT batter_id
  FROM game_situations
  GROUP BY 1
  -- HAVING COUNT(DISTINCT CASE WHEN game_situation IN ('No runner', 'High pressure') THEN game_situation ELSE NULL END) = 2
),
performance_metrics AS (
  SELECT
    t1.batter_id,
    CONCAT(t3.first_name, ' ', t3.last_name) AS batter_name,
    t1.game_situation,
    t1.batting_average,
    t1.avg_woba
  FROM game_situations t1
  JOIN eligible_batters t2 USING (batter_id)
  LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.dim_players` t3 ON t1.batter_id = t3.mlb_id
)
SELECT
  batter_name,
  MAX(CASE WHEN game_situation = 'No runner' THEN batting_average ELSE NULL END) AS BA_NoRunner,
  MAX(CASE WHEN game_situation = 'High pressure' THEN batting_average ELSE NULL END) AS BA_HighPressure
FROM performance_metrics
GROUP BY 1
HAVING MAX(CASE WHEN game_situation = 'No runner' THEN batting_average ELSE NULL END) >= 0.280
  AND MAX(CASE WHEN game_situation = 'High pressure' THEN batting_average ELSE NULL END) <= 0.200
ORDER BY BA_HighPressure ASC
LIMIT 15


-- RISP状況での長打力低下分析
WITH slugging_metrics AS (
  SELECT
    t1.batter AS batter_id,
    CONCAT(t2.first_name, ' ', t2.last_name) AS batter_name,
    -- runner situation
    CASE
      WHEN (on_2b != 0 OR on_3b != 0) THEN 'RISP' -- RISP
      WHEN (on_1b = 0 AND on_2b = 0 AND on_3b = 0) THEN 'No runner' -- no runner
      ELSE 'OTHER'
    END AS runner_situation,
    COUNT(*) AS plate_apperances,
    COUNTIF(t1.launch_speed IS NOT NULL) AS measured_pitches,
    -- slugging metrics
    AVG(iso_value) AS avg_iso,
    AVG(launch_speed) AS avg_launch_speed,
    AVG(launch_angle) AS avg_launch_angle,
    ROUND(SAFE_DIVIDE(COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95), 
      COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout'))), 3) AS hard_hit_rate
  FROM `tksm-dash-test-25.mlb_analytics_dash_25.statcast_2025` t1
  LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.dim_players` t2
    ON t1.batter = t2.mlb_id
  WHERE t1.events IS NOT NULL
    AND t1.batter IS NOT NULL
    AND t1.iso_value IS NOT NULL
  GROUP BY 1, 2, 3
  HAVING plate_apperances >= 80 AND measured_pitches >= 30
)
SELECT
  batter_name,
  MAX(CASE WHEN runner_situation = 'No runner' THEN avg_iso ELSE NULL END) AS iso_no_runner,
  MAX(CASE WHEN runner_situation = 'RISP' THEN avg_iso ELSE NULL END) AS iso_risp,
  MAX(CASE WHEN runner_situation = 'No runner' THEN hard_hit_rate ELSE NULL END) AS hhr_no_runner,
  MAX(CASE WHEN runner_situation = 'RISP' THEN hard_hit_rate ELSE NULL END) AS hhr_risp
FROM slugging_metrics
WHERE batter_name IS NOT NULL
  AND runner_situation IN ('No runner', 'RISP')
GROUP BY batter_name
HAVING 
  -- 必須: 両方の状況でデータが存在することを確認
  COUNT(CASE WHEN runner_situation = 'No runner' THEN 1 END) = 1 
  AND COUNT(CASE WHEN runner_situation = 'RISP' THEN 1 END) = 1 
  AND
  MAX(CASE WHEN runner_situation = 'No runner' THEN avg_iso ELSE NULL END) >= 0.200
  AND MAX(CASE WHEN runner_situation = 'RISP' THEN avg_iso ELSE NULL END) <= 0.150
ORDER BY iso_risp ASC
LIMIT 10
