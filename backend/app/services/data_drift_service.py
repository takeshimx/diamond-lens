"""
Data Drift Detection Service
MLモデル入力データの分布変化（データドリフト）を統計的に検知するサービス。

対象モデル:
- player_segmentation (KMeans): 打者/投手の分類
- stuff_plus / pitching_plus / pitching_plus_plus (XGBoost): 球質・投球評価

検知手法:
1. Feature Drift  — 入力特徴量の分布変化（KS検定, PSI, 平均値シフト）
2. Prediction Drift — モデル出力（predicted_run_exp）の分布変化
3. Concept Drift   — 特徴量と目的変数の関係変化（予測 vs 実績の乖離）
"""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from scipy import stats
from google.cloud import bigquery
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================
# データモデル
# ============================================================

@dataclass
class FeatureDriftResult:
    """個別特徴量のドリフト検知結果"""
    feature_name: str
    ks_statistic: float # KS統計量（0-1, 高いほど分布の差異が大きい）
    ks_p_value: float # p値（< alphaでドリフト有意）
    psi_value: float # PSI (>0.1 warning, >0.2 critical)
    mean_baseline: float # ベースライン平均値
    mean_target: float # ターゲット平均値
    mean_shift_pct: float # 平均値変化率
    drift_detected: bool # ドリフト検知フラグ
    severity: str # ドリフトの重要度（"none" | "warning" | "critical"）


@dataclass
class PredictionDriftResult:
    """Prediction Drift: モデル出力分布の変化"""
    ks_statistic: float
    ks_p_value: float
    psi_value: float
    mean_baseline: float  # baseline predicted_run_exp の平均
    mean_target: float    # target predicted_run_exp の平均
    mean_shift_pct: float
    score_baseline: float # baseline z-score 変換後スコアの平均
    score_target: float   # target z-score 変換後スコアの平均
    drift_detected: bool
    severity: str


@dataclass
class ConceptDriftResult:
    """Concept Drift: 予測と実績の関係変化"""
    rmse_baseline: float     # baseline RMSE(predicted vs actual)
    rmse_target: float       # target RMSE
    rmse_change_pct: float   # RMSE 変化率
    mae_baseline: float
    mae_target: float
    corr_baseline: float     # baseline 相関係数
    corr_target: float       # target 相関係数
    corr_degradation: float  # 相関の低下幅
    drift_detected: bool
    severity: str


