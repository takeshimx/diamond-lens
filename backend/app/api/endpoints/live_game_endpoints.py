"""
MLB リアルタイム試合速報 エンドポイント
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.app.services.live_game_service import LiveGameService
from backend.app.services.live_fatigue_service import LiveFatigueService

router = APIRouter(tags=["Live Games"])
service = LiveGameService()
fatigue_service = LiveFatigueService()


@router.get("/live/games/highlights")
async def get_daily_highlights(date: str):
    """指定日（JST YYYY-MM-DD）の全試合ハイライトを返す"""
    try:
        return await service.get_daily_highlights(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/games/schedule")
async def get_scheduled_games(date: str):
    """指定日（YYYY-MM-DD）の試合予定一覧を返す"""
    try:
        return await service.get_scheduled_games(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/games/{game_pk}/boxscore")
async def get_game_boxscore(game_pk: int):
    """終了試合のボックススコア（投手・野手スタッツ）を返す"""
    try:
        return await service.get_boxscore(game_pk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/standings")
async def get_standings(season: int = None):
    """
    MLB順位表を返す（AL/NL 各ディビジョン別）

    - season: シーズン年（省略時は今年）
    """
    try:
        return await service.get_standings(season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/fatigue/baselines")
async def get_pitcher_baselines(
    pitchers: List[str] = Query(..., description="投手名リスト（MLB API形式: 'Gerrit Cole'）"),
    season: int = 2025,
):
    """複数投手のシーズン平均球速ベースライン（イニング1）を一括取得"""
    try:
        return fatigue_service.get_pitcher_baselines(pitchers, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
