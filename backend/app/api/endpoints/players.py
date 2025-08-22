from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
# サービス層とスキーマをインポート
from backend.app.services.ai_service import get_ai_response_for_qna_enhanced
from backend.app.api.schemas import QnARequest
import logging
import time
# from services.ranking_queries import get_player_ranking_batch

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
# このルーターは、FastAPIアプリケーションの他の部分とは独立してエンドポイントを定義できます。
router = APIRouter()


 
@router.post(
    "/qa/player-stats", 
    response_model=Dict[str, Any],
    summary="選手/チームの統計情報に関するQ&AをAIで生成",
    description="ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。",
    tags=["players"] # 選手に関連するため 'players' タグを使用
)
async def get_player_stats_qna_endpoint(
    request: QnARequest # リクエストボディからQnARequestモデルを受け取る
    # query: str,
    # season: Optional[int] = None
) -> Dict[str, Any]:
    """
    ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。
    """
    start_time = time.time()
    logger.info(f"🚀 Request received: query='{request.query}', season={request.season}")
    
    try:
        logger.info("📊 Calling BigQuery service...")
        bq_start = time.time()
        
        # BigQuery処理
        # ... your BigQuery code ...
        
        bq_end = time.time()
        logger.info(f"📊 BigQuery completed in {bq_end - bq_start:.2f} seconds")
        
        logger.info("🤖 Calling Gemini API...")
        gemini_start = time.time()

        # ai_response = get_ai_response_for_qna(request.query, request.season)
        # testing
        ai_response = get_ai_response_for_qna_enhanced(request.query, request.season)

        gemini_end = time.time()
        logger.info(f"🤖 Gemini API completed in {gemini_end - gemini_start:.2f} seconds")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Total request completed in {total_time:.2f} seconds")
        
        if ai_response is None:
            logger.error("❌ AI response is None")
            raise HTTPException(status_code=500, detail="Failed to generate AI response.")
        
        return ai_response
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Error after {elapsed_time:.2f} seconds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# テスト用のエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Backend is working"}

@router.post("/test-post")
async def test_post_endpoint(request: dict):
    return {"received": request, "timestamp": time.time()}