"""
Stuff+ / Pitching+ モデルの学習・ランキング計算・Model Registry 登録スクリプト

Usage:
    python scripts/train_stuff_plus.py --season 2025
    python scripts/train_stuff_plus.py --season 2025 --min-pitches 50
"""

import sys
import os
import argparse
import json
import tempfile
import logging
from pathlib import Path
from typing import Tuple, Dict, List, Any

import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from google.cloud import bigquery, storage
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import pearsonr, spearmanr
from dotenv import load_dotenv

# プロジェクトルートをパスに追加（backend.app.* のインポートを解決）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.model_registry_service import ModelRegistryService, ModelVersion

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# 特徴量定義（Stuff+ と Pitching+ の差は制球関連特徴量）
# ============================================================
STUFF_FEATURES = [
    'release_speed', 'release_spin_rate', 'spin_axis',
    'pfx_x', 'pfx_z', 'release_extension',
    'release_pos_x', 'release_pos_z',
    'api_break_z_with_gravity', 'api_break_x_arm',
    'arm_angle',
]
# plate_z_norm: 打者ストライクゾーンで正規化した plate_z（P5 Command Precision 由来）
PITCHING_FEATURES = STUFF_FEATURES + ['plate_x', 'plate_z_norm']

# Pitching++ Pitching+ + tunnel + count + zone_distance
PITCHING_PP_FEATURES = STUFF_FEATURES + [
    # Command
    'plate_x', 'plate_z_norm', 'zone_distance',
    # Count
    'balls', 'strikes',
    # Tunnel
    'release_diff', 'speed_diff', 'prev_pfx_z',
]

# モデルごとの One-Hot Encoding 対象カテゴリカルカラム
CATEGORICAL_COLUMNS = {
    "stuff_plus": ["pitch_type"],
    "pitching_plus": ["pitch_type"],
    "pitching_plus_plus": ["pitch_type", "prev_pitch_type"],
}

# XGBoost ハイパーパラメータ
XGB_PARAMS = {
    'n_estimators': 500,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'early_stopping_rounds': 50,
}

QUERY_TEMPLATE = """
WITH sequenced AS (
    SELECT
        s.pitcher,
        s.pitch_type,
        s.pitch_name,
        s.release_speed,
        s.release_spin_rate,
        s.spin_axis,
        s.pfx_x,
        s.pfx_z,
        s.release_extension,
        s.release_pos_x,
        s.release_pos_z,
        s.plate_x,
        s.plate_z,
        s.sz_top,
        s.sz_bot,
        s.api_break_z_with_gravity,
        s.api_break_x_arm,
        s.arm_angle,
        s.delta_pitcher_run_exp,
        s.game_year,
        s.p_throws,
        s.stand,
        s.balls,
        s.strikes,
        -- LAG: 同一打席内の前球データ（Pitching++ 用）
        LAG(s.release_pos_x) OVER(PARTITION BY s.game_pk, s.at_bat_number ORDER BY s.pitch_number) AS prev_release_pos_x,
        LAG(s.release_pos_z) OVER(PARTITION BY s.game_pk, s.at_bat_number ORDER BY s.pitch_number) AS prev_release_pos_z,
        LAG(s.release_speed) OVER(PARTITION BY s.game_pk, s.at_bat_number ORDER BY s.pitch_number) AS prev_release_speed,
        LAG(s.pfx_z) OVER(PARTITION BY s.game_pk, s.at_bat_number ORDER BY s.pitch_number) AS prev_pfx_z,
        LAG(s.pitch_type) OVER(PARTITION BY s.game_pk, s.at_bat_number ORDER BY s.pitch_number) AS prev_pitch_type
    FROM `{project}.{dataset}.statcast_master` s
    WHERE s.game_year = {season}
)
SELECT
    sq.pitcher,
    p.full_name AS player_name,
    p.primary_position,
    t.team_name,
    t.league,
    sq.pitch_type,
    sq.pitch_name,
    sq.release_speed,
    sq.release_spin_rate,
    sq.spin_axis,
    sq.pfx_x,
    sq.pfx_z,
    sq.release_extension,
    sq.release_pos_x,
    sq.release_pos_z,
    sq.plate_x,
    sq.plate_z,
    sq.sz_top,
    sq.sz_bot,
    sq.api_break_z_with_gravity,
    sq.api_break_x_arm,
    sq.arm_angle,
    sq.delta_pitcher_run_exp,
    sq.game_year,
    sq.p_throws,
    sq.stand,
    sq.balls,
    sq.strikes,
    sq.prev_release_pos_x,
    sq.prev_release_pos_z,
    sq.prev_release_speed,
    sq.prev_pfx_z,
    sq.prev_pitch_type
FROM sequenced sq
LEFT JOIN `{project}.{dataset}.dim_players_latest` p ON sq.pitcher = p.mlbid
LEFT JOIN `{project}.{dataset}.dim_teams` t ON p.current_team_id = t.team_id
WHERE sq.pitch_type IS NOT NULL
    AND sq.release_speed IS NOT NULL
    AND sq.delta_pitcher_run_exp IS NOT NULL
    AND p.primary_position IN ('Pitcher', 'Two-Way Player')
"""



