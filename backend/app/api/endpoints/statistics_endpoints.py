from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.app.services.statistical_analysis import StatisticalAnalysisService

router = APIRouter(prefix="/statistics", tags=["Statistics"])

@router.get("/predict-winrate")
async def predict_winrate(
    team_ops: float = Query(..., ge=0.0, le=2.000, description="The OPS (On-base Plus Slugging) value for the team."),
    team_era: float = Query(..., ge=0.0, le=10.000, description="The ERA (Earned Run Average) value for the team."),
    team_hrs_allowed: int = Query(..., ge=0, le=300, description="The number of home runs allowed by the team.")
):
    """
    Predict the win rate for a team based on their OPS (On-base Plus Slugging) value, ERA (Earned Run Average) value, and the number of home runs allowed.

    Args:
        team_ops: チームOPS（例: 0.750）
        team_era: チームERA（例: 3.50）
        team_hrs_allowed: チームHRs Allowed（例: 200）
    
    Returns:
        予測勝率、想定勝利数、モデル評価指標
    """
    service = StatisticalAnalysisService()
    result = service.predict_winrate_from_ops(team_ops, team_era, team_hrs_allowed)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/ops-sensitivity")
async def ops_sensitivity_analysis(
    fixed_era: float = Query(4.00, ge=0.0, le=10.0, description="固定するERA値（デフォルト: 4.00）"),
    fixed_hrs_allowed: int = Query(180, ge=0, le=300, description="固定する被本塁打数（デフォルト: 180）")
):
    """
    OPSの変化が勝率に与える影響を分析

    Args:
        fixed_era: 固定するERA値（デフォルト: 4.00 = リーグ平均）
        fixed_hrs_allowed: 固定する被本塁打数（デフォルト: 180 = リーグ平均）

    Returns:
        OPS 0.650 ~ 0.850 の範囲での予測結果リスト
    """
    service = StatisticalAnalysisService()
    result = service.get_ops_sensitivity_analysis(fixed_era, fixed_hrs_allowed)
    return {"data": result, "count": len(result)}


@router.get("/model-summary")
async def get_model_summary():
    """
    回帰モデルの評価指標とメタ情報を取得
    
    Returns:
        R², RMSE, MAE, 回帰係数、回帰式
    """
    service = StatisticalAnalysisService()
    result = service.get_model_summary()
    return result