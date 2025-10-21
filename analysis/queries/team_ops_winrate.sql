CREATE OR REPLACE VIEW `tksm-dash-test-25.mlb_analytics_dash_25.team_ops_winrate_multivariate` AS
SELECT
    t1.season,
    t1.team,
    t1.ops,
    t1.r,
    t1.avg,
    t1.sb,
    t1.so,
    t2.era,
    t2.whip,
    t2.hr AS hrs_allowed,
    t2.w / (t2.w + t2.l) AS winrate
FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_team_batting_stats_master` t1
JOIN `tksm-dash-test-25.mlb_analytics_dash_25.fact_team_pitching_stats_master` t2 USING(season, team)
ORDER BY t1.season DESC, t1.ops DESC