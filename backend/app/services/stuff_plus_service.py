"""
Stuff+ / Pitching+ 推論サービス
事前計算済みランキングの取得と、個別投手のリアルタイム推論を提供
"""
import logging
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from backend.app.services.base import get_bq_client
from backend.app.services.model_registry_service import ModelRegistryService
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ランキング格納テーブル（train_stuff_plus.py の save_rankings_to_bq で書き込み）
RANKINGS_TABLE = settings.get_table_full_name("stuff_plus_rankings")

# リアルタイム推論用: statcast_master から取得するカラム
STATCAST_COLUMNS = [
    "pitcher", "player_name", "pitch_type", "pitch_name",
    "release_speed", "release_spin_rate", "spin_axis",
    "pfx_x", "pfx_z", "release_extension",
    "release_pos_x", "release_pos_z",
    "plate_x", "plate_z", "sz_top", "sz_bot",
    "api_break_z_with_gravity", "api_break_x_arm",
    "arm_angle",
    "delta_pitcher_run_exp",
]


class StuffPlusService:
    """Stuff+ / Pitching+ の推論とランキング取得"""

    def __init__(self):
        self.client = get_bq_client()
        self.registry = ModelRegistryService()
        # モデルアーティファクト（遅延ロード）
        self._models: Dict[str, Dict] = {}

    # ----------------------------------------------------------
    # モデルロード（遅延ロード）
    # ----------------------------------------------------------
    def _ensure_model_loaded(self, model_type: str) -> Dict:
        """
        Model Registry から active バージョンのモデルをロード（未ロード時のみ）
        Returns:
            artifact dict: {"model", "features", "encoded_columns",
                            "z_score_mu", "z_score_sigma", "min_pitches"}
        """
        if model_type in self._models:
            return self._models[model_type]

        try:
            artifact, version_meta = self.registry.load_model(model_type)
            self._models[model_type] = artifact
            logger.info(
                f"Loaded {model_type} model: version={version_meta.version}, "
                f"season={version_meta.training_season}"
            )
            return artifact
        except FileNotFoundError:
            logger.warning(f"No active model found for {model_type}")
            raise
        except Exception as e:
            logger.error(f"Failed to load {model_type} model: {e}")
            raise

    # ----------------------------------------------------------
    # ランキング取得（事前計算済み → BigQuery SELECT）
    # ----------------------------------------------------------
    # ----------------------------------------------------------
    # 名前フォーマット: "Last, First" → "First Last"
    # ----------------------------------------------------------
    @staticmethod
    def _format_name(name: str) -> str:
        if name and ", " in name:
            last, first = name.split(", ", 1)
            return f"{first} {last}"
        return name or ""

    async def get_rankings(
        self,
        model_type: str = "stuff_plus",
        season: int = 2025,
        limit: int = 50,
        offset: int = 0,
        sort_order: str = "desc",
        min_pitches: int = 0,
    ) -> Dict:
        """
        事前計算済みランキングを BigQuery から取得

        Returns:
            {"rankings": [...], "total": int, "model_type": str, "season": int}
        """
        score_col = "stuff_plus" if model_type == "stuff_plus" else "pitching_plus"
        order = "DESC" if sort_order == "desc" else "ASC"

        # min_pitches フィルタ
        pitches_filter = "AND pitch_count >= @min_pitches" if min_pitches > 0 else ""

        # トータル件数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `{RANKINGS_TABLE}`
            WHERE model_type = @model_type AND season = @season
            {pitches_filter}
        """

        # ランキングデータ
        query = f"""
            SELECT
                pitcher,
                player_name,
                pitch_name,
                p_throws,
                team_name,
                league,
                {score_col},
                pitch_count,
                avg_velo,
                avg_spin,
                mean_pred_run_exp,
                actual_run_exp
            FROM `{RANKINGS_TABLE}`
            WHERE model_type = @model_type AND season = @season
            {pitches_filter}
            ORDER BY {score_col} {order}
            LIMIT @limit OFFSET @offset
        """

        base_params = [
            ("model_type", "STRING", model_type),
            ("season", "INT64", season),
        ]
        if min_pitches > 0:
            base_params.append(("min_pitches", "INT64", min_pitches))

        job_config = self._make_job_config(
            base_params + [
                ("limit", "INT64", limit),
                ("offset", "INT64", offset),
            ]
        )

        try:
            # 件数取得
            count_config = self._make_job_config(base_params)
            count_result = list(self.client.query(count_query, job_config=count_config))
            total = count_result[0]["total"] if count_result else 0

            # ランキング取得
            df = self.client.query(query, job_config=job_config).to_dataframe()

            rankings = []
            for _, row in df.iterrows():
                rankings.append({
                    "pitcher_id": int(row["pitcher"]),
                    "player_name": row["player_name"],
                    "pitch_name": row["pitch_name"],
                    "hand": row.get("p_throws", ""),
                    "team": row.get("team_name", ""),
                    "league": row.get("league", ""),
                    "score": round(float(row[score_col]), 1),
                    "pitch_count": int(row["pitch_count"]),
                    "avg_velo": round(float(row["avg_velo"]), 1),
                    "avg_spin": round(float(row["avg_spin"]), 0),
                    "mean_pred_run_exp": round(float(row["mean_pred_run_exp"]), 6),
                    "actual_run_exp": round(float(row["actual_run_exp"]), 6),
                })

            return {
                "rankings": rankings,
                "total": total,
                "model_type": model_type,
                "season": season,
            }

        except Exception as e:
            logger.error(f"Failed to get rankings: {e}")
            raise

    # ----------------------------------------------------------
    # 個別投手の球種別スコア（リアルタイム推論）
    # ----------------------------------------------------------
    async def predict_single_pitcher(
        self,
        pitcher_id: int,
        model_type: str = "stuff_plus",
        season: int = 2025,
    ) -> Dict:
        """
        特定投手の球種別 Stuff+ / Pitching+ をリアルタイム推論

        Returns:
            {"pitcher_id", "player_name", "model_type", "pitches": [...]}
        """
        artifact = self._ensure_model_loaded(model_type)
        xgb_model: xgb.XGBRegressor = artifact["model"]
        encoded_columns: List[str] = artifact["encoded_columns"]
        z_mu: float = artifact["z_score_mu"]
        z_sigma: float = artifact["z_score_sigma"]
        min_pitches: int = artifact["min_pitches"]
        features: List[str] = artifact["features"]

        # BigQuery から該当投手のデータ取得
        cols = ", ".join(STATCAST_COLUMNS)
        query = f"""
            SELECT {cols}
            FROM `{settings.get_table_full_name('statcast_master')}`
            WHERE pitcher = @pitcher_id
                AND game_year = @season
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
                AND delta_pitcher_run_exp IS NOT NULL
        """
        job_config = self._make_job_config([
            ("pitcher_id", "INT64", pitcher_id),
            ("season", "INT64", season),
        ])

        df = self.client.query(query, job_config=job_config).to_dataframe()
        if df.empty:
            raise ValueError(f"No data found for pitcher_id={pitcher_id}, season={season}")

        player_name = self._format_name(df["player_name"].iloc[0])

        # plate_z を打者ストライクゾーンで正規化（Pitching+ 用）
        sz_range = df["sz_top"] - df["sz_bot"]
        df["plate_z_norm"] = np.where(
            sz_range > 0,
            (df["plate_z"] - df["sz_bot"]) / sz_range,
            np.nan,
        )

        # 特徴量作成
        df_clean = df.dropna(subset=features + ["pitch_type", "delta_pitcher_run_exp"]).copy()
        df_encoded = pd.get_dummies(
            df_clean[features + ["pitch_type"]], columns=["pitch_type"]
        )

        # encoded_columns に合わせる（存在しないカラムは 0 埋め）
        for col in encoded_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_encoded = df_encoded[encoded_columns]

        # 予測
        df_clean["predicted_run_exp"] = xgb_model.predict(df_encoded)

        # 球種ごとに集約
        score_col = "stuff_plus" if model_type == "stuff_plus" else "pitching_plus"
        agg = (
            df_clean
            .groupby("pitch_name")
            .agg(
                mean_pred_run_exp=("predicted_run_exp", "mean"),
                actual_run_exp=("delta_pitcher_run_exp", "mean"),
                pitch_count=("predicted_run_exp", "count"),
                avg_velo=("release_speed", "mean"),
                avg_spin=("release_spin_rate", "mean"),
            )
            .reset_index()
        )
        agg[score_col] = 100 + (z_mu - agg["mean_pred_run_exp"]) / z_sigma * 15

        pitches = []
        for _, row in agg.iterrows():
            pitches.append({
                "pitch_name": row["pitch_name"],
                "score": round(float(row[score_col]), 1),
                "pitch_count": int(row["pitch_count"]),
                "avg_velo": round(float(row["avg_velo"]), 1),
                "avg_spin": round(float(row["avg_spin"]), 0),
                "mean_pred_run_exp": round(float(row["mean_pred_run_exp"]), 6),
                "actual_run_exp": round(float(row["actual_run_exp"]), 6),
                "sufficient_sample": row["pitch_count"] >= min_pitches,
            })

        pitches.sort(key=lambda x: x["score"], reverse=True)

        return {
            "pitcher_id": pitcher_id,
            "player_name": player_name,
            "model_type": model_type,
            "season": season,
            "pitches": pitches,
        }

    # ----------------------------------------------------------
    # Stuff+ vs Pitching+ 比較（gap分析）
    # ----------------------------------------------------------
    async def compare_stuff_pitching(
        self,
        pitcher_id: int,
        season: int = 2025,
    ) -> Dict:
        """
        Stuff+ vs Pitching+ を比較。gap が大きい = 球質と制球に乖離あり

        Returns:
            {"pitcher_id", "player_name", "comparison": [...], "profile": str}
        """
        stuff = await self.predict_single_pitcher(pitcher_id, "stuff_plus", season)
        pitching = await self.predict_single_pitcher(pitcher_id, "pitching_plus", season)

        # pitch_name でマージ
        stuff_map = {p["pitch_name"]: p for p in stuff["pitches"]}
        pitching_map = {p["pitch_name"]: p for p in pitching["pitches"]}

        all_pitches = set(stuff_map.keys()) | set(pitching_map.keys())

        comparison = []
        total_gap = 0.0
        count = 0

        for pitch_name in sorted(all_pitches):
            s = stuff_map.get(pitch_name)
            p = pitching_map.get(pitch_name)

            stuff_score = s["score"] if s else None
            pitching_score = p["score"] if p else None
            gap = (stuff_score - pitching_score) if (stuff_score and pitching_score) else None

            comparison.append({
                "pitch_name": pitch_name,
                "stuff_plus": stuff_score,
                "pitching_plus": pitching_score,
                "gap": round(gap, 1) if gap is not None else None,
                "pitch_count": (s or p)["pitch_count"],
                "avg_velo": (s or p)["avg_velo"],
            })

            if gap is not None:
                total_gap += gap
                count += 1

        # 全球種の平均 gap で投手プロファイルを判定
        avg_gap = total_gap / count if count > 0 else 0

        if avg_gap > 5:
            profile = "stuff_dominant"
            profile_desc = "球質型: 球質は elite だが制球パターンで損している"
        elif avg_gap < -5:
            profile = "command_dominant"
            profile_desc = "制球型: 球質は平凡だが制球・配球で稼いでいる"
        else:
            profile = "balanced"
            profile_desc = "バランス型: 球質と制球のバランスが取れている"

        comparison.sort(key=lambda x: abs(x["gap"] or 0), reverse=True)

        return {
            "pitcher_id": pitcher_id,
            "player_name": stuff["player_name"],
            "season": season,
            "avg_gap": round(avg_gap, 1),
            "profile": profile,
            "profile_desc": profile_desc,
            "comparison": comparison,
        }

    # ----------------------------------------------------------
    # 選手名検索（ランキングテーブルから DISTINCT 投手を返す）
    # ----------------------------------------------------------
    async def search_pitchers(
        self,
        name: str,
        season: int = 2025,
        limit: int = 10,
    ) -> List[Dict]:
        """
        ランキングテーブルから名前で投手を検索

        Returns:
            [{"pitcher_id": int, "player_name": str, "team": str, "hand": str}, ...]
        """
        query = f"""
            SELECT DISTINCT pitcher, player_name, team_name, p_throws
            FROM `{RANKINGS_TABLE}`
            WHERE season = @season
                AND model_type = 'stuff_plus'
                AND LOWER(player_name) LIKE LOWER(@name_pattern)
            ORDER BY player_name
            LIMIT @limit
        """
        job_config = self._make_job_config([
            ("season", "INT64", season),
            ("name_pattern", "STRING", f"%{name}%"),
            ("limit", "INT64", limit),
        ])

        try:
            df = self.client.query(query, job_config=job_config).to_dataframe()
            results = []
            seen = set()
            for _, row in df.iterrows():
                pid = int(row["pitcher"])
                if pid in seen:
                    continue
                seen.add(pid)
                results.append({
                    "pitcher_id": pid,
                    "player_name": row["player_name"],
                    "team": row.get("team_name", ""),
                    "hand": row.get("p_throws", ""),
                })
            return results
        except Exception as e:
            logger.error(f"Failed to search pitchers: {e}")
            raise

    # ----------------------------------------------------------
    # ヘルパー
    # ----------------------------------------------------------
    @staticmethod
    def _make_job_config(params: List[tuple]):
        """BigQuery parameterized query 用の JobConfig を作成"""
        from google.cloud import bigquery as bq
        return bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter(name, type_, value)
                for name, type_, value in params
            ]
        )
