from fastapi import APIRouter, Query, HTTPException
from backend.app.services.player_segmentation import PlayerSegmentationService


router = APIRouter()
service = PlayerSegmentationService()


@router.get("/batter-segmentation")
async def batter_segmentation(
    season: int = Query(2025, ge=2000, le=2025), 
    min_pa: int = Query(300, ge=100, le=750)
):
    """Get batter segmentation using K-means clustering."""

    result = service.get_batter_segmentation(season=season, min_pa=min_pa)

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.get("/pitcher-segmentation")
async def pitcher_segmentation(
    season: int = Query(2025, ge=2000, le=2025), 
    min_ip: int = Query(90, ge=0, le=200)
):
    """Get pitcher segmentation using K-means clustering."""

    result = service.get_pitcher_segmentation(season=season, min_ip=min_ip)

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result