from fastapi import APIRouter, Query, HTTPException
from backend.app.services.pitcher_fatigue import PitcherFatigueService

router = APIRouter()

@router.get("/pitcher-fatigue")
async def get_pitcher_fatigue(
    pitcher_name: str = Query(..., description="Pitcher name"),
    season: int = Query(2025, ge=2021, le=2025, description="Season")
):
    """特定投手のイニング別疲労分析"""
    service = PitcherFatigueService()
    result = service.get_pitcher_fatigue_analysis(pitcher_name, season)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result

@router.get("/pitcher-fatigue/league-average")
async def get_league_average_fatigue(
    season: int = Query(2025, ge=2021, le=2025, description="Season")
):
    """リーグ全体のイニング別平均疲労傾向"""
    service = PitcherFatigueService()
    result = service.get_league_average_fatigue(season)
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result