@dataclass
class DriftReport:
    """ドリフト検知レポート"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: str = ""
    drift_type: str = "feature"  # "feature" | "prediction" | "concept"
    baseline_season: int = 0
    target_season: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    features: List[FeatureDriftResult] = field(default_factory=list)
    prediction_drift: Optional[PredictionDriftResult] = None
    concept_drift: Optional[ConceptDriftResult] = None
    overall_drift_detected: bool = False
    summary: str = ""

    def to_dict(self) -> Dict:
        """API レスポンス用の辞書変換"""
        result = {
            "report_id": self.report_id,
            "model_type": self.model_type,
            "drift_type": self.drift_type,
            "baseline_season": self.baseline_season,
            "target_season": self.target_season,
            "timestamp": self.timestamp,
            "overall_drift_detected": self.overall_drift_detected,
            "summary": self.summary,
            "features": [asdict(f) for f in self.features],
        }
        if self.prediction_drift:
            result["prediction_drift"] = asdict(self.prediction_drift)
        if self.concept_drift:
            result["concept_drift"] = asdict(self.concept_drift)
        return result


# ============================================================
# モデル別の特徴量定義
# ============================================================

MODEL_FEATURE_CONFIG = {
    "batter_segmentation": {
        "table": "fact_batting_stats_with_risp",
        "features": ["ops", "iso", "k_rate", "bb_rate"],
        "query_template": """
            SELECT
                season,
                ops,
                iso,
                (100.0 * so / pa) AS k_rate,
                (100.0 * bb / pa) AS bb_rate
            FROM `{table_full_name}`
            WHERE season = {season}
                AND pa >= {min_sample}
        """,
        "min_sample": 300,
    },
    "pitcher_segmentation": {
        "table": "fact_pitching_stats_master",
        "features": ["era", "k_9", "gbpct"],
        "query_template": """
            SELECT
                season,
                era,
                k_9,
                gbpct
            FROM `{table_full_name}`
            WHERE season = {season}
                AND gs > 0 AND ip > {min_sample}
        """,
        "min_sample": 90,
    },
    # ---- Stuff+ / Pitching+ / Pitching++ (XGBoost) ----
    # Statcast ピッチレベルの特徴量ドリフトを監視
    # ハードウェア変更（Hawk-Eye更新等）で分布が変わる可能性がある
    "stuff_plus": {
        "table": "statcast_master",
        "features": [
            "release_speed", "release_spin_rate", "spin_axis",
            "pfx_x", "pfx_z", "release_extension",
            "api_break_z_with_gravity", "api_break_x_arm", "arm_angle",
        ],
        "query_template": """
            SELECT
                game_year AS season,
                release_speed,
                release_spin_rate,
                spin_axis,
                pfx_x,
                pfx_z,
                release_extension,
                api_break_z_with_gravity,
                api_break_x_arm,
                arm_angle
            FROM `{table_full_name}`
            WHERE game_year = {season}
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
        """,
        "min_sample": 0,  # ピッチレベルなのでサンプル数フィルタ不要
    },
    "pitching_plus": {
        "table": "statcast_master",
        "features": [
            "release_speed", "release_spin_rate", "spin_axis",
            "pfx_x", "pfx_z", "release_extension",
            "api_break_z_with_gravity", "api_break_x_arm", "arm_angle",
            "plate_x", "plate_z",
        ],
        "query_template": """
            SELECT
                game_year AS season,
                release_speed,
                release_spin_rate,
                spin_axis,
                pfx_x,
                pfx_z,
                release_extension,
                api_break_z_with_gravity,
                api_break_x_arm,
                arm_angle,
                plate_x,
                plate_z
            FROM `{table_full_name}`
            WHERE game_year = {season}
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
        """,
        "min_sample": 0,
    },
    "pitching_plus_plus": {
        "table": "statcast_master",
        "features": [
            "release_speed", "release_spin_rate", "spin_axis",
            "pfx_x", "pfx_z", "release_extension",
            "api_break_z_with_gravity", "api_break_x_arm", "arm_angle",
            "plate_x", "plate_z",
        ],
        "query_template": """
            SELECT
                game_year AS season,
                release_speed,
                release_spin_rate,
                spin_axis,
                pfx_x,
                pfx_z,
                release_extension,
                api_break_z_with_gravity,
                api_break_x_arm,
                arm_angle,
                plate_x,
                plate_z
            FROM `{table_full_name}`
            WHERE game_year = {season}
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
        """,
        "min_sample": 0,
    },
}

# ============================================================
# Data Drift Detection Service
# ============================================================

class DataDriftService:
    """
    MLモデル入力データのドリフト検知サービス
    使用例:
        svc = DataDriftService()
        report = svc.detect_drift(
            baseline_season=2024,
            target_season=2025,
            model_type="batter_segmentation"
        )
        print(report.summary)
    """
    def __init__(self):
        self.client = bigquery.Client(project=settings.gcp_project_id)
        self.psi_warning = settings.ml_drift_psi_warning_threshold
        self.psi_critical = settings.ml_drift_psi_critical_threshold
        self.ks_alpha = settings.ml_drift_ks_alpha
    
    # ----------------------------------------------------------
    # Public: ドリフト検知メイン
    # ----------------------------------------------------------

    def detect_drift(
        self,
        baseline_season: int,
        target_season: int,
        model_type: str,
    ) -> DriftReport:
        """
        ベースラインシーズンとターゲットシーズン間の
        データドリフトを検知する。
        Args:
            baseline_season: 基準となるシーズン（例: 2024）
            target_season: 比較対象のシーズン（例: 2025）
            model_type: "batter_segmentation" | "pitcher_segmentation"
        Returns:
            DriftReport: 各特徴量のドリフト検知結果を含むレポート
        """
        if model_type not in MODEL_FEATURE_CONFIG:
            raise ValueError(
                f"Unknown model_type: {model_type}. "
                f"Available: {list(MODEL_FEATURE_CONFIG.keys())}"
            )
        
        config = MODEL_FEATURE_CONFIG[model_type]

        # Step 1: BigQuery からデータ取得
        logger.info(
            f"Fetching data for drift detection: "
            f"{model_type} ({baseline_season} vs {target_season})"
        )
        df_baseline = self._fetch_season_data(
            config, baseline_season
        )
        df_target = self._fetch_season_data(
            config, target_season
        )
        
        if df_baseline.empty or df_target.empty:
            return DriftReport(
                model_type=model_type,
                baseline_season=baseline_season,
                target_season=target_season,
                summary="データ不足: ドリフト検知を実行できませんでした。",
            )
        
        # Step 2: 各特徴量のドリフト検知
        feature_results: List[FeatureDriftResult] = []
        for feature in config["features"]:
            result = self._analyze_feature_drift(
                baseline=df_baseline[feature].dropna(),
                target=df_target[feature].dropna(),
                feature_name=feature,
            )
            feature_results.append(result)
        
        # Step 3: 総合判定
        # check if any drift is detected in any feature
        overall_drift = any(f.drift_detected for f in feature_results)
        critical_features = [
            f.feature_name for f in feature_results
            if f.severity == "critical"
        ]
        warning_features = [
            f.feature_name for f in feature_results
            if f.severity == "warning"
        ]

        summary = self._build_summary(
            model_type, baseline_season, target_season,
            critical_features, warning_features,
        )

        report = DriftReport(
            model_type=model_type,
            baseline_season=baseline_season,
            target_season=target_season,
            features=feature_results,
            overall_drift_detected=overall_drift,
            summary=summary,
        )

        logger.info(
            f"Drift detection complete: overall_drift={overall_drift}, "
            f"critical={len(critical_features)}, warning={len(warning_features)}"
        )
        return report
    
    # ----------------------------------------------------------
    # Private: BigQuery データ取得
    # ----------------------------------------------------------

    def _fetch_season_data(
        self, config: Dict, season: int
    ) -> pd.DataFrame:
        """
        指定されたシーズンの特徴量データを BigQuery から取得する
        """
        table_full_name = settings.get_table_full_name(config["table"])
        query = config["query_template"].format(
            table_full_name=table_full_name,
            season=season,
            min_sample=config["min_sample"]
        )
        try:
            df = self.client.query(query).to_dataframe()
            logger.info(f"Fetched {len(df)} rows for season {season}")
            return df
        except Exception as e:
            logger.error(f"BigQuery fetch failed: {e}")
            return pd.DataFrame()
    
    # ----------------------------------------------------------
    # Private: 個別特徴量のドリフト分析
    # ----------------------------------------------------------

    def _analyze_feature_drift(
        self,
        baseline: pd.Series,
        target: pd.Series,
        feature_name: str,
    ) -> FeatureDriftResult:
        """
        1つの特徴量に対して3つの統計テストを実行し、
        ドリフトの有無と深刻度を判定する。
        """
        # 1. KS検定
        ks_stat, ks_p = stats.ks_2samp(baseline, target)

        # 2. PSI計算
        psi = self._calculate_psi(baseline, target)

        # 3. 平均値シフト
        mean_base = float(baseline.mean())
        mean_tgt = float(target.mean())
        if mean_base != 0:
            mean_shift = ((mean_tgt - mean_base) / abs(mean_base)) * 100
        else:
            mean_shift = 0.0 if mean_tgt == 0 else 100.0
        
        # 総合判定
        severity, drift_detected = self._determine_severity(ks_p, psi)

        return FeatureDriftResult(
            feature_name=feature_name,
            ks_statistic=round(ks_stat, 4),
            ks_p_value=round(ks_p, 6),
            psi_value=round(psi, 4),
            mean_baseline=round(mean_base, 4),
            mean_target=round(mean_tgt, 4),
            mean_shift_pct=round(mean_shift, 2),
            drift_detected=drift_detected,
            severity=severity,
        )
    
    # ----------------------------------------------------------
    # Private: PSI (Population Stability Index) 計算
    # ----------------------------------------------------------

    @staticmethod
    def _calculate_psi(
        baseline: pd.Series,
        target: pd.Series,
        n_bins: int = 10,
    ) -> float:
        """
        Population Stability Index を計算。
        PSI = Σ (P_target_i - P_baseline_i) * ln(P_target_i / P_baseline_i)
        (「10個のバケツの中身が、昔と今でどれくらい入れ替わったか」を数値化したもの)
        PSI < 0.1  → 分布は安定
        PSI 0.1-0.2 → 若干の変化（Warning）
        PSI > 0.2  → 有意な変化（Critical）
        Args:
            baseline: 基準シーズンのデータ
            target: 比較シーズンのデータ
            n_bins: ヒストグラムのビン数
        Returns:
            PSI 値
        """
        # ビンの端点をベースラインから決定
        _, bin_edges = np.histogram(baseline, bins=n_bins)

        # 各ビンの割合を計算（0除算防止のため微小値を加算）
        eps = 1e-4
        baseline_counts = np.histogram(baseline, bins=bin_edges)[0]
        target_counts = np.histogram(target, bins=bin_edges)[0]

        baseline_pct = (baseline_counts / len(baseline)) + eps
        target_pct = (target_counts / len(target)) + eps

        # PSI 計算
        psi = np.sum(
            (target_pct - baseline_pct) * np.log(target_pct / baseline_pct)
        )
        return float(psi)
    
    # ----------------------------------------------------------
    # Private: 深刻度判定
    # ----------------------------------------------------------
    def _determine_severity(
        self, ks_p_value: float, psi_value: float
    ) -> tuple:
        """
        KS検定のp値とPSI値から深刻度を判定。

        Returns:
            (severity: str, drift_detected: bool)
        """
        if psi_value >= self.psi_critical or ks_p_value < self.ks_alpha:
            return "critical", True
        elif psi_value >= self.psi_warning:
            return "warning", True
        else:
            return "none", False
    
    # ----------------------------------------------------------
    # Private: Generate Summary
    # ----------------------------------------------------------

    # ----------------------------------------------------------
    # Public: Prediction Drift 検知（Stuff+ 専用）
    # ----------------------------------------------------------

    def detect_prediction_drift(
        self,
        baseline_season: int,
        target_season: int,
        model_type: str,
    ) -> DriftReport:
        """
        モデル予測値（predicted_run_exp）の分布変化を検知。
        同じモデルで baseline / target の Statcast データを推論し、
        予測分布の KS / PSI を計算する。

        Stuff+ / Pitching+ / Pitching++ 専用。
        """
        from backend.app.services.stuff_plus_service import StuffPlusService

        stuff_svc = StuffPlusService()
        artifact = stuff_svc._ensure_model_loaded(model_type)
        xgb_model = artifact["model"]
        encoded_columns = artifact["encoded_columns"]
        features = artifact["features"]
        z_mu = artifact["z_score_mu"]
        z_sigma = artifact["z_score_sigma"]

        logger.info(
            f"Prediction drift detection: {model_type} "
            f"({baseline_season} vs {target_season})"
        )

        preds_baseline = self._predict_season(
            xgb_model, encoded_columns, features,
            model_type, baseline_season,
        )
        preds_target = self._predict_season(
            xgb_model, encoded_columns, features,
            model_type, target_season,
        )

        if preds_baseline is None or preds_target is None:
            return DriftReport(
                model_type=model_type,
                drift_type="prediction",
                baseline_season=baseline_season,
                target_season=target_season,
                summary="データ不足: Prediction Drift 検知を実行できませんでした。",
            )

        # KS 検定
        ks_stat, ks_p = stats.ks_2samp(preds_baseline, preds_target)
        psi = self._calculate_psi(
            pd.Series(preds_baseline), pd.Series(preds_target)
        )

        mean_base = float(np.mean(preds_baseline))
        mean_tgt = float(np.mean(preds_target))
        mean_shift = (
            ((mean_tgt - mean_base) / abs(mean_base)) * 100
            if mean_base != 0 else 0.0
        )

        # z-score 変換後のスコア平均
        score_base = 100 + (z_mu - mean_base) / z_sigma * 15
        score_tgt = 100 + (z_mu - mean_tgt) / z_sigma * 15

        severity, drift_detected = self._determine_severity(ks_p, psi)

        pred_result = PredictionDriftResult(
            ks_statistic=round(ks_stat, 4),
            ks_p_value=round(ks_p, 6),
            psi_value=round(psi, 4),
            mean_baseline=round(mean_base, 6),
            mean_target=round(mean_tgt, 6),
            mean_shift_pct=round(mean_shift, 2),
            score_baseline=round(score_base, 1),
            score_target=round(score_tgt, 1),
            drift_detected=drift_detected,
            severity=severity,
        )

        summary = self._build_prediction_drift_summary(
            model_type, baseline_season, target_season,
            pred_result,
        )

        report = DriftReport(
            model_type=model_type,
            drift_type="prediction",
            baseline_season=baseline_season,
            target_season=target_season,
            prediction_drift=pred_result,
            overall_drift_detected=drift_detected,
            summary=summary,
        )

        logger.info(
            f"Prediction drift complete: severity={severity}, "
            f"score {score_base:.1f}→{score_tgt:.1f}"
        )
        return report

    # ----------------------------------------------------------
    # Public: Concept Drift 検知（Stuff+ 専用）
    # ----------------------------------------------------------

    def detect_concept_drift(
        self,
        baseline_season: int,
        target_season: int,
        model_type: str,
    ) -> DriftReport:
        """
        予測値 vs 実績値の関係変化（Concept Drift）を検知。
        同じモデルの RMSE / MAE / 相関係数が baseline→target で悪化していれば
        特徴量と目的変数の関係が変わった（= 再学習が必要）ことを示す。
        """
        from backend.app.services.stuff_plus_service import StuffPlusService

        stuff_svc = StuffPlusService()
        artifact = stuff_svc._ensure_model_loaded(model_type)
        xgb_model = artifact["model"]
        encoded_columns = artifact["encoded_columns"]
        features = artifact["features"]

        logger.info(
            f"Concept drift detection: {model_type} "
            f"({baseline_season} vs {target_season})"
        )

        metrics_base = self._compute_pred_vs_actual(
            xgb_model, encoded_columns, features,
            model_type, baseline_season,
        )
        metrics_tgt = self._compute_pred_vs_actual(
            xgb_model, encoded_columns, features,
            model_type, target_season,
        )

        if metrics_base is None or metrics_tgt is None:
            return DriftReport(
                model_type=model_type,
                drift_type="concept",
                baseline_season=baseline_season,
                target_season=target_season,
                summary="データ不足: Concept Drift 検知を実行できませんでした。",
            )

        rmse_change = (
            ((metrics_tgt["rmse"] - metrics_base["rmse"])
             / metrics_base["rmse"]) * 100
            if metrics_base["rmse"] != 0 else 0.0
        )
        corr_degradation = metrics_base["corr"] - metrics_tgt["corr"]

        # Concept Drift 判定:
        # - RMSE が 20% 以上悪化 → critical
        # - RMSE が 10% 以上悪化 or 相関が 0.1 以上低下 → warning
        if rmse_change >= 20 or corr_degradation >= 0.15:
            severity, drift_detected = "critical", True
        elif rmse_change >= 10 or corr_degradation >= 0.05:
            severity, drift_detected = "warning", True
        else:
            severity, drift_detected = "none", False

        concept_result = ConceptDriftResult(
            rmse_baseline=round(metrics_base["rmse"], 6),
            rmse_target=round(metrics_tgt["rmse"], 6),
            rmse_change_pct=round(rmse_change, 2),
            mae_baseline=round(metrics_base["mae"], 6),
            mae_target=round(metrics_tgt["mae"], 6),
            corr_baseline=round(metrics_base["corr"], 4),
            corr_target=round(metrics_tgt["corr"], 4),
            corr_degradation=round(corr_degradation, 4),
            drift_detected=drift_detected,
            severity=severity,
        )

        summary = self._build_concept_drift_summary(
            model_type, baseline_season, target_season,
            concept_result,
        )

        report = DriftReport(
            model_type=model_type,
            drift_type="concept",
            baseline_season=baseline_season,
            target_season=target_season,
            concept_drift=concept_result,
            overall_drift_detected=drift_detected,
            summary=summary,
        )

        logger.info(
            f"Concept drift complete: severity={severity}, "
            f"RMSE {metrics_base['rmse']:.6f}→{metrics_tgt['rmse']:.6f} "
            f"({rmse_change:+.1f}%)"
        )
        return report

    # ----------------------------------------------------------
    # Private: シーズン全体の予測値を取得
    # ----------------------------------------------------------

    def _predict_season(
        self, model, encoded_columns, features,
        model_type, season,
    ) -> Optional[np.ndarray]:
        """Statcast データを取得し、モデルで全ピッチの予測値を返す"""
        from backend.app.services.stuff_plus_service import STATCAST_COLUMNS
        import xgboost as xgb

        cols = ", ".join(STATCAST_COLUMNS)
        query = f"""
            SELECT {cols}
            FROM `{settings.get_table_full_name('statcast_master')}`
            WHERE game_year = @season
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
                AND delta_pitcher_run_exp IS NOT NULL
            LIMIT 200000
        """
        from google.cloud import bigquery as bq
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("season", "INT64", season),
            ]
        )

        try:
            df = self.client.query(query, job_config=job_config).to_dataframe()
        except Exception as e:
            logger.error(f"Failed to fetch data for season {season}: {e}")
            return None

        if df.empty:
            return None

        # plate_z_norm
        sz_range = df["sz_top"] - df["sz_bot"]
        df["plate_z_norm"] = np.where(
            sz_range > 0,
            (df["plate_z"] - df["sz_bot"]) / sz_range,
            np.nan,
        )

        # Pitching++ 用特徴量
        if model_type == "pitching_plus_plus":
            df = df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
            grp = df.groupby(["game_pk", "at_bat_number"])
            df["prev_release_pos_x"] = grp["release_pos_x"].shift(1)
            df["prev_release_pos_z"] = grp["release_pos_z"].shift(1)
            df["prev_release_speed"] = grp["release_speed"].shift(1)
            df["prev_pfx_z"] = grp["pfx_z"].shift(1)
            df["prev_pitch_type"] = grp["pitch_type"].shift(1)

            df["release_diff"] = np.sqrt(
                (df["release_pos_x"] - df["prev_release_pos_x"]) ** 2
                + (df["release_pos_z"] - df["prev_release_pos_z"]) ** 2
            )
            df["speed_diff"] = df["release_speed"] - df["prev_release_speed"]
            df["zone_distance"] = np.sqrt(
                df["plate_x"] ** 2 + (df["plate_z_norm"] - 0.5) ** 2
            )
            df["release_diff"] = df["release_diff"].fillna(0)
            df["speed_diff"] = df["speed_diff"].fillna(0)
            df["prev_pfx_z"] = df["prev_pfx_z"].fillna(df["pfx_z"])
            df["prev_pitch_type"] = df["prev_pitch_type"].fillna("NONE")

        cat_cols = (
            ["pitch_type", "prev_pitch_type"]
            if model_type == "pitching_plus_plus"
            else ["pitch_type"]
        )

        df_clean = df.dropna(
            subset=features + ["delta_pitcher_run_exp"]
        ).copy()
        if df_clean.empty:
            return None

        df_encoded = pd.get_dummies(
            df_clean[features + cat_cols], columns=cat_cols
        )
        for col in encoded_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_encoded = df_encoded[encoded_columns]

        predictions = model.predict(df_encoded)
        return predictions

    # ----------------------------------------------------------
    # Private: Predicted vs Actual の誤差メトリクス計算
    # ----------------------------------------------------------

    def _compute_pred_vs_actual(
        self, model, encoded_columns, features,
        model_type, season,
    ) -> Optional[Dict]:
        """予測と実績の RMSE / MAE / 相関を計算"""
        from backend.app.services.stuff_plus_service import STATCAST_COLUMNS

        cols = ", ".join(STATCAST_COLUMNS)
        query = f"""
            SELECT {cols}
            FROM `{settings.get_table_full_name('statcast_master')}`
            WHERE game_year = @season
                AND pitch_type IS NOT NULL
                AND release_speed IS NOT NULL
                AND delta_pitcher_run_exp IS NOT NULL
            LIMIT 200000
        """
        from google.cloud import bigquery as bq
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("season", "INT64", season),
            ]
        )

        try:
            df = self.client.query(query, job_config=job_config).to_dataframe()
        except Exception as e:
            logger.error(f"Failed to fetch data for season {season}: {e}")
            return None

        if df.empty:
            return None

        # plate_z_norm
        sz_range = df["sz_top"] - df["sz_bot"]
        df["plate_z_norm"] = np.where(
            sz_range > 0,
            (df["plate_z"] - df["sz_bot"]) / sz_range,
            np.nan,
        )

        # Pitching++ 用特徴量
        if model_type == "pitching_plus_plus":
            df = df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
            grp = df.groupby(["game_pk", "at_bat_number"])
            df["prev_release_pos_x"] = grp["release_pos_x"].shift(1)
            df["prev_release_pos_z"] = grp["release_pos_z"].shift(1)
            df["prev_release_speed"] = grp["release_speed"].shift(1)
            df["prev_pfx_z"] = grp["pfx_z"].shift(1)
            df["prev_pitch_type"] = grp["pitch_type"].shift(1)

            df["release_diff"] = np.sqrt(
                (df["release_pos_x"] - df["prev_release_pos_x"]) ** 2
                + (df["release_pos_z"] - df["prev_release_pos_z"]) ** 2
            )
            df["speed_diff"] = df["release_speed"] - df["prev_release_speed"]
            df["zone_distance"] = np.sqrt(
                df["plate_x"] ** 2 + (df["plate_z_norm"] - 0.5) ** 2
            )
            df["release_diff"] = df["release_diff"].fillna(0)
            df["speed_diff"] = df["speed_diff"].fillna(0)
            df["prev_pfx_z"] = df["prev_pfx_z"].fillna(df["pfx_z"])
            df["prev_pitch_type"] = df["prev_pitch_type"].fillna("NONE")

        cat_cols = (
            ["pitch_type", "prev_pitch_type"]
            if model_type == "pitching_plus_plus"
            else ["pitch_type"]
        )

        df_clean = df.dropna(
            subset=features + ["delta_pitcher_run_exp"]
        ).copy()
        if df_clean.empty:
            return None

        df_encoded = pd.get_dummies(
            df_clean[features + cat_cols], columns=cat_cols
        )
        for col in encoded_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_encoded = df_encoded[encoded_columns]

        predicted = model.predict(df_encoded)
        actual = df_clean["delta_pitcher_run_exp"].values

        rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
        mae = float(np.mean(np.abs(predicted - actual)))
        corr = float(np.corrcoef(predicted, actual)[0, 1])

        return {"rmse": rmse, "mae": mae, "corr": corr}

    # ----------------------------------------------------------
    # Private: Summary Builders
    # ----------------------------------------------------------

    @staticmethod
    def _build_summary(
        model_type: str,
        baseline: int,
        target: int,
        critical: List[str],
        warning: List[str],
    ) -> str:
        """Generate summary message for feature drift."""
        if not critical and not warning:
            return (
                f"{model_type}: {baseline}→{target} シーズン間でデータドリフトは"
                f"検出されませんでした。モデルは安定した入力データで動作しています。"
            )

        parts = [f"{model_type}: {baseline}→{target} シーズン間でドリフトを検出。"]
        if critical:
            parts.append(f"CRITICAL: {', '.join(critical)}")
        if warning:
            parts.append(f"Warning: {', '.join(warning)}")
        parts.append("モデルの再学習を検討してください。")

        return " ".join(parts)

    @staticmethod
    def _build_prediction_drift_summary(
        model_type: str,
        baseline: int,
        target: int,
        result: PredictionDriftResult,
    ) -> str:
        """Generate summary for prediction drift."""
        if not result.drift_detected:
            return (
                f"{model_type}: {baseline}→{target} の予測分布は安定しています。"
                f"(平均スコア: {result.score_baseline:.1f}→{result.score_target:.1f})"
            )
        parts = [
            f"{model_type}: {baseline}→{target} で予測分布のドリフトを検出。",
            f"平均スコア: {result.score_baseline:.1f}→{result.score_target:.1f}",
            f"(PSI={result.psi_value:.4f}, severity={result.severity})",
        ]
        if result.severity == "critical":
            parts.append("モデルの再学習を強く推奨します。")
        return " ".join(parts)

    @staticmethod
    def _build_concept_drift_summary(
        model_type: str,
        baseline: int,
        target: int,
        result: ConceptDriftResult,
    ) -> str:
        """Generate summary for concept drift."""
        if not result.drift_detected:
            return (
                f"{model_type}: {baseline}→{target} の予測精度は維持されています。"
                f"(RMSE: {result.rmse_baseline:.6f}→{result.rmse_target:.6f}, "
                f"相関: {result.corr_baseline:.4f}→{result.corr_target:.4f})"
            )
        parts = [
            f"{model_type}: {baseline}→{target} でConcept Driftを検出。",
            f"RMSE: {result.rmse_baseline:.6f}→{result.rmse_target:.6f} "
            f"({result.rmse_change_pct:+.1f}%)",
            f"相関: {result.corr_baseline:.4f}→{result.corr_target:.4f}",
        ]
        if result.severity == "critical":
            parts.append(
                "特徴量と結果の関係が大きく変化しています。再学習を強く推奨します。"
            )
        else:
            parts.append("再学習を検討してください。")
        return " ".join(parts)


        