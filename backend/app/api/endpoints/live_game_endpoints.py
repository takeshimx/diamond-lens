"""
MLB リアルタイム試合速報 エンドポイント
"""
from fastapi import APIRouter, HTTPException

from backend.app.services.live_game_service import LiveGameService

router = APIRouter(tags=["Live Games"])
service = LiveGameService()


@router.get("/live/games/today")
async def get_today_live_games():
    """
    本日進行中の全試合の現在状態を返す

    - 投手名・打者名・カウント (B-S-O)・スコア・イニングを含む
    - Live 試合がない場合は空配列を返す
    """
    try:
        return await service.get_today_live_games()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
