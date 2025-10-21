from typing import Dict, List, Optional
from google.cloud import bigquery
import pandas as pd
import numpy as np

class StatisticalAnalysisService:
    """Service for performing statistical analysis on baseball data."""

    def __init__(self):
        self.client = bigquery.Client()
    
    def predict_winrate_from_ops(
            self, 
            team_ops: float,
            team_era: float,
            team_hrs_allowed: int
            ) -> Dict:
        """
        Predict win rate from OPS, ERA, and HRs Allowed.

        Args: 
            team_ops (float): The OPS (On-base Plus Slugging) value for the team.
            team_era (float): The earned run average for the team.
            team_hrs_allowed (int): The home runs allowed for the team.

        Returns:
            Dict: A dictionary containing the predicted win rate, expected wins per season, and model evaluation metrics.
        """
        # Predict with BigQuery ML
        query = f"""
        SELECT
            {team_ops} AS input_ops,
            {team_era} AS input_era,
            {team_hrs_allowed} AS input_hrs_allowed,
            predicted_winrate,
            ROUND(predicted_winrate * 162, 0) AS expected_wins_per_season
        FROM ML.PREDICT(
            MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`,
            (SELECT
                {team_ops} AS ops,
                {team_era} AS era,
                {team_hrs_allowed} AS hrs_allowed
            )
        )
        """

        try:
            result = self.client.query(query).to_dataframe()
            predicted_win_rate = result['predicted_winrate'].values[0]
            expected_wins = result['expected_wins_per_season'].values[0]

            # Get model evaluation metrics
            eval_query = """
            SELECT
                r2_score,
                mean_squared_error,
                mean_absolute_error
            FROM ML.EVALUATE(
                MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`
            )
            """
            eval_result = self.client.query(eval_query).to_dataframe()
            r2_score = eval_result['r2_score'].values[0]
            mse = eval_result['mean_squared_error'].values[0]
            mae = eval_result['mean_absolute_error'].values[0]

            return {
                "input_ops": team_ops,
                "input_era": team_era,
                "input_hrs_allowed": team_hrs_allowed,
                "predicted_win_rate": round(float(predicted_win_rate), 4),
                "expected_wins_per_season": int(expected_wins),
                "model_metrics": {
                    "r2_score": round(float(r2_score), 3),
                    "mse": round(float(mse), 3),
                    "mae": round(float(mae), 4)
                },
                "interpretation": self._interpret_prediction(team_ops, team_era, predicted_win_rate)
            }
        
        except Exception as e:
            return {
                "error": str(e),
                "message": "An error occurred while predicting win rate from OPS."
            }
    
    def _interpret_prediction(
            self, 
            ops: float,
            era: float,
            win_rate: float
        ) -> str:
        """Interpret the prediction results. 予測結果のビジネス的解釈を行う。"""

        wins = int(win_rate * 162)

        # Ranking by win rate
        if win_rate >= 0.6:
            rank = "Postseason favorite"
        elif win_rate >= 0.550:
            rank = "Postseason contender"
        elif win_rate >= 0.500:
            rank = "Playoff hopeful"
        else:
            rank = "Non-contender"
        
        return f"OPS {ops:.3f}、ERA {era:.3f}のチームは勝率{win_rate:.3f} (年間約{wins}勝)を記録し、{rank}と予測されます。"
    

    def get_ops_sensitivity_analysis(
        self,
        fixed_era: float = 4.00,
        fixed_hrs_allowed: int = 180
    ) -> List[Dict]:
        """
        Get sensitivity analysis for OPS (On-base Plus Slugging) values.
        OPSの変化が勝率に与える影響を分析する。

        Args:
            fixed_era: 固定するERA値（デフォルト: 4.00 = リーグ平均）
            fixed_hrs_allowed: 固定する被本塁打数（デフォルト: 180 = リーグ平均）

        Returns:
            OPS 0.650 ~ 0.850 の範囲での予測結果
        """

        ops_range = [round(x, 3) for x in np.arange(0.650, 0.851, 0.010)]

        ops_values = " UNION ALL ".join([
            f"SELECT {ops} AS ops, {fixed_era} AS era, {fixed_hrs_allowed} AS hrs_allowed"
            for ops in ops_range
        ])
        query = f"""
        SELECT
            ops as input_ops,
            predicted_winrate,
            ROUND(predicted_winrate * 162, 0) as expected_wins
        FROM ML.PREDICT(
            MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`,
            ({ops_values})
        )
        ORDER BY input_ops
        """

        result = self.client.query(query).to_dataframe()

        return [
            {
                "ops": round(row['input_ops'], 3),
                "win_rate": round(row['predicted_winrate'], 4),
                "expected_wins": int(row['expected_wins'])
            }
            for _, row in result.iterrows()
        ]
    
    def get_model_summary(self) -> Dict:
        """
        Get a summary of the model's performance and metadata.

        Returns:
            A dictionary containing the model's performance metrics and metadata
            such as R2 score, RMSE, MAE, regression coefficients, etc.
        """

        # Model evaluation metrics
        eval_query = """
        SELECT
            r2_score,
            mean_squared_error,
            mean_absolute_error
        FROM ML.EVALUATE(
            MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`
        )
        """
        eval_result = self.client.query(eval_query).to_dataframe()

        # Regression coefficients
        weights_query = """
        SELECT
            processed_input,
            weight
        FROM ML.WEIGHTS(
            MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`
        )
        WHERE processed_input != '__INTERCEPT__'
        """
        weights_result = self.client.query(weights_query).to_dataframe()

        # Intercept
        intercept_query = """
        SELECT
            weight AS intercept
        FROM ML.WEIGHTS(
            MODEL `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`
        )
        WHERE processed_input = '__INTERCEPT__'
        """
        intercept_result = self.client.query(intercept_query).to_dataframe()

        # processed_inputで係数を特定（インデックスではなく名前でアクセス）
        weights_dict = dict(zip(weights_result['processed_input'], weights_result['weight']))
        coefficient_ops = float(weights_dict.get('ops', 0.0))
        coefficient_era = float(weights_dict.get('era', 0.0))
        coefficient_hrs_allowed = float(weights_dict.get('hrs_allowed', 0.0))
        intercept = float(intercept_result['intercept'].values[0]) if len(intercept_result) > 0 else 0.0

        return {
            "model_type": "Linear Regression",
            "metrics": {
                "r2_score": round(float(eval_result['r2_score'].values[0]), 3),
                "rmse": round(np.sqrt(float(eval_result['mean_squared_error'].values[0])), 4),
                "mae": round(float(eval_result['mean_absolute_error'].values[0]), 4)
            },
            "regression_equation": {
                "coefficient_ops": round(coefficient_ops, 4),
                "coefficient_era": round(coefficient_era, 4),
                "coefficient_hrs_allowed": round(coefficient_hrs_allowed, 4),
                "intercept": round(intercept, 4),
                "formula": f"win_rate = {coefficient_ops:.4f} * team_ops + {coefficient_era:.4f} * team_era + {coefficient_hrs_allowed:.4f} * team_hrs_allowed + {intercept:.4f}"
            },
            "interpretation": {
                "ops_increase_0.01": f"OPSが0.01増加すると、勝率は{coefficient_ops*0.01:.4f}向上し、シーズン勝利数は約{coefficient_ops*0.01*162:.1f}勝増加します。",
                "era_increase_0.01": f"ERAが0.01増加すると、勝率は{coefficient_era*0.01:.4f}低下し、シーズン勝利数は約{coefficient_era*0.01*162:.1f}勝減少します。",
                "hrs_allowed_increase_0.01": f"HRs Allowedが0.01増加すると、勝率は{coefficient_hrs_allowed*0.01:.4f}低下し、シーズン勝利数は約{coefficient_hrs_allowed*0.01*162:.1f}勝減少します。",
                "example": f"OPSが0.750のとき、勝率は{coefficient_ops*0.750 + intercept:.3f}、シーズン勝利数は約{int((coefficient_ops*0.750 + intercept)*162)}勝です。"
            }
        }
        
