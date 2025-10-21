WITH players_ba AS (
    SELECT
        batter_name,
        p_throws,
        -- BA
        ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')), -- total hits
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf') -- total at bats
        )), 3
        ) AS avg_by_p_throws,
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.tbl_statcast_2021_2025_master`
    WHERE events IS NOT NULL
        AND game_type = "R"
        AND batter_name IS NOT NULL
        AND p_throws IN ('R', 'L')
    GROUP BY p_throws, batter_name
    HAVING COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf')) >= 200
)
SELECT
    t1.batter_name,
    -- BA against RHP
    MAX(CASE WHEN t1.p_throws = 'R' THEN t1.avg_by_p_throws ELSE NULL END) AS avg_rhp,

    -- BA against LHP
    MAX(CASE WHEN t1.p_throws = 'L' THEN t1.avg_by_p_throws ELSE NULL END) AS avg_lhp,

    -- diff by p_throw types
    (MAX(CASE WHEN t1.p_throws = 'R' THEN t1.avg_by_p_throws ELSE NULL END) - 
    MAX(CASE WHEN t1.p_throws = 'L' THEN t1.avg_by_p_throws ELSE NULL END)) AS diff_vs_p_throws
FROM players_ba t1
GROUP BY t1.batter_name
HAVING diff_vs_p_throws IS NOT NULL
ORDER BY diff_vs_p_throws DESC