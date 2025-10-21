-- Build model
CREATE OR REPLACE MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops`
OPTIONS(
    model_type='linear_reg',
    input_label_cols=['winrate'],
    data_split_method='random',
    data_split_eval_fraction=0.2
) AS
SELECT
    ops,
    winrate
FROM `tksm-dash-test-25.mlb_analytics_dash_25.team_ops_winrate`
WHERE winrate IS NOT NULL

-- Build model multivariate
CREATE OR REPLACE MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`
OPTIONS(
    model_type='linear_reg',
    input_label_cols=['winrate'],
    data_split_method='random',
    data_split_eval_fraction=0.2
) AS
SELECT
    ops,
    era,
    hrs_allowed,
    winrate
FROM `tksm-dash-test-25.mlb_analytics_dash_25.team_ops_winrate_multivariate`
WHERE winrate IS NOT NULL

-- Evaluate model
SELECT
    mean_squared_error,
    r2_score,
    mean_absolute_error
FROM ML.EVALUATE(
    MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops`
)

-- Predict winrate
SELECT
    ops AS input_ops,
    predicted_winrate,
    ROUND(predicted_winrate * 162, 0) AS expected_wins_per_season
FROM ML.PREDICT(
    MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops`,
    (
        SELECT 0.700 AS ops UNION ALL
        SELECT 0.750 as ops UNION ALL
        SELECT 0.800 as ops UNION ALL
        SELECT 0.850 as ops
    )
)
ORDER BY input_ops

-- Regression coefficients
SELECT
    processed_input,
    weight
FROM ML.WEIGHTS(
    MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops`
)
ORDER BY processed_input