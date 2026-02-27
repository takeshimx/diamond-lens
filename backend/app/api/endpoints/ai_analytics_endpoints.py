from fastapi import APIRouter, HTTPException, Request
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
from backend.app.services.ai_agent_service import run_mlb_agent
from backend.app.services.llm_logger_service import get_llm_logger, LLMLogEntry
from backend.app.config.prompt_registry import get_prompt_version
from backend.app.middleware.request_id import get_request_id
from backend.app.core.exceptions import PromptInjectionError
import logging
import time

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger("diamond-lens")
monitoring = get_monitoring_service()
llm_logger = get_llm_logger()

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
    request_body: QnARequest, # リクエストボディからQnARequestモデルを受け取る
    request: Request,
    # query: str,
    # season: Optional[int] = None
) -> Dict[str, Any]:
    """
    ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。
    会話履歴機能: session_idを指定することで、過去の会話を参照して「彼」などの代名詞を自動解決します。
    """
    # セッションIDがない場合は新規作成
    session_id = request_body.session_id or str(uuid4())
    start_time = time.time()

    # ★ user_id をミドルウェアから取得
    user_id = getattr(request.state, "user_id", "anonymous")

    # ★ Guardrail チェック
    from backend.app.services.security_guardrail import get_security_guardrail
    guardrail = get_security_guardrail()
    is_safe, reason = guardrail.validate_and_log(request_body.query)
    if not is_safe:
        return {
            "answer": "申し訳ございませんが、このリクエストにはお応えできません。MLB統計に関する質問をお願いいたします。",
            "isTable": False,
            "isChart": False,
            "session_id": session_id,
            "blocked": True,
        }
    
    # LLM ログエントリを初期化
    log_entry = LLMLogEntry()
    log_entry.request_id = get_request_id()
    log_entry.user_id = user_id
    log_entry.session_id = session_id
    log_entry.user_query = request_body.query
    log_entry.endpoint = "/qa/player-stats"
    log_entry.prompt_name = "parse_query"
    log_entry.prompt_version = get_prompt_version("parse_query")

    # Structured logging for query
    structured_logger.info(
        "Player stats query received",
        query=request_body.query,
        season=request_body.season
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
            request_body.query,
            request_body.season,
            session_id=session_id  # ★ セッションIDを渡す ★
        )

        gemini_end = time.time()
        logger.info(f"🤖 Gemini API completed in {gemini_end - gemini_start:.2f} seconds")

        # ログエントリに結果を記録
        log_entry.llm_latency_ms = (gemini_end - gemini_start) * 1000
        log_entry.total_latency_ms = (time.time() - start_time) * 1000
        log_entry.bigquery_latency_ms = bq_latency

        total_time = time.time() - start_time
        total_time_ms = total_time * 1000
        logger.info(f"✅ Total request completed in {total_time:.2f} seconds")

        # Record processing metrics
        if ai_response and ai_response.get("query_info"):
            query_type = ai_response["query_info"].get("query_type", "unknown")
            log_entry.parsed_query_type = query_type
            log_entry.parsed_player_name = ai_response["query_info"].get("name")
            log_entry.parsed_season = ai_response["query_info"].get("season")
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
            log_entry.success = False
            log_entry.error_type = "null_response"
            llm_logger.log(log_entry)  # エラーもログに記録
            monitoring.record_api_error("/qa/player-stats", "null_response")
            structured_logger.error("AI response is None")
            raise HTTPException(status_code=500, detail="Failed to generate AI response.")
        
        # 成功時のログ記録
        log_entry.response_answer = ai_response.get("answer", "")
        log_entry.response_has_table = ai_response.get("isTable", False)
        log_entry.response_has_chart = ai_response.get("isChart", False)
        log_entry.success = True
        llm_logger.log(log_entry)

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
        
        log_entry.success = False
        log_entry.error_type = error_type
        log_entry.error_message = str(e)
        log_entry.total_latency_ms = (time.time() - start_time) * 1000
        llm_logger.log(log_entry)  # エラーもログに記録

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


