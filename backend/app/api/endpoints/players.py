from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
# サービス層とスキーマをインポート
from backend.app.services.player_service import *
from backend.app.api.schemas import *
import logging
# from services.ranking_queries import get_player_ranking_batch

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
# このルーターは、FastAPIアプリケーションの他の部分とは独立してエンドポイントを定義できます。
router = APIRouter()


 
@router.post(
    "/qa/player-stats", 
    response_model=str,
    summary="選手/チームの統計情報に関するQ&AをAIで生成",
    description="ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。",
    tags=["players"] # 選手に関連するため 'players' タグを使用
)
async def get_player_stats_qna_endpoint(
    request: QnARequest # リクエストボディからQnARequestモデルを受け取る
    # query: str,
    # season: Optional[int] = None
) -> str:
    """
    ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。
    """

    ai_response = get_ai_response_for_qna(request.query, request.season)

    if ai_response is None:
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")
    return ai_response