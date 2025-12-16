from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
from uuid import uuid4
# サービス層とスキーマをインポート
from backend.app.services.ai_service import get_ai_response_with_simple_chart # For Development, add backend. path
# 新しいインポート（テスト用）
# from backend.app.services.ai_service_refactored import get_ai_response_with_simple_chart
from backend.app.services.conversation_service import get_conversation_service

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
    summary="選手/チームの統計情報に関するQ&AをAIで生成（会話履歴対応）",
    description="ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。会話履歴を考慮して代名詞や省略を自動解決します。",
    tags=["players"] # 選手に関連するため 'players' タグを使用
)
async def get_player_stats_qna_endpoint(
    request: QnARequest # リクエストボディからQnARequestモデルを受け取る
    # query: str,
    # season: Optional[int] = None
) -> Dict[str, Any]:
    """
    ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。
    会話履歴機能: session_idを指定することで、過去の会話を参照して「彼」などの代名詞を自動解決します。
    """
    # セッションIDがない場合は新規作成
    session_id = request.session_id or str(uuid4())

    start_time = time.time()
    logger.info(f"🚀 Request received: query='{request.query}', season={request.season}, session_id={session_id}")

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
        # Use chart-enabled version for enhanced visualization (会話履歴対応)
        ai_response = get_ai_response_with_simple_chart(
            request.query,
            request.season,
            session_id=session_id  # ★ セッションIDを渡す ★
        )

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

        # ★ レスポンスにセッションIDを含める ★
        ai_response["session_id"] = session_id

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

# ★★★ 新規エンドポイント: 会話履歴取得 ★★★
@router.get(
    "/qa/history/{session_id}",
    response_model=Dict[str, Any],
    summary="会話履歴を取得",
    description="指定されたセッションIDの会話履歴を取得します。",
    tags=["players"]
)
async def get_chat_history(session_id: str):
    """
    指定セッションの会話履歴を取得

    Args:
        session_id: セッションID

    Returns:
        会話履歴のリスト
    """
    conv_service = get_conversation_service()
    history = conv_service.get_chat_history(session_id)

    return {
        "session_id": session_id,
        "history": history,
        "count": len(history)
    }


# ★★★ 新規エンドポイント: 会話履歴クリア ★★★
@router.delete(
    "/qa/history/{session_id}",
    response_model=Dict[str, Any],
    summary="会話履歴をクリア",
    description="指定されたセッションIDの会話履歴を削除します。",
    tags=["players"]
)
async def clear_chat_history(session_id: str):
    """
    セッションの会話履歴を削除

    Args:
        session_id: セッションID

    Returns:
        削除成功メッセージ
    """
    conv_service = get_conversation_service()
    conv_service.clear_session(session_id)

    logger.info(f"🗑️ Session cleared: {session_id}")

    return {
        "message": "Session cleared successfully",
        "session_id": session_id
    }


# テスト用のエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Backend is working"}

@router.post("/test-post")
async def test_post_endpoint(request: dict):
    return {"received": request, "timestamp": time.time()}