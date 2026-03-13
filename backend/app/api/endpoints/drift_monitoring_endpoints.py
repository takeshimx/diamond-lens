"""
Drift Monitoring API Endpoints
MLモデル入力データのドリフト検知・監視エンドポイント
"""

import logging

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.app.services.data_drift_service import DataDriftService
from backend.app.services.ml_monitoring_logger import get_ml_monitoring_logger
from backend.app.services.model_registry_service import ModelRegistryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml-monitoring", tags=["ML Monitoring"])

service = DataDriftService()
monitoring_logger = get_ml_monitoring_logger()

# Registry for auto-baseline (fallback gracefully if unavailable)
try:
    registry = ModelRegistryService()
except Exception:
    registry = None


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
    model_type: str


# ============================================================
# エンドポイント
# ============================================================

@router.post("/detect-drift")
async def detect_drift(
    model_type: str,
    target_season: int,
    baseline_season: Optional[int] = Query(None),
):
    """
    MLモデル入力データのドリフト検知を実行。
    baseline_season が未指定の場合、Registry の active モデルから学習シーズンを自動取得する。
    """
    if baseline_season is None:
        if registry is None:
            raise HTTPException(
                status_code=400,
                detail="baseline_season is required (Model Registry unavailable)."
            )
        active = registry.get_active_version(model_type)
        if not active:
            raise HTTPException(
                status_code=400, 
                detail=f"baseline_season is required because no active model version was found for {model_type}."
            )
        baseline_season = active.training_season
        logger.info(f"Auto-selected baseline_season {baseline_season} for model {model_type} from registry")
    
    # 指定されたシーズンでドリフト検知実行
    report = service.detect_drift(
        baseline_season=baseline_season,
        target_season=target_season,
        model_type=model_type,
    )
    
    # Save log to BigQuery
    monitoring_logger.log_drift_report(report)

    return report


@router.post("/detect-prediction-drift")
async def detect_prediction_drift(
    model_type: str = Query(
        ...,
        description="stuff_plus / pitching_plus / pitching_plus_plus",
        pattern="^(stuff_plus|pitching_plus|pitching_plus_plus)$",
    ),
    target_season: int = Query(..., ge=2020, le=2026),
    baseline_season: Optional[int] = Query(None, ge=2020, le=2026),
):
    """
    Prediction Drift: モデル予測値の分布変化を検知。
    同じモデルで baseline / target の Statcast データを推論し、
    予測分布の KS / PSI を比較する。Stuff+ 系モデル専用。
    """
    if baseline_season is None:
        if registry is None:
            raise HTTPException(
                status_code=400,
                detail="baseline_season is required (Model Registry unavailable)."
            )
        active = registry.get_active_version(model_type)
        if not active:
            raise HTTPException(
                status_code=400,
                detail=f"baseline_season is required because no active model was found for {model_type}."
            )
        baseline_season = active.training_season

    try:
        report = service.detect_prediction_drift(
            baseline_season=baseline_season,
            target_season=target_season,
            model_type=model_type,
        )
        monitoring_logger.log_drift_report(report)
        return report
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction drift detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-concept-drift")
async def detect_concept_drift(
    model_type: str = Query(
        ...,
        description="stuff_plus / pitching_plus / pitching_plus_plus",
        pattern="^(stuff_plus|pitching_plus|pitching_plus_plus)$",
    ),
    target_season: int = Query(..., ge=2020, le=2026),
    baseline_season: Optional[int] = Query(None, ge=2020, le=2026),
):
    """
    Concept Drift: 予測精度の劣化を検知。
    同じモデルの RMSE / 相関係数が baseline→target で悪化していれば
    特徴量と目的変数の関係が変わった（= 再学習が必要）ことを示す。
    """
    if baseline_season is None:
        if registry is None:
            raise HTTPException(
                status_code=400,
                detail="baseline_season is required (Model Registry unavailable)."
            )
        active = registry.get_active_version(model_type)
        if not active:
            raise HTTPException(
                status_code=400,
                detail=f"baseline_season is required because no active model was found for {model_type}."
            )
        baseline_season = active.training_season

    try:
        report = service.detect_concept_drift(
            baseline_season=baseline_season,
            target_season=target_season,
            model_type=model_type,
        )
        monitoring_logger.log_drift_report(report)
        return report
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Concept drift detection failed: {e}")
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
