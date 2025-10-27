import pandas as pd
import numpy as np
from google.cloud import bigquery


class PitcherFatigueService:
    def __init__(self):
        self.client = bigquery.Client()

    def get_pitcher_fatigue_analysis(self, pitcher_name: str, season: int = 2025):
        """Fetch and analyze pitcher fatigue data from BigQuery."""
        # 名前フォーマット変換: "Yoshinobu Yamamoto" → "Yamamoto, Yoshinobu"
        if ',' not in pitcher_name and ' ' in pitcher_name:
            parts = pitcher_name.strip().split()
            if len(parts) == 2:
                pitcher_name = f"{parts[1]}, {parts[0]}"

        query = f"""
        WITH pitcher_games AS (
            SELECT DISTINCT game_pk, pitcher_id
            FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_pitching_counts_by_inning_2025`
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
            quality.avg_spin_rate as fastball_spin,
            AVG(perf.ops_against) as ops_against,
            AVG(perf.batting_average_against) as batting_average_against
        FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_pitching_counts_by_inning_2025` as counts
        INNER JOIN pitcher_games pg
            ON counts.game_pk = pg.game_pk
            AND counts.pitcher_id = pg.pitcher_id
        LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.view_pitch_type_quality_by_inning_2025` as quality
            ON counts.pitcher_id = quality.pitcher_id
            AND counts.game_pk = quality.game_pk
            AND counts.inning = quality.inning
            AND quality.pitch_name IN ('4-Seam Fastball', 'Fastball')
        LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.tbl_pitching_performance_by_inning` as perf
            ON counts.pitcher_id = perf.pitcher_id
            AND counts.inning = perf.inning
            AND perf.game_year = {season}
        WHERE counts.pitcher_name = '{pitcher_name}'
          AND quality.avg_release_speed IS NOT NULL
        GROUP BY counts.pitcher_name, counts.pitcher_id, counts.game_pk, counts.inning,
                 counts.total_pitches, counts.strike_rate, counts.ball_rate,
                 quality.avg_release_speed, quality.avg_spin_rate
        ORDER BY counts.game_pk, counts.inning
        """

        try:
            df = self.client.query(query).to_dataframe()

            if df.empty:
                # 投手名の存在確認
                check_query = f"""
                SELECT DISTINCT pitcher_name
                FROM `tksm-dash-test-25.mlb_analytics_dash_25.tbl_pitching_performance_by_inning`
                WHERE game_year = {season}
                AND pitcher_name LIKE '%{pitcher_name.split()[0]}%'
                LIMIT 10
                """
                suggestions = self.client.query(check_query).to_dataframe()
                suggestion_list = suggestions['pitcher_name'].tolist() if not suggestions.empty else []

                return {
                    "error": True,
                    "message": f"No data found for pitcher {pitcher_name} in season {season}.",
                    "suggestions": suggestion_list
                }

            # Fatigue metric calculations
            df = self._calculate_fatigue_indicators(df)

            # response
            innings_data = []
            for _, row in df.iterrows():
                innings_data.append({
                    "inning": int(row['inning']),
                    "fastball_speed": round(float(row['fastball_speed']), 2) if pd.notna(row['fastball_speed']) else None,
                    "speed_drop": round(float(row['speed_drop']), 2) if pd.notna(row['speed_drop']) else None,
                    "cumulative_pitches": int(row['cumulative_pitches']),
                    "ops_against": round(float(row['ops_against']), 3),
                    "strike_rate": round(float(row['strike_rate']), 3),
                    "fatigue_risk": "high" if row.get('speed_drop', 0) > 0.5 else "moderate" if row.get('speed_drop', 0) > 0.3 else "low"
                })
            
            return {
                "error": False,
                "pitcher_name": pitcher_name,
                "season": season,
                "innings": innings_data
            }

        except Exception as e:
            return {"error": True, "message": str(e)}
    

    def _calculate_fatigue_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fatigue indicators for the pitcher data."""
        # cumulative_pitchesは削除（使用しない）
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
            'ops_increase': 'mean',
            'strike_rate_drop': 'mean'
        }).reset_index()

        # NaN値を0に置換
        df_agg = df_agg.fillna(0)

        return df_agg
    
    def get_league_average_fatigue(self, season: int = 2025):
        """Fetch league average fatigue metrics."""
        query = f"""
        SELECT
            counts.pitcher_id,
            counts.game_pk,
            counts.inning,
            counts.total_pitches,
            counts.strike_rate,
            quality.avg_release_speed as fastball_speed,
            perf.ops_against
        FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_pitching_counts_by_inning_2025` as counts
        LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.view_pitch_type_quality_by_inning_2025` as quality
            ON counts.pitcher_id = quality.pitcher_id
            AND counts.game_pk = quality.game_pk
            AND counts.inning = quality.inning
            AND quality.pitch_name IN ('4-Seam Fastball', 'Fastball')
        LEFT JOIN `tksm-dash-test-25.mlb_analytics_dash_25.tbl_pitching_performance_by_inning` as perf
            ON counts.pitcher_id = perf.pitcher_id
            AND counts.inning = perf.inning
            AND perf.game_year = {season}
        WHERE quality.avg_release_speed IS NOT NULL
        """
        
        try:
            df = self.client.query(query).to_dataframe()

            if df.empty:
                return {"error": True, "message": f"No league data found for season {season}."}
            
            # Only starting pitchers
            starters = df[df['inning'] == 1]['pitcher_id'].unique()
            df_starters = df[df['pitcher_id'].isin(starters)]

            # Include only innings from 1 to 8
            df_starters = df_starters[df_starters['inning'] <= 8]

            # Calculate fatigue indicators for all pitchers
            all_pitchers = []
            for pitcher_id in starters:
                pitcher_df = df_starters[df_starters['pitcher_id'] == pitcher_id]
                if len(pitcher_df) > 0:
                    pitcher_df = self._calculate_fatigue_indicators(pitcher_df)
                    all_pitchers.append(pitcher_df)
            
            all_data = pd.concat(all_pitchers, ignore_index=True)

            # metrtic by inning
            inning_avg = all_data.groupby('inning').agg({
                'speed_drop': 'mean',
                'ops_increase': 'mean',
                'strike_rate_drop': 'mean',
                'cumulative_pitches': 'mean'
            }).reset_index()

            inning_stats = []
            for _, row in inning_avg.iterrows():
                inning_stats.append({
                    "inning": int(row['inning']),
                    "avg_speed_drop": round(float(row['speed_drop']), 3),
                    "avg_ops_increase": round(float(row['ops_increase']), 3),
                    "avg_strike_rate_drop": round(float(row['strike_rate_drop']), 3),
                    "avg_cumulative_pitches": round(float(row['cumulative_pitches']), 1)
                })
            
            return {
                "error": False,
                "season": season,
                "inning_stats": inning_stats
            }
        
        except Exception as e:
            return {"error": True, "message": str(e)}
