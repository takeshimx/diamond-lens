"""
Data Drift Detection Service
MLモデル入力データの分布変化（データドリフト）を統計的に検知するサービス。
パイロット対象: player_segmentation.py の KMeans モデル
- 打者特徴量: ops, iso, k_rate, bb_rate
- 投手特徴量: era, k_9, gbpct
検知手法:
1. Kolmogorov-Smirnov (KS) 検定 — 2分布の統計的差異
2. Population Stability Index (PSI) — 分布安定性の業界標準指標
3. 平均値シフト検知 — 変化率ベースの直感的指標
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
class DriftReport:
    """ドリフト検知レポート"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: str = ""
    baseline_season: int = 0
    target_season: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    features: List[FeatureDriftResult] = field(default_factory=list)
    overall_drift_detected: bool = False
    summary: str = ""

    def to_dict(self) -> Dict:
        """API レスポンス用の辞書変換"""
        return {
            "report_id": self.report_id,
            "model_type": self.model_type,
            "baseline_season": self.baseline_season,
            "target_season": self.target_season,
            "timestamp": self.timestamp,
            "overall_drift_detected": self.overall_drift_detected,
            "summary": self.summary,
            "features": [asdict(f) for f in self.features],
        }


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

    @staticmethod
    def _build_summary(
        model_type: str,
        baseline: int,
        target: int,
        critical: List[str],
        warning: List[str],
    ) -> str:
        """Generate summary message."""
        if not critical and not warning:
            return (
                f"{model_type}: {baseline}→{target} シーズン間でデータドリフトは"
                f"検出されませんでした。モデルは安定した入力データで動作しています。"
            )
        
        parts = [f"{model_type}: {baseline}→{target} シーズン間でドリフトを検出。"]
        if critical:
            parts.append(f"🔴 CRITICAL: {', '.join(critical)}")
        if warning:
            parts.append(f"🟡 Warning: {', '.join(warning)}")
        parts.append("モデルの再学習を検討してください。")

        return " ".join(parts)
        




        