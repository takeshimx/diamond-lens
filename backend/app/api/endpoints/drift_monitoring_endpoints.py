"""
Drift Monitoring API Endpoints
MLモデル入力データのドリフト検知・監視エンドポイント
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.app.services.data_drift_service import DataDriftService
from backend.app.services.ml_monitoring_logger import get_ml_monitoring_logger

router = APIRouter(prefix="/ml-monitoring", tags=["ML Monitoring"])

service = DataDriftService()
monitoring_logger = get_ml_monitoring_logger()


# ============================================================
# レスポンスモデル
# ============================================================

class FeatureDriftResponse(BaseModel):
    feature_name: str
    ks_statistic: float
    ks_p_value: float
    psi_value: float
    mean_baseline: float
    mean_target: float
    mean_shift_pct: float
    drift_detected: bool
    severity: str


class DriftReportResponse(BaseModel):
    report_id: str
    model_type: str
    baseline_season: int
    target_season: int
    timestamp: str
    overall_drift_detected: bool
    summary: str
    features: List[FeatureDriftResponse]


class DriftDetectRequest(BaseModel):
    baseline_season: int
    target_season: int
    model_type: str  # "batter_segmentation" | "pitcher_segmentation"


# ============================================================
# エンドポイント
# ============================================================

@router.post("/detect-drift", response_model=DriftReportResponse)
async def detect_drift(request: DriftDetectRequest):
    """
    指定された2シーズン間のデータドリフトを検知する。

    結果は BigQuery にも自動的に記録される。
    """
    try:
        report = service.detect_drift(
            baseline_season=request.baseline_season,
            target_season=request.target_season,
            model_type=request.model_type,
        )

        # BigQuery にログを記録
        monitoring_logger.log_drift_report(report)

        return report.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift-history")
async def get_drift_history(
    model_type: str = Query(..., description="Model type to query"),
    limit: int = Query(30, ge=1, le=100),
):
    """過去のドリフト検知履歴を取得"""
    history = monitoring_logger.get_drift_history(
        model_type=model_type, limit=limit
    )
    return {"model_type": model_type, "history": history}


@router.get("/drift-summary")
async def get_drift_summary(
    model_type: str = Query(..., description="Model type to query"),
):
    """最新のドリフト検知サマリを取得"""
    summary = monitoring_logger.get_latest_summary(model_type)
    if not summary:
        return {
            "model_type": model_type,
            "message": "No drift detection records found.",
        }
    return summary