class StuffPlusTrainer:
    """Stuff+ / Pitching+ 両モデルの学習・ランキング計算・登録"""

    def __init__(self, project_id: str, dataset_id: str, min_pitches: int = 100):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.min_pitches = min_pitches
        self.bq_client = bigquery.Client(project=project_id)
        self.registry = ModelRegistryService()
        logger.info(f"Initialized: project={project_id}, min_pitches={min_pitches}")
    
    # ----------------------------------------------------------
    # Step 1: データ取得
    # ----------------------------------------------------------
    def fetch_data(self, season: int) -> pd.DataFrame:
        """BigQuery から statcast_master を取得"""
        query = QUERY_TEMPLATE.format(
            project=self.project_id,
            dataset=self.dataset_id,
            season=season,
        )
        logger.info(f"Fetching statcast data for season {season}...")
        df = self.bq_client.query(query).to_dataframe()
        logger.info(f"Fetched {len(df):,} records, {df['pitcher'].nunique()} pitchers")
        return df

    # ----------------------------------------------------------
    # Step 2: モデル学習
    # ----------------------------------------------------------
    def train_model(
        self, df: pd.DataFrame, features: List[str], model_name: str
    ) -> Tuple[xgb.XGBRegressor, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
        """
        XGBoost 学習
        Returns:
            (model, df_clean, df_encoded, metrics)
        """
        logger.info(f"--- Training {model_name} ({len(features)} features) ---")

        # カテゴリカルカラムをモデルごとに決定
        cat_cols = CATEGORICAL_COLUMNS.get(model_name, ["pitch_type"])

        # 欠損除去 + One-Hot Encoding
        df_clean = df.dropna(subset=features + ["delta_pitcher_run_exp"]).copy()
        df_encoded = pd.get_dummies(df_clean[features + cat_cols], columns=cat_cols)

        X = df_encoded
        y = df_clean["delta_pitcher_run_exp"].values
        logger.info(f"X shape: {X.shape}, y shape: {y.shape}")

        # Train / Test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # XGBoost 学習
        model = xgb.XGBRegressor(**XGB_PARAMS)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

        # Pitch-level 評価
        y_pred = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        metrics = {
            "pitch_level_rmse": round(rmse, 6),
            "pitch_level_r2": round(r2, 6),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": X.shape[1],
        }
        logger.info(f"{model_name} pitch-level: RMSE={rmse:.4f}, R²={r2:.4f}")

        return model, df_clean, df_encoded, metrics


    # ----------------------------------------------------------
    # Step 3: ランキング計算（投手×球種に集約 → z-score正規化）
    # ----------------------------------------------------------
    def compute_rankings(
        self,
        df_clean: pd.DataFrame,
        model: xgb.XGBRegressor,
        df_encoded: pd.DataFrame,
        model_name: str,
        metrics: Dict[str, float],
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        投手×球種レベルに集約して Stuff+ / Pitching+ スコアを計算
        Returns:
            (ranking_df, updated_metrics)
        """
        score_col = model_name

        # 全データに対する予測
        df_clean["predicted_run_exp"] = model.predict(df_encoded)

        # 投手 × 球種ごとに集約
        ranking = (
            df_clean
            .groupby(["pitcher", "player_name", "pitch_name", "p_throws", "team_name", "league"])
            .agg(
                mean_pred_run_exp=("predicted_run_exp", "mean"),
                actual_run_exp=("delta_pitcher_run_exp", "mean"),
                pitch_count=("predicted_run_exp", "count"),
                avg_velo=("release_speed", "mean"),
                avg_spin=("release_spin_rate", "mean"),
            )
            .reset_index()
            .query(f"pitch_count >= {self.min_pitches}")
        )

        # z-score 正規化: 100 = league avg, 15pt = 1σ
        mu = ranking["mean_pred_run_exp"].mean()
        sigma = ranking["mean_pred_run_exp"].std()
        ranking[score_col] = 100 + (mu - ranking["mean_pred_run_exp"]) / sigma * 15

        # 集約レベルでのバリデーション
        corr_pearson, p_pearson = pearsonr(ranking["mean_pred_run_exp"], ranking["actual_run_exp"])
        corr_spearman, _ = spearmanr(ranking["mean_pred_run_exp"], ranking["actual_run_exp"])
        
        # metrics 更新
        metrics.update({
            "agg_records": len(ranking),
            "agg_pearson_r": round(float(corr_pearson), 4),
            "agg_pearson_p": float(p_pearson),
            "agg_spearman_r": round(float(corr_spearman), 4),
            "score_mean": round(float(ranking[score_col].mean()), 1),
            "score_std": round(float(ranking[score_col].std()), 1),
            "score_min": round(float(ranking[score_col].min()), 1),
            "score_max": round(float(ranking[score_col].max()), 1),
            "z_score_mu": round(float(mu), 6),
            "z_score_sigma": round(float(sigma), 6),
        })

        logger.info(
            f"{model_name} aggregated: {len(ranking)} pitcher×pitch_type combos, "
            f"Pearson r={corr_pearson:.4f}, Spearman r={corr_spearman:.4f}"
        )
        logger.info(
            f"{score_col} distribution: mean={ranking[score_col].mean():.1f}, "
            f"std={ranking[score_col].std():.1f}, "
            f"range=[{ranking[score_col].min():.1f}, {ranking[score_col].max():.1f}]"
        )

        return ranking, metrics

    # ----------------------------------------------------------
    # Step 4: アーティファクト保存 + Model Registry 登録
    # ----------------------------------------------------------
    def save_artifacts(
        self,
        model: xgb.XGBRegressor,
        ranking: pd.DataFrame,
        features: List[str],
        encoded_columns: List[str],
        metrics: Dict[str, float],
        model_name: str,
        season: int,
    ) -> ModelVersion:
        """
        GCS にモデル + ランキング保存 → BigQuery に ModelVersion 登録
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        version_str = f"v{now.strftime('%Y%m%d_%H%M%S')}_s{season}"
        bucket_name = self.registry.bucket_name
        bucket = self.registry.bucket

        base_path = f"models/{model_name}/{version_str}"

        # 1) XGBoost モデルを GCS に保存
        model_artifact = {
            "model": model,
            "features": features,
            "encoded_columns": encoded_columns,
            "z_score_mu": metrics["z_score_mu"],
            "z_score_sigma": metrics["z_score_sigma"],
            "min_pitches": self.min_pitches,
        }
        model_gcs_path = f"{base_path}/model.joblib"
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            joblib.dump(model_artifact, f.name)
            blob = bucket.blob(model_gcs_path)
            blob.upload_from_filename(f.name)
        logger.info(f"Model saved to gs://{bucket_name}/{model_gcs_path}")

        # 2) ランキング CSV を GCS に保存
        ranking_gcs_path = f"{base_path}/rankings.csv"
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            ranking.to_csv(f.name, index=False)
            blob = bucket.blob(ranking_gcs_path)
            blob.upload_from_filename(f.name)
        logger.info(f"Rankings saved to gs://{bucket_name}/{ranking_gcs_path}")

        # 3) メタデータ JSON を GCS に保存
        metadata = {
            "model_name": model_name,
            "season": season,
            "version": version_str,
            "features": features,
            "encoded_columns": encoded_columns,
            "xgb_params": XGB_PARAMS,
            "min_pitches": self.min_pitches,
            "metrics": metrics,
        }
        metadata_gcs_path = f"{base_path}/metadata.json"
        blob = bucket.blob(metadata_gcs_path)
        blob.upload_from_string(
            json.dumps(metadata, indent=2, default=str),
            content_type="application/json",
        )
        logger.info(f"Metadata saved to gs://{bucket_name}/{metadata_gcs_path}")

        # 4) BigQuery Model Registry に登録
        version = ModelVersion(
            version=version_str,
            model_type=model_name,
            algorithm="xgboost",
            training_season=season,
            trained_at=now.isoformat(),
            gcs_path=f"gs://{bucket_name}/{model_gcs_path}",
            n_samples=metrics["n_train"] + metrics["n_test"],
            features=features,
            model_params={
                "xgb_params": XGB_PARAMS,
                "min_pitches": self.min_pitches,
                "metrics": metrics,
            },
            is_active=False,
            created_by="train_stuff_plus.py",
        )
        self.registry._insert_bq_metadata(version)
        logger.info(f"Registered in Model Registry: {model_name} {version_str}")

        return version

    # ----------------------------------------------------------
    # Step 5: ランキングを BigQuery テーブルに書き込み
    # ----------------------------------------------------------
    def save_rankings_to_bq(
        self, ranking: pd.DataFrame, model_name: str, season: int
    ) -> None:
        """ランキング結果を BigQuery テーブルに書き込み（API用）"""
        table_id = f"{self.project_id}.{self.dataset_id}.stuff_plus_rankings"

        # 既存データを削除（再トレーニング時の重複防止）
        delete_query = f"""
            DELETE FROM `{table_id}`
            WHERE model_type = @model_type AND season = @season
        """
        delete_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("model_type", "STRING", model_name),
                bigquery.ScalarQueryParameter("season", "INT64", season),
            ]
        )
        self.bq_client.query(delete_query, job_config=delete_config).result()
        logger.info(f"Deleted existing rankings: model_type={model_name}, season={season}")

        # model_type と season カラムを追加
        df_out = ranking.copy()
        df_out["model_type"] = model_name
        df_out["season"] = season

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            ],
        )
        job = self.bq_client.load_table_from_dataframe(
            df_out, table_id, job_config=job_config
        )
        job.result()
        logger.info(f"Rankings written to {table_id}: {len(df_out)} rows ({model_name})")

    # ----------------------------------------------------------
    # run: 全パイプライン実行
    # ----------------------------------------------------------
    def run(self, season: int) -> Dict[str, ModelVersion]:
        """学習からランキング保存までの全パイプライン"""
        logger.info("=" * 70)
        logger.info(f"Stuff+ / Pitching+ Training Pipeline: season={season}")
        logger.info("=" * 70)

        # 1. データ取得（1回だけ）
        df = self.fetch_data(season)

        # 特徴量エンジニアリング: plate_z を打者ストライクゾーンで正規化
        sz_range = df["sz_top"] - df["sz_bot"]
        df["plate_z_norm"] = np.where(
            sz_range > 0,
            (df["plate_z"] - df["sz_bot"]) / sz_range,
            np.nan,
        )
        n_valid = df["plate_z_norm"].notna().sum()
        logger.info(f"plate_z_norm computed: {n_valid:,}/{len(df):,} valid rows")

        # Pitching++ 用特徴量エンジニアリング
        # P5: zone_distance — ゾーン中心 (0, 0.5) からの距離
        df["zone_distance"] = np.sqrt(
            df["plate_x"] ** 2 + (df["plate_z_norm"] - 0.5) ** 2
        )

        # P1: release_diff — 前球とのリリースポイント差（トンネル距離）
        df["release_diff"] = np.sqrt(
            (df["release_pos_x"] - df["prev_release_pos_x"]) ** 2
            + (df["release_pos_z"] - df["prev_release_pos_z"]) ** 2
        )

        # P1: speed_diff — 前球との球速差
        df["speed_diff"] = df["release_speed"] - df["prev_release_speed"]

        # 打席の最初の球（prev = NULL）をデフォルト値で埋める
        df["release_diff"] = df["release_diff"].fillna(0)       # トンネル無し
        df["speed_diff"] = df["speed_diff"].fillna(0)            # 球速変化なし
        df["prev_pfx_z"] = df["prev_pfx_z"].fillna(df["pfx_z"]) # 自球の変化量
        df["prev_pitch_type"] = df["prev_pitch_type"].fillna("NONE")  # 前球なし

        logger.info(
            f"Pitching++ features: zone_distance valid={df['zone_distance'].notna().sum():,}, "
            f"release_diff valid={df['release_diff'].notna().sum():,}"
        )

        results = {}

        for model_name, features in [
            ("stuff_plus", STUFF_FEATURES),
            ("pitching_plus", PITCHING_FEATURES),
            ("pitching_plus_plus", PITCHING_PP_FEATURES),
        ]:
            logger.info("")
            logger.info(f"{'=' * 30} {model_name} {'=' * 30}")

            # 2. モデル学習
            model, df_clean, df_encoded, metrics = self.train_model(
                df, features, model_name
            )

            # 3. ランキング計算
            ranking, metrics = self.compute_rankings(
                df_clean, model, df_encoded, model_name, metrics
            )

            # 4. GCS + Model Registry 保存
            version = self.save_artifacts(
                model, ranking, features, df_encoded.columns.tolist(),
                metrics, model_name, season,
            )

            # 5. BigQuery ランキングテーブルに書き込み
            self.save_rankings_to_bq(ranking, model_name, season)

            results[model_name] = version

            # TOP 5 表示
            score_col = model_name
            top5 = ranking.nlargest(5, score_col)
            logger.info(f"\n{model_name} TOP 5:")
            for _, row in top5.iterrows():
                logger.info(
                    f"  {row['player_name']:25s} {row['pitch_name']:18s} "
                    f"{score_col}={row[score_col]:.1f}  "
                    f"velo={row['avg_velo']:.1f}  spin={row['avg_spin']:.0f}"
                )
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 70)
        logger.info("NEXT STEPS:")
        logger.info("  1. promote version:")
        logger.info("     svc = ModelRegistryService()")
        for name, ver in results.items():
            logger.info(f"     svc.promote_version('{name}', '{ver.version}')")
        logger.info("  2. API エンドポイントからランキング取得可能")
        logger.info("=" * 70)

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Train Stuff+ / Pitching+ XGBoost models"
    )
    parser.add_argument(
        "--season", type=int, required=True,
        help="Season year (e.g., 2025)"
    )
    parser.add_argument(
        "--min-pitches", type=int, default=100,
        help="Minimum pitch count for ranking aggregation (default: 100)"
    )
    args = parser.parse_args()

    load_dotenv()
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("BIGQUERY_DATASET_ID")

    if not project_id or not dataset_id:
        logger.error("GCP_PROJECT_ID and BIGQUERY_DATASET_ID must be set in .env")
        sys.exit(1)

    trainer = StuffPlusTrainer(project_id, dataset_id, min_pitches=args.min_pitches)

    try:
        trainer.run(season=args.season)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()