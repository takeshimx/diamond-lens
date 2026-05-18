from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List, Any, Dict, AsyncGenerator
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
from backend.app.middleware.request_context import (
    get_bq_latency_ms,
    reset_bq_latency_ms,
    set_session_id,
)
from backend.app.core.exceptions import PromptInjectionError
from fastapi.responses import StreamingResponse
from backend.app.utils.streaming import stream_json_events, format_sse
from backend.app.api.rate_limit import limiter
from backend.app.config.settings import get_settings
from backend.app.services.token_budget_service import get_token_budget_service
from backend.app.services.bq_embedding_service import get_bq_embedding_service
from backend.app.services.chat_orchestrator import ChatOrchestrator
import asyncio
import logging
import time
from pydantic import BaseModel

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger("diamond-lens")
# NOTE: monitoring / llm_logger はモジュールimport時にBigQuery/Monitoring
# クライアントを初期化して起動を遅延させていたため、各エンドポイント関数の
# 冒頭で `get_*()` を呼ぶ形に変更（シングルトンなので初回のみ初期化される）。

# APIRouterインスタンスを作成
# このルーターは、FastAPIアプリケーションの他の部分とは独立してエンドポイントを定義できます。
router = APIRouter()

# 動的リミット関数: リクエストごとに settings から値を取得
def _player_stats_limit() -> str:
    return f"{get_settings().rate_limit_player_stats_per_minute}/minute"

def _agent_chat_limit() -> str:
    return f"{get_settings().rate_limit_agent_chat_per_minute}/minute"


