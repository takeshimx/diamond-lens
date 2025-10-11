from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
# サービス層とスキーマをインポート
from backend.app.services.ai_service import get_ai_response_with_simple_chart # For Development, add backend. path
from backend.app.api.schemas import QnARequest # For Development, add backend. path
from backend.app.utils.structured_logger import get_logger
from backend.app.services.monitoring_service import get_monitoring_service
import logging
import time

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger("diamond-lens")
monitoring = get_monitoring_service()

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

    # Structured logging for query
    structured_logger.info(
        "Player stats query received",
        query=request.query,
        season=request.season
    )

    try:
        logger.info("📊 Calling BigQuery service...")
        bq_start = time.time()

        # BigQuery処理
        # ... your BigQuery code ...

        bq_end = time.time()
        bq_latency = (bq_end - bq_start) * 1000
        logger.info(f"📊 BigQuery completed in {bq_end - bq_start:.2f} seconds")

        logger.info("🤖 Calling Gemini API...")
        gemini_start = time.time()

        # ai_response = get_ai_response_for_qna(request.query, request.season)
        # Use chart-enabled version for enhanced visualization
        ai_response = get_ai_response_with_simple_chart(request.query, request.season)

        gemini_end = time.time()
        logger.info(f"🤖 Gemini API completed in {gemini_end - gemini_start:.2f} seconds")

        total_time = time.time() - start_time
        total_time_ms = total_time * 1000
        logger.info(f"✅ Total request completed in {total_time:.2f} seconds")

        # Record processing metrics
        if ai_response and ai_response.get("query_info"):
            query_type = ai_response["query_info"].get("query_type", "unknown")
            monitoring.record_query_processing_time(query_type, total_time_ms)
            monitoring.record_bigquery_latency(query_type, bq_latency)

            structured_logger.info(
                "Query processed successfully",
                query_type=query_type,
                processing_time_ms=round(total_time_ms, 2),
                bigquery_latency_ms=round(bq_latency, 2)
            )

        if ai_response is None:
            logger.error("❌ AI response is None")
            monitoring.record_api_error("/qa/player-stats", "null_response")
            structured_logger.error("AI response is None")
            raise HTTPException(status_code=500, detail="Failed to generate AI response.")

        return ai_response

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Error after {elapsed_time:.2f} seconds: {str(e)}")

        # Determine error type
        error_type = "unknown_error"
        if "validation" in str(e).lower():
            error_type = "validation_error"
        elif "bigquery" in str(e).lower():
            error_type = "bigquery_error"
        elif "llm" in str(e).lower() or "gemini" in str(e).lower():
            error_type = "llm_error"

        monitoring.record_api_error("/qa/player-stats", error_type)
        structured_logger.error(
            "Query processing failed",
            error_type=error_type,
            error_message=str(e),
            elapsed_time_ms=round(elapsed_time * 1000, 2)
        )

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# テスト用のエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Backend is working"}

@router.post("/test-post")
async def test_post_endpoint(request: dict):
    return {"received": request, "timestamp": time.time()}