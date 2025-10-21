-- Players KPIs
CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.executive_kpis` AS
SELECT
  season,
  name,
  team,

  -- Core Metrics
  ops,
  avg,
  obp,
  slg,
  -- RISP
  batting_average_at_risp,

  war,
  ab AS at_bats,
  pa AS plate_appearances,
  h AS hits,
  hr AS home_runs,
  rbi,
  sb AS stolen_bases
FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_with_risp`
WHERE season >= 2024
    AND pa >= 100
ORDER BY season DESC

-- Weekly performance trend
CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.executive_kpis_weekly` AS
WITH weekly_stats AS (
    SELECT
        game_year AS season,
        batter_name,
        -- Weekly stats
        EXTRACT(WEEK FROM game_date) AS week_number,
        DATE_TRUNC(game_date, WEEK) AS week_start_date,
        -- BA
        ROUND(SAFE_DIVIDE(
            COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits
            COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf') -- total at bats
        )), 3
        ) AS weekly_avg,
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
        ), 3) AS weekly_ops,
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')) AS weekly_hits,
        COUNTIF(events = 'home_run') AS weekly_homeruns,
        -- Number of BBs
        COUNTIF(events in ('walk', 'intent_walk')) AS weekly_bbs,
        -- Number of at bats
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) AS weekly_abs,
        COUNT(DISTINCT game_pk) AS games_played
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.tbl_statcast_2021_2025_master`
    WHERE game_year = 2025
        AND events IS NOT NULL
        AND game_date IS NOT NULL
        AND batter_name IS NOT NULL
    GROUP BY season, batter_name, week_number, week_start_date
)
SELECT
    season,
    batter_name,
    week_number,
    week_start_date,
    weekly_avg,
    weekly_ops,
    weekly_hits,
    weekly_homeruns,
    weekly_bbs,
    weekly_abs,
    games_played,
    -- WoW (Week over Week) Metrics
    weekly_ops - LAG(weekly_ops) OVER(PARTITION BY batter_name, season ORDER BY week_number) AS wow_ops
FROM weekly_stats
ORDER BY season, week_number

-- Top Performers Dashbaord
CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.executive_kpis_top_performers` AS
SELECT
    season,
    name,
    team,
    ops,
    avg,
    batting_average_at_risp,
    hr,
    rbi,
    war,
    wrcplus,
    -- Ranking
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY ops DESC) AS ops_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY avg DESC) AS avg_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY batting_average_at_risp DESC) AS risp_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY hr DESC) AS hr_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY rbi DESC) AS rbi_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY war DESC) AS war_rank,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY wrcplus DESC) AS wrcplus_rank,
    CURRENT_TIMESTAMP() AS last_updated
FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_with_risp`
WHERE season >= 2024
    AND pa >= 350
QUALIFY ops_rank <= 20 OR risp_rank <= 20 OR war_rank <= 20
ORDER BY season DESC, war DESC