@router.post(
    "/qa/player-stats",
    response_model=Dict[str, Any],
    summary="選手/チームの統計情報に関するQ&AをAIで生成（会話履歴対応）",
    description="ユーザーの自然言語クエリに基づいて、AIが選手/チームの統計情報に関する回答を生成します。会話履歴を考慮して代名詞や省略を自動解決します。",
    tags=["players"] # 選手に関連するため 'players' タグを使用
)
@limiter.limit(_player_stats_limit)
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
    monitoring = get_monitoring_service()
    llm_logger = get_llm_logger()
    # セッションIDがない場合は新規作成
    session_id = request_body.session_id or str(uuid4())
    set_session_id(session_id)
    reset_bq_latency_ms()

    # トークンバジェットチェック
    token_budget = get_token_budget_service()
    if token_budget.is_budget_exceeded("chat"):
        return {
            "answer": "本日のAI分析サービスの利用上限に達しました。明日以降に再度お試しください。",
            "isTable": False,
            "isChart": False,
            "session_id": session_id,
            "service_at_capacity": True,
        }
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

        logger.info("🤖 Calling Gemini API + Quality Warning Check (parallel)...")
        gemini_start = time.time()

        # AI レスポンス生成と BQ 類似クエリ品質チェックを並列実行
        # asyncio.to_thread: 同期関数をスレッドプールで実行し await で待つ
        # asyncio.gather: 複数の非同期タスクを並列実行し、全完了を待つ
        ai_response, warning_result = await asyncio.gather(
            asyncio.to_thread(
                get_ai_response_with_simple_chart,
                request_body.query,
                request_body.season,
                session_id=session_id,
            ),
            asyncio.to_thread(
                get_bq_embedding_service().check_quality_warning,
                request_body.query,
            ),
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

        # ★ レスポンスにセッションIDと品質警告フラグを含める ★
        ai_response["session_id"] = session_id
        ai_response["quality_warning"] = warning_result

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
@limiter.limit(_agent_chat_limit)
async def get_agentic_stats_endpoint(
    request: Request,
    body: QnARequest,
) -> Dict[str, Any]:
    """
    自律型エージェント（LangGraph）を起動して回答を得るエンドポイント。
    """
    llm_logger = get_llm_logger()
    session_id = body.session_id or str(uuid4())
    set_session_id(session_id)
    reset_bq_latency_ms()

    # トークンバジェットチェック
    token_budget = get_token_budget_service()
    if token_budget.is_budget_exceeded("chat"):
        return {
            "query": body.query,
            "answer": "本日のAI分析サービスの利用上限に達しました。明日以降に再度お試しください。",
            "steps": [],
            "session_id": session_id,
            "is_agentic": True,
            "isTable": False,
            "isChart": False,
            "service_at_capacity": True,
        }

    start_time = time.time()

    # LLM ログエントリを初期化
    log_entry = LLMLogEntry()
    log_entry.request_id = get_request_id()
    log_entry.user_id = getattr(request.state, "user_id", "anonymous")
    log_entry.session_id = session_id
    log_entry.user_query = body.query
    log_entry.endpoint = "/qa/agentic-stats"

    logger.info(f"🤖 Agentic Request: query='{body.query}', session_id={session_id}")

    try:
        # 自律型エージェントの実行
        result_state = run_mlb_agent(body.query)
        
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

        # ログエントリに結果を記録
        log_entry.total_latency_ms = elapsed_time * 1000
        log_entry.bigquery_latency_ms = get_bq_latency_ms() or None
        log_entry.response_answer = answer
        log_entry.response_has_table = result_state.get("isTable", False)
        log_entry.response_has_chart = result_state.get("isChart", False)
        log_entry.routing_result = "agentic"  # エージェント経由であることを記録
        log_entry.success = True

        # Reflection Loop情報が含まれている場合は記録
        if "retry_count" in result_state and result_state["retry_count"] > 0:
            log_entry.is_retry = True
            log_entry.retry_count = result_state["retry_count"]
            # retry_reasonの判定
            if result_state.get("last_error"):
                log_entry.retry_reason = "sql_error"
            elif result_state.get("last_query_result_count") == 0:
                log_entry.retry_reason = "empty_result"
            else:
                log_entry.retry_reason = "unknown"

        llm_logger.log(log_entry)

        return {
            "query": body.query,
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
        logger.warning(f"🚨 Guardrail blocked: {e.detected_pattern}", extra={"query": body.query[:100]})

        # ログに記録
        log_entry.success = False
        log_entry.error_type = "prompt_injection"
        log_entry.error_message = e.detected_pattern
        log_entry.total_latency_ms = (time.time() - start_time) * 1000
        llm_logger.log(log_entry)

        return {
            "query": body.query,
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

        # ログに記録
        log_entry.success = False
        log_entry.error_type = "agent_error"
        log_entry.error_message = str(e)
        log_entry.total_latency_ms = (time.time() - start_time) * 1000
        llm_logger.log(log_entry)

        # エラー発生時は詳細を返却
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


class FeedbackRequest(BaseModel):
    session_id: str
    request_id: str
    user_rating: str
    category: Optional[str] = None
    reason: Optional[str] = None

@router.post("/qa/feedback")
async def submit_llm_feedback(feedback: FeedbackRequest):
    """ユーザーからのAI回答フィードバックを記録する"""
    try:
        llm_logger = get_llm_logger()
        llm_logger.update_feedback(
            request_id=feedback.request_id,
            session_id=feedback.session_id,
            user_rating=feedback.user_rating,
            category=feedback.category,
            reason=feedback.reason
        )
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Feedback error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to log feedback")


@router.post(
    "/qa/agentic-stats-stream",
    summary="自律型エージェントによる高度な分析・Q&A (ストリーミング版)",
    description="LangGraphを用いた自律型エージェントが、複雑な質問に対してリアルタイムでストリーミング回答を生成します。",
    tags=["agentic"],
    response_class=StreamingResponse
)
@limiter.limit(_agent_chat_limit)
async def get_agentic_stats_stream_endpoint(
    request: Request,
    body: QnARequest,
) -> StreamingResponse:
    """
    自律型エージェント（LangGraph）をストリーミングモードで起動するエンドポイント。
    Server-Sent Events (SSE) を使用して、リアルタイムで結果を送信します。
    """
    session_id = body.session_id or str(uuid4())
    # ContextVar にセット → 下流の call_gemini ログにも auto-populate される
    set_session_id(session_id)
    reset_bq_latency_ms()

    # トークンバジェットチェック
    token_budget = get_token_budget_service()
    if token_budget.is_budget_exceeded("chat"):
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service at capacity",
                "detail": "本日のAI分析サービスの利用上限に達しました。明日以降に再度お試しください。",
                "session_id": session_id,
                "service_at_capacity": True,
            },
        )

    # output_format が指定されている場合はクエリにヒントを付与して LLM 判定を誘導する
    resolved_query = body.query
    if body.output_format == "table":
        resolved_query = f"{body.query} 表で"
    elif body.output_format == "text":
        resolved_query = f"{body.query} テキストで"

    logger.info(f"🌊 Stream Request: query='{resolved_query}', session_id={session_id}")

    # LLMログエントリを初期化
    llm_logger = get_llm_logger()
    log_entry = LLMLogEntry()
    log_entry.request_id = get_request_id()
    log_entry.user_id = getattr(request.state, "user_id", "anonymous")
    log_entry.session_id = session_id
    log_entry.user_query = body.query
    log_entry.endpoint = "/qa/agentic-stats-stream"
    log_entry.success = True
    stream_start_time = time.time()

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """SSEイベントを生成する非同期ジェネレーター"""
        # エンドポイントレベルで全トークンを蓄積。
        # run_mlb_agent_stream の synthesizer 捕捉ロジックが取りこぼした場合の
        # 最終フォールバックとして使用する。
        endpoint_accumulated_answer = ""
        try:
            # Session start event
            yield {
                "type": "session_start",
                "session_id": session_id,
                "query": body.query
            }

            # Agent start event
            yield {
                "type": "agent_start",
                "message": "エージェントが質問を分析しています..."
            }

            # Feature flag による新旧切替（Phase 2 移行期間）
            settings = get_settings()
            if settings.use_legacy_chat_agent:
                from backend.app.services.ai_agent_service import run_mlb_agent_stream
                event_iter = run_mlb_agent_stream(
                    resolved_query,
                    request_id=log_entry.request_id,
                    session_id=session_id,
                    user_id=log_entry.user_id,
                )
            else:
                orchestrator = ChatOrchestrator()
                event_iter = orchestrator.run_stream(
                    resolved_query,
                    request_id=log_entry.request_id,
                    session_id=session_id,
                    user_id=log_entry.user_id,
                )
            
            async for event in event_iter:
                event_type = event.get("type")
                # トークンを無条件で蓄積（current_node 等のフィルタは介在しない）
                if event_type == "token":
                    content = event.get("content")
                    if content:
                        endpoint_accumulated_answer += content
                if event_type == "final_answer":
                    # event["answer"] が None/"" の場合、エンドポイント蓄積にフォールバック
                    log_entry.response_answer = (
                        event.get("answer")
                        or endpoint_accumulated_answer
                        or ""
                    )
                    log_entry.response_has_table = event.get("isTable", False)
                    log_entry.response_has_chart = event.get("isChart", False)
                    log_entry.llm_latency_ms = event.get("llm_latency_ms")
                    # ChatOrchestrator が tool 戻り値から集計した BQ 時間を受け取る
                    # (ContextVar 経由が StreamingResponse 配下で伝わらないための回避策)
                    _event_bq_ms = event.get("bigquery_latency_ms")
                    if _event_bq_ms:
                        log_entry.bigquery_latency_ms = _event_bq_ms
                yield event

            # Session end event
            yield {
                "type": "stream_end",
                "message": "処理が完了しました"
            }

            # 最終フォールバック: final_answer イベント自体が来なかった/空だった場合
            if not log_entry.response_answer and endpoint_accumulated_answer:
                log_entry.response_answer = endpoint_accumulated_answer
                logger.warning(
                    f"final_answer event missing/empty; recovered from endpoint token "
                    f"accumulation (len={len(endpoint_accumulated_answer)})"
                )

            log_entry.total_latency_ms = (time.time() - stream_start_time) * 1000
            # event 経由で既にセット済みなら ContextVar からの上書きは不要
            if log_entry.bigquery_latency_ms is None:
                _bq_ms = get_bq_latency_ms()
                log_entry.bigquery_latency_ms = _bq_ms if _bq_ms > 0 else None
            logger.info(f"📊 Endpoint log: bigquery_latency_ms={log_entry.bigquery_latency_ms}, "
                       f"total_latency_ms={log_entry.total_latency_ms:.0f}ms")
            llm_logger.log(log_entry)

        except PromptInjectionError as e:
            log_entry.success = False
            log_entry.error_type = "prompt_injection"
            log_entry.error_message = e.detected_pattern
            log_entry.total_latency_ms = (time.time() - stream_start_time) * 1000
            log_entry.bigquery_latency_ms = get_bq_latency_ms() or None
            llm_logger.log(log_entry)
            yield {
                "type": "error",
                "error_type": "blocked",
                "message": e.message,
                "detected_pattern": e.detected_pattern
            }
        except Exception as e:
            logger.error(f"❌ Stream Error: {str(e)}", exc_info=True)
            log_entry.success = False
            log_entry.error_type = "stream_error"
            log_entry.error_message = str(e)
            log_entry.total_latency_ms = (time.time() - stream_start_time) * 1000
            log_entry.bigquery_latency_ms = get_bq_latency_ms() or None
            llm_logger.log(log_entry)
            yield {
                "type": "error",
                "error_type": "internal_error",
                "message": str(e)
            }
    
    return StreamingResponse(
        stream_json_events(event_generator()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginxのバッファリングを無効化
        }
    )


# テスト用のエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Backend is working"}

@router.post("/test-post")
async def test_post_endpoint(request: dict):
    return {"received": request, "timestamp": time.time()}