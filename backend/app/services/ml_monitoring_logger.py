"""
ML Monitoring Logger Service
ドリフト検知結果を BigQuery に非同期で記録するサービス。

llm_logger_service.py と同じパターン:
- 非同期書き込み (threading)
- シングルトンインスタンス
- メインスレッドをブロックしない設計
"""
import os
import uuid
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import asdict
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# BigQuery 設定
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
TABLE_ID = "ml_drift_monitoring_logs"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


class MLMonitoringLogger:
    """ドリフト検知結果を BigQuery に記録するサービス"""

    def __init__(self):
        self.client: Optional[bigquery.Client] = None
        try:
            self.client = bigquery.Client(project=PROJECT_ID)
            logger.info(f"MLMonitoringLogger initialized for {FULL_TABLE_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize MLMonitoringLogger: {e}")
    
    def log_drift_report(self, report) -> None:
        """
        DriftReport を非同期で BigQuery に書き込む。

        drift_type に応じて記録形式を変える:
        - "feature": 各特徴量を個別行として記録
        - "prediction": prediction_drift を1行として記録
        - "concept": concept_drift を1行として記録

        Args:
            report: DriftReport インスタンス
        """
        if not self.client:
            logger.warning("MLMonitoringLogger not initialized, skipping log")
            return

        drift_type = getattr(report, "drift_type", "feature")
        rows = []

        if drift_type == "feature" and report.features:
            for feature in report.features:
                rows.append({
                    "log_id": str(uuid.uuid4()),
                    "timestamp": report.timestamp,
                    "report_id": report.report_id,
                    "model_type": report.model_type,
                    "drift_type": drift_type,
                    "baseline_season": report.baseline_season,
                    "target_season": report.target_season,
                    "feature_name": feature.feature_name,
                    "ks_statistic": feature.ks_statistic,
                    "ks_p_value": feature.ks_p_value,
                    "psi_value": feature.psi_value,
                    "mean_baseline": feature.mean_baseline,
                    "mean_target": feature.mean_target,
                    "mean_shift_pct": feature.mean_shift_pct,
                    "drift_detected": feature.drift_detected,
                    "severity": feature.severity,
                    "overall_drift_detected": report.overall_drift_detected,
                })

        elif drift_type == "prediction" and report.prediction_drift:
            pd_result = report.prediction_drift
            rows.append({
                "log_id": str(uuid.uuid4()),
                "timestamp": report.timestamp,
                "report_id": report.report_id,
                "model_type": report.model_type,
                "drift_type": drift_type,
                "baseline_season": report.baseline_season,
                "target_season": report.target_season,
                "feature_name": "predicted_run_exp",
                "ks_statistic": pd_result.ks_statistic,
                "ks_p_value": pd_result.ks_p_value,
                "psi_value": pd_result.psi_value,
                "mean_baseline": pd_result.mean_baseline,
                "mean_target": pd_result.mean_target,
                "mean_shift_pct": pd_result.mean_shift_pct,
                "drift_detected": pd_result.drift_detected,
                "severity": pd_result.severity,
                "overall_drift_detected": report.overall_drift_detected,
            })

        elif drift_type == "concept" and report.concept_drift:
            cd_result = report.concept_drift
            rows.append({
                "log_id": str(uuid.uuid4()),
                "timestamp": report.timestamp,
                "report_id": report.report_id,
                "model_type": report.model_type,
                "drift_type": drift_type,
                "baseline_season": report.baseline_season,
                "target_season": report.target_season,
                "feature_name": "concept_pred_vs_actual",
                "ks_statistic": 0.0,
                "ks_p_value": 0.0,
                "psi_value": 0.0,
                "mean_baseline": cd_result.rmse_baseline,
                "mean_target": cd_result.rmse_target,
                "mean_shift_pct": cd_result.rmse_change_pct,
                "drift_detected": cd_result.drift_detected,
                "severity": cd_result.severity,
                "overall_drift_detected": report.overall_drift_detected,
            })

        if not rows:
            logger.warning(
                f"No rows to log for drift report "
                f"{report.report_id} (drift_type={drift_type})"
            )
            return

        thread = threading.Thread(
            target=self._write_rows_to_bigquery,
            args=(rows,),
            daemon=True,
        )
        thread.start()
    
    def get_drift_history(
        self, model_type: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        指定モデルのドリフト検知履歴を取得。
        Args:
            model_type: 監視対象モデル名
            limit: 取得件数の上限
        Returns:
            履歴レコードのリスト
        """
        if not self.client:
            return []
        query = f"""
            SELECT *
            FROM `{FULL_TABLE_ID}`
            WHERE model_type = @model_type
            ORDER BY timestamp DESC
            LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
                bigquery.ScalarQueryParameter(
                    "limit", "INT64", limit
                ),
            ]
        )
        try:
            result = self.client.query(query, job_config=job_config)
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Failed to fetch drift history: {e}")
            return []
    
    def get_latest_summary(self, model_type: str) -> Optional[Dict]:
        """最新のドリフトサマリを取得"""
        if not self.client:
            return None
        query = f"""
            SELECT
                report_id,
                model_type,
                baseline_season,
                target_season,
                timestamp,
                overall_drift_detected,
                COUNTIF(drift_detected) AS drifted_feature_count,
                COUNT(*) AS total_feature_count,
                MAX(psi_value) AS max_psi,
                ARRAY_AGG(
                    STRUCT(feature_name, severity, psi_value)
                    ORDER BY psi_value DESC
                ) AS feature_details
            FROM `{FULL_TABLE_ID}`
            WHERE model_type = @model_type
                AND report_id = (
                    SELECT report_id FROM `{FULL_TABLE_ID}`
                    WHERE model_type = @model_type
                    ORDER BY timestamp DESC LIMIT 1
                )
            GROUP BY report_id, model_type, baseline_season,
                     target_season, timestamp, overall_drift_detected
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
            ]
        )
        try:
            rows = list(self.client.query(query, job_config=job_config))
            return dict(rows[0]) if rows else None
        except Exception as e:
            logger.error(f"Failed to fetch drift summary: {e}")
            return None
    
    def _write_rows_to_bigquery(self, rows: List[Dict]) -> None:
        """BigQuery に複数行を挿入（内部用・別スレッドで実行）"""
        try:
            errors = self.client.insert_rows_json(FULL_TABLE_ID, rows)
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.debug(
                    f"ML drift log written: {len(rows)} rows"
                )
        except Exception as e:
            logger.error(f"Failed to write ML drift log: {e}")


# Singleton instance
_monitoring_logger_instance: Optional[MLMonitoringLogger] = None


def get_ml_monitoring_logger() -> MLMonitoringLogger:
    """シングルトンの MLMonitoringLogger を取得"""
    global _monitoring_logger_instance
    if _monitoring_logger_instance is None:
        _monitoring_logger_instance = MLMonitoringLogger()
    return _monitoring_logger_instance