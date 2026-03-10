from fastapi import APIRouter, Query, HTTPException
from backend.app.services.player_segmentation import PlayerSegmentationService


router = APIRouter()
service = PlayerSegmentationService()


@router.get("/batter-segmentation")
async def batter_segmentation(
    season: int = Query(2025, ge=2000, le=2026),
    min_pa: int = Query(300, ge=100, le=750),
    use_ft_transformer: bool = Query(default=False),
    force_local: bool = Query(default=False, description="強制的にローカルのK-meansを使用"),
):
    """
    Get batter segmentation using K-means clustering.

    - デフォルト: ローカルのK-meansを使用
    - USE_VERTEX_AI_ENDPOINT=true の場合: Vertex AI Endpoint を使用（失敗時はローカルにフォールバック）
    - force_local=true の場合: 強制的にローカルのK-meansを使用
    """

    result = await service.get_batter_segmentation(
        season=season, min_pa=min_pa,
        use_ft_transformer=use_ft_transformer,
        force_local=force_local,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.get("/pitcher-segmentation")
async def pitcher_segmentation(
    season: int = Query(2025, ge=2000, le=2026),
    min_ip: int = Query(90, ge=0, le=200),
    use_ft_transformer: bool = Query(default=False),
    force_local: bool = Query(default=False, description="強制的にローカルのK-meansを使用"),
):
    """
    Get pitcher segmentation using K-means clustering.

    - デフォルト: ローカルのK-meansを使用
    - USE_VERTEX_AI_ENDPOINT=true の場合: Vertex AI Endpoint を使用（失敗時はローカルにフォールバック）
    - force_local=true の場合: 強制的にローカルのK-meansを使用
    """

    result = await service.get_pitcher_segmentation(
        season=season, min_ip=min_ip,
        use_ft_transformer=use_ft_transformer,
        force_local=force_local,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result