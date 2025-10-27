from fastapi import APIRouter, Query, HTTPException
from backend.app.services.pitcher_substitution_ml import PitcherSubstitutionMLService

router = APIRouter()

@router.get("/pitcher-substitution-ml")
async def predict_pitcher_substitution(
    pitcher_name: str = Query(..., description="Pitcher name"),
    season: int = Query(2025, ge=2021, le=2025, description="Season")
):
    """
    【MLモデルを使った投手交代推奨予測】
    
    各イニング終了後に投手を交代すべきかをMLモデルで予測
    - fatigue_probability: 次イニングで疲労する確率（0.0～1.0）
    - recommendation: SUBSTITUTE（交代推奨）or CONTINUE（続投推奨）
    """
    service = PitcherSubstitutionMLService()
    result = service.predict_substitution(pitcher_name, season)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result