@router.post(
    "/qa/agentic-stats",
    response_model=Dict[str, Any],
    summary="自律型エージェントによる高度な分析・Q&A",
    description="LangGraphを用いた自律型エージェントが、複雑な質問に対して複数ステップの推論を行い、回答を生成します。",
    tags=["agentic"]
)
async def get_agentic_stats_endpoint(
    request: QnARequest
) -> Dict[str, Any]:
    """
    自律型エージェント（LangGraph）を起動して回答を得るエンドポイント。
    """
    session_id = request.session_id or str(uuid4())
    start_time = time.time()
    
    logger.info(f"🤖 Agentic Request: query='{request.query}', session_id={session_id}")
    
    try:
        # 自律型エージェントの実行
        result_state = run_mlb_agent(request.query)
        
        # 1. 回答の取得（final_answer または 最後のメッセージから）
        answer = result_state.get("final_answer", "")
        if not answer:
            # final_answerが空の場合、メッセージ履歴の最後のAIメッセージを探す
            for msg in reversed(result_state.get("messages", [])):
                if msg.type == "ai" and msg.content:
                    answer = msg.content
                    break
        
        # 2. 思考プロセス（Steps）の抽出をより柔軟に
        steps = []
        for msg in result_state.get("messages", []):
            # ツール呼び出し（思考）の判定
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                tool_name = tool_calls[0].get("name", "データ検索") if isinstance(tool_calls[0], dict) else getattr(tool_calls[0], "name", "データ検索")
                steps.append({
                    "type": "thought",
                    "content": f"計画: {tool_name} を実行して情報を収集します。"
                })
            # ツール実行結果（実行）の判定
            elif msg.type == "tool" or hasattr(msg, "tool_call_id"):
                steps.append({
                    "type": "execution",
                    "content": "実行: データベースから必要な情報を取得しました。"
                })

        elapsed_time = time.time() - start_time
        logger.info(f"✅ Agentic request completed in {elapsed_time:.2f} seconds. Answer length: {len(answer)}, Steps: {len(steps)}")
        
        return {
            "query": request.query,
            "answer": answer or "回答を生成できませんでした。プロンプトまたはデータ取得に問題があります。",
            "steps": steps,
            "session_id": session_id,
            "processing_time_ms": round(elapsed_time * 1000, 2),
            "is_agentic": True,
            "isTable": result_state.get("isTable", False),
            "tableData": result_state.get("tableData"),
            "columns": result_state.get("columns"),
            "isTransposed": result_state.get("isTransposed", False),
            "isChart": result_state.get("isChart", False),
            "chartType": result_state.get("chartType"),
            "chartData": result_state.get("chartData"),
            "chartConfig": result_state.get("chartConfig"),
            "isMatchupCard": result_state.get("isMatchupCard", False),
            "matchupData": result_state.get("matchupData")
        }
    
    except PromptInjectionError as e:
        # Guardrailによるブロック → 400（クライアントエラー）として返す
        logger.warning(f"🚨 Guardrail blocked: {e.detected_pattern}", extra={"query": request.query[:100]})
        return {
            "query": request.query,
            "answer": e.message,  # 丁寧な拒否メッセージ
            "steps": [],
            "session_id": session_id,
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            "is_agentic": True,
            "isTable": False,
            "isChart": False,
            "blocked": True,  # フロントエンド側で判別するフラグ
            "blocked_reason": e.detected_pattern,
        }
    
    except Exception as e:
        logger.error(f"❌ Agentic Error: {str(e)}", exc_info=True)
        # エラー発生時は詳細を返却
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# テスト用のエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Backend is working"}

@router.post("/test-post")
async def test_post_endpoint(request: dict):
    return {"received": request, "timestamp": time.time()}