"""
試合終了サマリー自動投稿エンドポイント

Cloud Scheduler から定期的に叩かれることを想定。
LAD の試合終了を検知して Discord にサマリーを投稿する。
"""

from fastapi import APIRouter, HTTPException, Query
from backend.app.services.game_summary_service import GameSummaryService

router = APIRouter(tags=["Game Summary"])
service = GameSummaryService()


@router.post("/internal/summary/trigger")
async def trigger_lad_summary(date: str = Query(default=None, description="対象日 YYYY-MM-DD（省略時は今日）")):
    """
    LAD試合終了サマリーのトリガー（Cloud Scheduler から呼び出し）

    - LADの終了試合を検知
    - 未投稿のものに限りGeminiでサマリーを生成してDiscordへ投稿
    - GCSで投稿済み管理（重複投稿防止）
    - date 指定で過去日のテストも可能
    """
    try:
        result = await service.run(date=date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
