"""本番応答に対する非同期 Judge 評価

原則:
- ユーザー応答を返した後に実行する。レイテンシに影響させない。
- サンプリングして一部のみ評価する。全件は課金が読めない。
- 例外は必ずここで握り潰す。Judge の失敗が本流を壊してはならない。
"""
import asyncio
import json
import logging
import random
from typing import Any, Dict, List, Optional

from backend.app.config.settings import get_settings
from backend.app.services.synthesizer_judge_service import AnswerMode, SynthesizerJudgeService
from backend.app.utils.bq_dml import insert_rows_dml


logger = logging.getLogger(__name__)

# 文書検索 (RAG) を行うツール。採点モード "rag" の判定に使う。
# 戻り値の形ではなくツール名で見るのは chat_orchestrator.SYNTHESIS_REQUIRED_TOOLS と同じ思想。
RETRIEVAL_TOOLS = frozenset({"glossary_search_tool"})

_judge: Optional[SynthesizerJudgeService] = None


def _get_judge() -> SynthesizerJudgeService:
    global _judge
    if _judge is None:
        _judge = SynthesizerJudgeService()
    return _judge


def should_sample() -> bool:
    s = get_settings()
    if not s.online_judge_enabled:
        return False
    return random.random() < s.online_judge_sample_rate


def _truncate(text: str, limit: int = 4000) -> str:
    """Judge への入力を切り詰める。長大なデータで課金が膨らむのを防ぐ。"""
    return text if len(text) <= limit else text[:limit] + " ...(truncated)"


def resolve_answer_mode(tool_names: Optional[set], synthesized: bool) -> Optional[AnswerMode]:
    """回答の経路から Judge の採点モードを決める。None は採点対象外。

    - 機械整形した回答 → "raw"
    - RAG ツールの結果から LLM が文章を組み立てた回答 → "rag"
    - ツールを呼ばずに LLM が直接答えた回答 → None（元データが無く、採点基準が成り立たない）
    """
    if not synthesized:
        return "raw"
    if (tool_names or set()) & RETRIEVAL_TOOLS:
        return "rag"
    return None


async def judge_and_log(
    request_id: str,
    user_query: str,
    tool_results: List[Any],
    final_answer: str,
    answer_mode: AnswerMode,
) -> None:
    """応答確定後に呼ぶ。同期的に待たないこと。

    answer_mode は resolve_answer_mode() で決めた値を渡す。
    """
    try:
        if not final_answer:
            return

        source_data = _truncate(json.dumps(tool_results, ensure_ascii=False, default=str))

        # Judge 本体は同期 I/O のため、イベントループを塞がないよう別スレッドへ逃がす
        verdict = await asyncio.to_thread(
            _get_judge().evaluate_output,
            case_id=request_id,
            user_query=user_query,
            source_data=source_data,
            synthesizer_output=_truncate(final_answer),
            answer_mode=answer_mode,
        )
        _write_to_bq(request_id, verdict)
    except Exception as e:
        # 本流に伝播させない。ログだけ残す。
        logger.warning(f"online judge failed (request_id={request_id}): {e}")


def _write_to_bq(request_id: str, verdict: Any) -> None:
    """判定結果を BQ に蓄積する。テーブルは別途作成が必要。"""
    from backend.app.services.bigquery_service import client, PROJECT_ID

    row = verdict.to_dict()
    row["request_id"] = request_id
    # issues は List[str]。BQ 側は STRING カラムのため JSON 文字列に落とす。
    row["issues"] = json.dumps(row.get("issues") or [], ensure_ascii=False)
    table_id = f"{PROJECT_ID}.{get_settings().bigquery_dataset_id}.online_judge_verdicts"
    insert_rows_dml(client, table_id, [row])