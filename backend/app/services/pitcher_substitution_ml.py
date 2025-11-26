import pandas as pd
import numpy as np
from google.cloud import bigquery
import joblib
import os
from backend.app.config.settings import get_settings


settings = get_settings()


class PitcherSubstitutionMLService:
    def __init__(self):
        self.client = bigquery.Client()

        # 1. Load the pre-trained ML model, scaler, and features
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        self.model = joblib.load(os.path.join(model_dir, 'pitcher_fatigue_model.pkl'))
        self.scaler = joblib.load(os.path.join(model_dir, 'pitcher_fatigue_scaler.pkl'))
        self.features = joblib.load(os.path.join(model_dir, 'pitcher_fatigue_features.pkl'))
        self.threshold = 0.3 # Recall is prioritized over precision since we want to catch as many fatigue cases as possible
    
    def predict_substitution(self, pitcher_name: str, season: int = 2025):
        """
        特定投手のイニング別交代推奨度を予測
        """
        # 名前フォーマット変換: "Yoshinobu Yamamoto" → "Yamamoto, Yoshinobu"
        if ',' not in pitcher_name and ' ' in pitcher_name:
            parts = pitcher_name.strip().split()
            if len(parts) == 2:
                pitcher_name = f"{parts[1]}, {parts[0]}"

        # 2. Fetch data from BigQuery
        query = f"""
        WITH pitcher_games AS (
            SELECT DISTINCT game_pk, pitcher_id
            FROM `{settings.get_table_full_name('view_pitching_counts_by_inning_2025')}`
            WHERE pitcher_name = '{pitcher_name}'
        )
        SELECT
            counts.pitcher_name,
            counts.pitcher_id,
            counts.game_pk,
            counts.inning,
            counts.total_pitches,
            counts.strike_rate,
            counts.ball_rate,
            quality.avg_release_speed as fastball_speed,
            AVG(perf.ops_against) as ops_against
        FROM `{settings.get_table_full_name('view_pitching_counts_by_inning_2025')}` as counts
        INNER JOIN pitcher_games pg
            ON counts.game_pk = pg.game_pk
            AND counts.pitcher_id = pg.pitcher_id
        LEFT JOIN `{settings.get_table_full_name('view_pitch_type_quality_by_inning_2025')}` as quality
            ON counts.pitcher_id = quality.pitcher_id
            AND counts.game_pk = quality.game_pk
            AND counts.inning = quality.inning
            AND quality.pitch_name IN ('4-Seam Fastball', 'Fastball')
        LEFT JOIN `{settings.get_table_full_name('tbl_pitching_performance_by_inning')}` as perf
            ON counts.pitcher_id = perf.pitcher_id
            AND counts.inning = perf.inning
            AND perf.game_year = {season}
        WHERE counts.pitcher_name = '{pitcher_name}'
          AND quality.avg_release_speed IS NOT NULL
        GROUP BY counts.pitcher_name, counts.pitcher_id, counts.game_pk, counts.inning,
                 counts.total_pitches, counts.strike_rate, counts.ball_rate, quality.avg_release_speed
        ORDER BY counts.game_pk, counts.inning
        """

        try:
            print(f"Querying for: {pitcher_name}, season: {season}")
            df = self.client.query(query).to_dataframe()
            print(f"Query returned {len(df)} rows")

            if df.empty:
                # 投手名の存在確認
                check_query = f"""
                SELECT DISTINCT pitcher_name
                FROM `{settings.get_table_full_name('tbl_pitching_performance_by_inning')}`
                WHERE game_year = {season}
                AND pitcher_name LIKE '%{pitcher_name.split()[0]}%'
                LIMIT 10
                """
                suggestions = self.client.query(check_query).to_dataframe()
                suggestion_list = suggestions['pitcher_name'].tolist() if not suggestions.empty else []

                return {
                    "error": True,
                    "message": f"No data found for {pitcher_name}",
                    "suggestions": suggestion_list
                }
            # 3. Calculate fatigue indicators
            df = self._calculate_fatigue_indicators(df)

            # Debug: Print feature values
            print("\n=== Feature values for prediction ===")
            print(df[['inning', 'cumulative_pitches', 'speed_drop', 'ops_increase', 'ops_against', 'fastball_speed']].head(8))
            print(f"\nBaseline OPS: {df['ops_against'].iloc[0] if len(df) > 0 else 'N/A'}")

            # 4. Predict substitution recommendation using the ML model
            predictions = []
            for idx, row in df.iterrows():
                # Skip the last inning as we cannot predict beyond it
                if idx == len(df) - 1:
                    continue

                # 4-1: Prepare features
                feature_values = [
                    row['inning'],
                    row['speed_drop'],
                    row['cumulative_pitches'],
                    row['strike_rate_drop'],
                    row['ops_increase'],
                    row['fastball_speed'],
                    row['strike_rate'],
                    row['ball_rate']
                ]

                # 4-2: Scale features
                features_scaled = self.scaler.transform([feature_values])

                # 4-3: Predict probability
                # predict_proba: [疲労なし確率, 疲労あり確率]
                # [0][1]で「疲労あり確率」を取得
                fatigue_proba = self.model.predict_proba(features_scaled)[0][1]

                # 4-4: Determine recommendation
                # 疲労確率が30%より大きいなら交代推奨
                should_substitute = fatigue_proba > self.threshold

                predictions.append({
                    "inning": int(row['inning']),
                    "fatigue_probability": round(float(fatigue_proba), 3),
                    "recommendation": "SUBSTITUTE" if should_substitute else "CONTINUE",
                    "fastball_speed": round(float(row['fastball_speed']), 1),
                    "cumulative_pitches": int(row['cumulative_pitches']),
                    "ops_against": round(float(row['ops_against']), 3)
                })
            
            return {
                "error": False,
                "pitcher_name": pitcher_name,
                "season": season,
                "threshold": self.threshold,
                "predictions": predictions
            }
        
        except Exception as e:
            return {"error": True, "message": str(e)}
    

    def _calculate_fatigue_indicators(self, df):
        """
        【疲労指標を計算】
        notebookのStep 2と同じロジック
        """
        # cumulative_pitchesは0で固定（スケール問題のため使用しない）
        df['cumulative_pitches'] = 0

        # 初回ベースライン（全ゲームの1回の平均）
        baseline_df = df[df['inning'] == 1].agg({
            'fastball_speed': 'mean',
            'ops_against': 'mean',
            'strike_rate': 'mean'
        })

        df['baseline_speed'] = baseline_df['fastball_speed']
        df['baseline_ops'] = baseline_df['ops_against']
        df['baseline_strike_rate'] = baseline_df['strike_rate']

        # 疲労指標
        df['speed_drop'] = df['baseline_speed'] - df['fastball_speed']
        df['ops_increase'] = df['ops_against'] - df['baseline_ops']
        df['strike_rate_drop'] = df['baseline_strike_rate'] - df['strike_rate']

        # イニング別に集約（複数ゲームの同じイニングを平均）
        df_agg = df.groupby('inning').agg({
            'pitcher_name': 'first',
            'pitcher_id': 'first',
            'fastball_speed': 'mean',
            'speed_drop': 'mean',
            'cumulative_pitches': 'mean',
            'ops_against': 'mean',
            'strike_rate': 'mean',
            'ball_rate': 'mean',
            'ops_increase': 'mean',
            'strike_rate_drop': 'mean'
        }).reset_index()

        # NaN値を0に置換
        df_agg = df_agg.fillna(0)

        return df_agg