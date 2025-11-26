"""
投手Whiff率予測サービス
LightGBMモデルを使用して投手の状況別whiff率を予測
"""
import os
import logging
import pandas as pd
import lightgbm as lgb
from google.cloud import bigquery
from typing import List, Dict, Optional
from backend.app.services.base import get_bq_client
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PitcherPredictionService:
    """投手whiff率予測サービス"""

    def __init__(self):
        self.client = get_bq_client()
        self.model = None
        self.train_features = None
        self._load_model()

    def _load_model(self):
        """LightGBMモデルとトレーニング特徴量を読み込み"""
        try:
            # モデルファイルのパス
            model_path = os.path.join(
                os.path.dirname(__file__),
                '..', '..', 'models', 'lightgbm_whiff.txt'
            )

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")

            self.model = lgb.Booster(model_file=model_path)
            logger.info(f"✅ LightGBM model loaded from {model_path}")

            # トレーニング時の特徴量リストを読み込み
            features_path = os.path.join(
                os.path.dirname(__file__),
                '..', '..', 'models', 'train_features.txt'
            )

            if os.path.exists(features_path):
                with open(features_path, 'r') as f:
                    self.train_features = [line.strip() for line in f.readlines()]
                logger.info(f"✅ Training features loaded: {len(self.train_features)} features")
            else:
                logger.warning(f"⚠️ Training features file not found: {features_path}")

        except Exception as e:
            logger.error(f"❌ Failed to load model: {str(e)}")
            raise

    async def predict_whiff(
        self,
        pitcher_name: str,
        batter_stand: Optional[str] = None,
        inning: Optional[int] = None,
        order_thru: Optional[int] = None,
        runner_situation: Optional[str] = None,
        batter_level: Optional[str] = None,
        count_situation: Optional[str] = None,
        pitch_count_group: Optional[str] = None
    ) -> Dict:
        """
        指定された状況で投手の球種別whiff率を予測

        Returns:
            predictions: 球種別の予測whiff率リスト
            recommendations: 攻略ポイント
        """
        try:
            # BigQueryから投手データを取得
            query = f"""
            SELECT
              pitcher_name,
              batter_stand,
              inning,
              order_thru,
              runner_situation,
              batter_level,
              pitch_name,
              count_situation,
              pitch_count_group,

              AVG(release_speed) as release_speed,
              AVG(release_spin_rate) as release_spin_rate,
              AVG(pfx_x) as pfx_x,
              AVG(pfx_z) as pfx_z,
              AVG(release_extension) as release_extension,

              AVG(avg_speed_vs_stand) as avg_speed_vs_stand,
              AVG(avg_spin_vs_stand) as avg_spin_vs_stand,
              AVG(hard_hit_rate_vs_stand) as hard_hit_rate_vs_stand,
              AVG(avg_pfx_x_vs_stand) as avg_pfx_x_vs_stand,
              AVG(avg_pfx_z_vs_stand) as avg_pfx_z_vs_stand,
              AVG(zone_rate_vs_stand) as zone_rate_vs_stand,
              AVG(woba_against_vs_stand) as woba_against_vs_stand,

              AVG(avg_speed_by_inning) as avg_speed_by_inning,
              AVG(avg_spin_by_inning) as avg_spin_by_inning,
              AVG(hard_hit_rate_by_inning) as hard_hit_rate_by_inning,
              AVG(avg_pfx_x_by_inning) as avg_pfx_x_by_inning,
              AVG(avg_pfx_z_by_inning) as avg_pfx_z_by_inning,
              AVG(zone_rate_by_inning) as zone_rate_by_inning,
              AVG(woba_against_by_inning) as woba_against_by_inning,

              AVG(avg_speed_by_order) as avg_speed_by_order,
              AVG(avg_spin_by_order) as avg_spin_by_order,
              AVG(hard_hit_rate_by_order) as hard_hit_rate_by_order,
              AVG(avg_pfx_x_by_order) as avg_pfx_x_by_order,
              AVG(avg_pfx_z_by_order) as avg_pfx_z_by_order,
              AVG(zone_rate_by_order) as zone_rate_by_order,
              AVG(woba_against_by_order) as woba_against_by_order,

              AVG(avg_speed_by_runner) as avg_speed_by_runner,
              AVG(avg_spin_by_runner) as avg_spin_by_runner,
              AVG(hard_hit_rate_by_runner) as hard_hit_rate_by_runner,
              AVG(avg_pfx_x_by_runner) as avg_pfx_x_by_runner,
              AVG(avg_pfx_z_by_runner) as avg_pfx_z_by_runner,
              AVG(zone_rate_by_runner) as zone_rate_by_runner,
              AVG(woba_against_by_runner) as woba_against_by_runner,

              AVG(avg_speed_vs_batter_level) as avg_speed_vs_batter_level,
              AVG(avg_spin_vs_batter_level) as avg_spin_vs_batter_level,
              AVG(hard_hit_rate_vs_batter_level) as hard_hit_rate_vs_batter_level,
              AVG(avg_pfx_x_vs_batter_level) as avg_pfx_x_vs_batter_level,
              AVG(avg_pfx_z_vs_batter_level) as avg_pfx_z_vs_batter_level,
              AVG(zone_rate_vs_batter_level) as zone_rate_vs_batter_level,
              AVG(woba_against_vs_batter_level) as woba_against_vs_batter_level,

              AVG(avg_speed_by_count) as avg_speed_by_count,
              AVG(avg_spin_by_count) as avg_spin_by_count,
              AVG(hard_hit_rate_by_count) as hard_hit_rate_by_count,
              AVG(avg_pfx_x_by_count) as avg_pfx_x_by_count,
              AVG(avg_pfx_z_by_count) as avg_pfx_z_by_count,
              AVG(zone_rate_by_count) as zone_rate_by_count,
              AVG(woba_against_by_count) as woba_against_by_count,

              AVG(avg_speed_by_pitch_count_group) as avg_speed_by_pitch_count_group,
              AVG(avg_spin_by_pitch_count_group) as avg_spin_by_pitch_count_group,
              AVG(hard_hit_rate_by_pitch_count_group) as hard_hit_rate_by_pitch_count_group,
              AVG(avg_pfx_x_by_pitch_count_group) as avg_pfx_x_by_pitch_count_group,
              AVG(avg_pfx_z_by_pitch_count_group) as avg_pfx_z_by_pitch_count_group,
              AVG(zone_rate_by_pitch_count_group) as zone_rate_by_pitch_count_group,
              AVG(woba_against_by_pitch_count_group) as woba_against_by_pitch_count_group,

              AVG(CAST(is_whiff AS FLOAT64)) as actual_whiff_rate,
              COUNT(*) as pitch_count

            FROM `{settings.get_table_full_name('pitcher_batter_features_integrated')}`
            WHERE pitcher_name = '{pitcher_name}'
              {f"AND batter_stand = '{batter_stand}'" if batter_stand else ""}
              {f"AND inning = {inning}" if inning else ""}
              {f"AND order_thru = {order_thru}" if order_thru else ""}
              {f"AND runner_situation = '{runner_situation}'" if runner_situation else ""}
              {f"AND batter_level = '{batter_level}'" if batter_level else ""}
              {f"AND count_situation = '{count_situation}'" if count_situation else ""}
              {f"AND pitch_count_group = '{pitch_count_group}'" if pitch_count_group else ""}
              AND is_whiff IS NOT NULL
            GROUP BY
              pitcher_name, batter_stand, inning, order_thru,
              runner_situation, batter_level, pitch_name, count_situation, pitch_count_group
            HAVING COUNT(*) >= 5
            """

            df_pitcher = self.client.query(query).to_dataframe()

            if df_pitcher.empty:
                raise ValueError(f"指定された状況のデータが見つかりません: {pitcher_name}")

            # 特徴量エンコーディング
            categorical_features = [
                'batter_stand', 'inning', 'order_thru',
                'runner_situation', 'batter_level', 'pitch_name',
                'count_situation', 'pitch_count_group'
            ]

            numerical_features = [col for col in df_pitcher.columns
                                if col not in categorical_features + ['pitcher_name', 'actual_whiff_rate', 'pitch_count']]

            df_encoded = pd.get_dummies(
                df_pitcher[categorical_features + numerical_features],
                columns=categorical_features,
                drop_first=True
            )

            # トレーニング時の特徴量と合わせる
            if self.train_features:
                for col in self.train_features:
                    if col not in df_encoded.columns:
                        df_encoded[col] = 0
                df_encoded = df_encoded[self.train_features]

            # 予測実行
            predicted_whiff_rate = self.model.predict(df_encoded)
            df_pitcher['predicted_whiff_rate'] = predicted_whiff_rate

            # 球種別の実際のwhiff率を取得
            query_actual = f"""
            SELECT
              pitch_name,
              AVG(CAST(is_whiff AS FLOAT64)) as actual_whiff_rate,
              COUNT(*) as pitch_count
            FROM `{settings.get_table_full_name('pitcher_batter_features_integrated')}`
            WHERE pitcher_name = '{pitcher_name}'
              AND is_whiff IS NOT NULL
            GROUP BY pitch_name
            """
            df_actual = self.client.query(query_actual).to_dataframe()

            # 球種ごとに予測値を平均化（複数の条件がある場合）
            df_pitcher_agg = df_pitcher.groupby('pitch_name').agg({
                'predicted_whiff_rate': 'mean'
            }).reset_index()

            # 結果を整形
            predictions = []
            for _, row in df_pitcher_agg.iterrows():
                pitch_name = row['pitch_name']
                actual_row = df_actual[df_actual['pitch_name'] == pitch_name]

                predictions.append({
                    "pitch_name": pitch_name,
                    "predicted_whiff_rate": float(row['predicted_whiff_rate']),
                    "actual_whiff_rate": float(actual_row['actual_whiff_rate'].iloc[0]) if not actual_row.empty else None,
                    "pitch_count": int(actual_row['pitch_count'].iloc[0]) if not actual_row.empty else None
                })

            # 予測値でソート（低い順 = 狙い目）
            predictions = sorted(predictions, key=lambda x: x['predicted_whiff_rate'])

            # 推奨事項を生成
            recommendations = self._generate_recommendations(predictions, count_situation)

            return {
                "pitcher_name": pitcher_name,
                "situation": {
                    "batter_stand": batter_stand,
                    "inning": inning,
                    "order_thru": order_thru,
                    "runner_situation": runner_situation,
                    "batter_level": batter_level,
                    "count_situation": count_situation,
                    "pitch_count_group": pitch_count_group
                },
                "predictions": predictions,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"❌ Prediction error: {str(e)}")
            raise

    def _generate_recommendations(self, predictions: List[Dict], count_situation: str) -> List[str]:
        """予測結果から攻略ポイントを生成"""
        recommendations = []

        if not predictions:
            return ["データ不足のため推奨事項を生成できません"]

        # 最も狙い目の球種
        easiest = predictions[0]
        recommendations.append(
            f"🎯 最も狙い目: {easiest['pitch_name']} (whiff率 {easiest['predicted_whiff_rate']:.1%})"
        )

        # 最も危険な球種
        hardest = predictions[-1]
        recommendations.append(
            f"⚠️ 警戒すべき: {hardest['pitch_name']} (whiff率 {hardest['predicted_whiff_rate']:.1%})"
        )

        # カウント状況に応じたアドバイス
        if count_situation == "pitcher_advantage":
            recommendations.append("💡 投手有利カウント: 決め球に警戒、ゾーン外の誘い球を見送れ")
        elif count_situation == "batter_advantage":
            recommendations.append("💡 打者有利カウント: ストライク先行で来るため積極的に狙え")

        return recommendations

    async def get_available_pitchers(self) -> List[str]:
        """予測可能な投手一覧を取得"""
        try:
            query = f"""
            SELECT DISTINCT pitcher_name
            FROM `{settings.get_table_full_name('pitcher_batter_features_integrated')}`
            WHERE pitcher_name IS NOT NULL
            ORDER BY pitcher_name
            """
            df = self.client.query(query).to_dataframe()
            return df['pitcher_name'].tolist()
        except Exception as e:
            logger.error(f"❌ Failed to get pitchers: {str(e)}")
            raise
