"""
ChatOrchestrator: チャット機能の唯一の入口。
素の google-genai SDK + tool_use ループで、共通ツール (tools/) を順次呼び出す。

設計原則:
- LangGraph には依存しない（StrategyAgent との結合を切る）
- ストリーミング (SSE) はエンドポイント側で SSE 化するため、ここでは
  辞書イベントの AsyncGenerator を返す（既存 run_mlb_agent_stream と同じ契約）
- tool 関数の戻り値構造（{"isTable", "tableData", ...}）はそのまま LLM に渡し、
  最終的に UI 層に構造化データを返す責務は final_answer 構築側が持つ

依存:
- backend/app/services/tools/  共通ツール
- backend/app/services/security_guardrail  Prompt Injection 防御
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from google import genai
from google.genai import types

from backend.app.config.prompt_registry import get_prompt_version
from backend.app.config.settings import get_settings
from backend.app.core.exceptions import PromptInjectionError
from backend.app.services.llm_gateway_service import _calc_cost_usd
from backend.app.services.llm_logger_service import LLMLogEntry, get_llm_logger
from backend.app.services.online_judge_service import judge_and_log, should_sample
from backend.app.services.security_guardrail import get_security_guardrail
from backend.app.services.token_budget_service import get_token_budget_service
from backend.app.services.tools import (
    CHAT_TOOL_DECLARATIONS,
    CHAT_TOOL_DECLARATIONS_SEMANTIC,
    CHAT_TOOL_REGISTRY,
    GLOSSARY_SEARCH_DECL,
    _get_semantic_tool_registry,
    glossary_search_tool,
)
from backend.app.utils.structured_logger import get_logger

logger = get_logger("chat-orchestrator")

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_TOOL_ITERATIONS = 6


def _get_valid_metric_keys() -> List[str]:
    """METRIC_MAP の正規キー名一覧を取得する。
    LLM の system prompt に注入し、'rbi' のような短縮形ではなく
    'runs_batted_in' のような正規名のみ使うよう制約する。
    """
    try:
        from backend.app.config.query_maps import METRIC_MAP
        return sorted(METRIC_MAP.keys())
    except Exception:
        return []


def _get_semantic_metrics_and_dimensions() -> tuple:
    """Semantic Layer 登録済みメトリクス・次元の語彙を取得する。
    warmup 失敗時は空タプルを返し、prompt は fail-open でその旨を明示する。
    """
    try:
        from backend.app.services.semantic_layer_client import get_metric_metadata
        meta = get_metric_metadata()
        return (
            sorted(meta.get("metrics", [])),
            sorted(meta.get("dimensions", [])),
        )
    except Exception:
        return ([], [])


def _build_system_prompt_legacy() -> str:
    """legacy 経路 (USE_SEMANTIC_LAYER=false) 用の system prompt。
    get_batter_stats_tool / get_pitcher_stats_tool の構造化引数を LLM に指示。
    """
    current_year = datetime.now().year
    metric_keys = _get_valid_metric_keys()
    metric_vocab_line = (
        ", ".join(metric_keys) if metric_keys else "(METRIC_MAP 読み込み失敗)"
    )
    return f"""あなたはMLBデータ分析の専門アシスタントです。
ユーザーの質問を解析し、提供されたツールを呼び出して必要なデータを取得し、
プロのアナリスト視点で簡潔かつ的確な日本語回答を返してください。

【現在の日付に関する絶対ルール】
- **現在は {current_year} 年です。** {current_year - 1} 年以前のシーズンは **過去の実績** (確定値) です。
- 過去シーズンの成績を「予測」「推定」「見込み」などの表現で記述することは禁止です。事実として記述してください。
- データベースには 2015 年〜 {current_year} 年の全シーズンの実績データが格納されています。
- 「データがない」「予測です」と早合点せず、ツールが返した数値はそのまま事実として扱ってください。

【ツール呼び出しの絶対ルール】
- ユーザー質問の自然文解析 (NLU) は **あなた自身の責務** です。
- get_batter_stats_tool / get_pitcher_stats_tool を呼ぶ際は、必ず **構造化引数** を直接渡してください:
    * name: 選手名を英語フルネームに正規化 (例: 「大谷さん」→ "Shohei Ohtani", 「鈴木誠也」→ "Seiya Suzuki")
    * season: 年指定があれば整数で (例: {current_year - 1})。「キャリア」「通算」なら省略。「今年」「今シーズン」は {current_year}。
    * query_type: 状況なし年指定 → 'season_batting' / 状況あり → 'batting_splits' / 通算 → 'career_batting'
    * metrics: **必ず以下の正規キー名のみ** をリストで指定してください (短縮形・別名は禁止、validation エラーになります):
        {metric_vocab_line}
        または特殊キーワード 'main_stats' (主要スタッツ一括取得) のいずれか。
        例: 「打点」→ ['runs_batted_in'] (NOT 'rbi') / 「本塁打」→ ['homerun'] (NOT 'hr') / 「打率」→ ['batting_average'] (NOT 'avg')
    * split_type / inning / strikes / balls / game_score / pitcher_throws / pitch_type: 該当時のみ
    * output_format: デフォルト 'data' (生データ取得)。ユーザーが「表で」と言ったら 'table'。
- 旧式の `query` (自然文) 引数は **使わないでください**。ツール内で NLU が再実行されて遅くなります。

【データ分析の絶対ルール】
- 自分の知識だけで回答することは禁止です。必ずツールを呼び出して最新データを取得してください。
- 打者対投手の対戦質問では、必ず mlb_matchup_analytics_tool と mlb_matchup_history_tool の両方を使ってください。
- ツールが空結果やエラーを返した場合、引数を見直して 1〜2 回まで再試行してください。

【応答合成のルール】
- ツールから返ってきた 'data' (生データ) を読んで、**あなたが** 最終応答を組み立ててください。
- 数値は **そのまま事実として記述** (「〇〇は××本塁打を記録しました」)。推測表現禁止。
- Markdown 見出しと箇条書きを使い、主語から始まる完全な文章で回答を生成してください。
"""


def _build_system_prompt_semantic() -> str:
    """Semantic Layer 経路 (USE_SEMANTIC_LAYER=true) 用の system prompt。
    query_semantic_metrics_tool に構造化引数を渡すよう LLM に指示。
    """
    current_year = datetime.now().year
    metrics, dimensions = _get_semantic_metrics_and_dimensions()
    metrics_line = ", ".join(metrics) if metrics else "(Semantic Layer warmup 失敗、MetricFlow に直接問い合わせ)"
    dimensions_line = ", ".join(dimensions) if dimensions else "(取得不可)"
    return f"""あなたはMLBデータ分析の専門アシスタントです。
ユーザーの質問を解析し、`query_semantic_metrics_tool` を呼び出してデータを取得し、
プロのアナリスト視点で簡潔かつ的確な日本語回答を返してください。

【現在の日付に関する絶対ルール】
- **現在は {current_year} 年です。** {current_year - 1} 年以前のシーズンは **過去の実績** (確定値) です。
- 過去シーズンの成績を「予測」「推定」「見込み」などの表現で記述することは禁止です。事実として記述してください。
- 「今年」「今シーズン」「最新」は **season={current_year}**。「去年」は **season={current_year - 1}**。

【ツール呼び出しの絶対ルール】
- ユーザー質問の NLU は **あなた自身の責務** です。`query_semantic_metrics_tool` に構造化引数を直接渡してください。
- **`metrics` 引数には以下の正規メトリクス名のみ使用可** (短縮形・別名は禁止):
    {metrics_line}

【利用可能な次元】
{dimensions_line}

【その他】
- 打者は entity_type='player'、投手は entity_type='pitcher'。
- 打者対投手の対戦質問では mlb_matchup_analytics_tool と mlb_matchup_history_tool を使用 (Semantic Layer 未対応のため)。

【応答合成のルール】
- ツール戻り値を読んで **あなたが** 最終応答を組み立ててください。
- 数値はそのまま事実として記述 (「〇〇は××本塁打を記録しました」)。推測表現禁止。
- Markdown 見出しと箇条書きを使い、主語から始まる完全な文章で回答してください。
"""


def _build_system_prompt(use_semantic: bool = False) -> str:
    """システムプロンプト構築。フラグで legacy / semantic 経路を切替。"""
    return _build_system_prompt_semantic() if use_semantic else _build_system_prompt_legacy()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize_tool_result(obj: Any) -> Any:
    """Gemini API は NaN/Infinity を拒否するため None に置換する。
    旧 executor_node から踏襲。"""
    if isinstance(obj, list):
        return [_sanitize_tool_result(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_tool_result(v) for k, v in obj.items()}
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        if obj in (float("inf"), float("-inf")):
            return None
    return obj


def _extract_structured_payload(tool_results: List[Any]) -> Dict[str, Any]:
    """ツール戻り値から UI 用構造化フィールドを抽出する。
    旧 synthesizer_node の構造化抽出ロジックを移植。
    """
    payload: Dict[str, Any] = {
        "isTable": False,
        "isChart": False,
        "isMatchupCard": False,
        "tableData": None,
        "columns": None,
        "isTransposed": False,
        "chartType": "",
        "chartData": None,
        "chartConfig": None,
        "matchupData": {},
    }
    # Table / Chart は最後の構造化結果を優先
    for res in reversed(tool_results):
        if not isinstance(res, dict):
            continue
        if res.get("isTable") is True:
            payload.update({
                "isTable": True,
                "tableData": res.get("tableData"),
                "columns": res.get("columns"),
                "isTransposed": res.get("isTransposed", False),
            })
            break
        if res.get("isChart") is True:
            payload.update({
                "isChart": True,
                "chartType": res.get("chartType", ""),
                "chartData": res.get("chartData"),
                "chartConfig": res.get("chartConfig"),
            })
            break

    # MatchupCard は list 形式の戻り値から構築
    matchup_history: List[Dict[str, Any]] = []
    matchup_stats: List[Dict[str, Any]] = []
    for res in tool_results:
        if isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, dict):
                if "pitch_name" in first and ("batting_average" in first or "avg" in first):
                    for item in res:
                        if "avg" in item and "batting_average" not in item:
                            item["batting_average"] = item["avg"]
                    matchup_stats = res
                    payload["isMatchupCard"] = True
                elif "game_date" in first:
                    matchup_history = res
                    payload["isMatchupCard"] = True
    if payload["isMatchupCard"]:
        seed = matchup_stats or matchup_history or [{}]
        payload["matchupData"] = {
            "stats": matchup_stats,
            "history": matchup_history[:50],
            "summary": {
                "batter": seed[0].get("batter_name", "Batter"),
                "pitcher": seed[0].get("pitcher_name", "Pitcher"),
            },
        }
    return payload


def _format_rows_as_markdown(tool_results: List[Any]) -> str:
    """tool 戻り値を LLM 不使用で Markdown 文字列に整形する。
    synthesize_response=False (デフォルト) で UI 表示テキストとして使う。

    対応する tool 戻り値形式:
      1. {"data": [rows], "parameters": {...}}  — legacy batter/pitcher services
      2. {"answer": "...", "isTable": bool, "tableData": [...], "columns": [...]}  — Semantic Layer
      3. {"answer": "..."} — Semantic Layer sentence モード
    """
    parts: List[str] = []
    for res in tool_results:
        if not isinstance(res, dict):
            continue

        # 形式 1: legacy batter/pitcher の生データ
        rows = res.get("data")
        if rows and isinstance(rows, list):
            params = res.get("parameters") or {}
            player = params.get("name") or (rows[0].get("name") if rows else None)
            season = params.get("season")
            header_bits = [b for b in [player, f"{season}年" if season else None] if b]
            if header_bits:
                parts.append(f"### {' / '.join(header_bits)}")
            for row in rows:
                for col, val in row.items():
                    if val is None:
                        continue
                    parts.append(f"- {col}: {val}")
            continue

        # 形式 2: Semantic Layer の table 構造化応答
        if res.get("isTable") and res.get("tableData"):
            table_data = res["tableData"]
            cols = res.get("columns") or []
            col_keys = [c.get("key") if isinstance(c, dict) else c for c in cols]
            if not col_keys and table_data:
                col_keys = list(table_data[0].keys())
            for row in table_data:
                for k in col_keys:
                    v = row.get(k)
                    if v is None:
                        continue
                    parts.append(f"- {k}: {v}")
            continue

        # 形式 3: answer フィールドのみ (Semantic Layer sentence モード等)
        answer = res.get("answer")
        if answer and isinstance(answer, str):
            parts.append(answer)

    return "\n".join(parts) or "データが取得できませんでした。"


# 戻り値が「生データ」ではなく「文章」であるツール。
# これらが呼ばれた場合は機械整形ではなく LLM に応答を合成させる。
SYNTHESIS_REQUIRED_TOOLS = frozenset({"glossary_search_tool"})


def _needs_synthesis(tool_names_seen: set) -> bool:
    """LLM #2 による応答合成が必要かを、呼ばれたツール名から判定する。

    戻り値のキー（"sources" 等）で推測すると、将来別のツールが同じキーを
    返した際に黙って挙動が変わるため、ツール名を明示的に見る。
    """
    return bool(tool_names_seen & SYNTHESIS_REQUIRED_TOOLS)


def _append_sources(answer: str, tool_results: List[Any]) -> str:
    """tool 戻り値の sources を回答末尾に機械的に付加する。

    LLM に「出典を書け」と指示する方式は取らない。要約の過程で落とされ、
    出典の有無が LLM の裁量に左右されるため（実際に落ちた事例あり）。
    既に同じ出典行が含まれている場合は二重付加しない。
    """
    sources = sorted({
        s
        for r in tool_results
        if isinstance(r, dict)
        for s in (r.get("sources") or [])
    })
    if not sources or not answer:
        return answer

    line = "出典: " + ", ".join(sources)
    if line in answer:
        return answer
    return f"{answer}\n\n{line}"


class ChatOrchestrator:
    """素の Gemini SDK + tool_use ループで動くチャットエンジン。

    tool 実行後の挙動を 2 モードで切替:
      - synthesize_response=False (デフォルト): tool が返した生データをそのまま返す。LLM #2 を呼ばない。
      - synthesize_response=True: tool データを LLM に渡して自然言語応答を合成する。
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        synthesize_response: bool = False,
        use_semantic_layer: Optional[bool] = None,
        use_glossary_rag: Optional[bool] = None,
    ):
        self.model = model
        self.synthesize_response = synthesize_response
        # use_semantic_layer 未指定なら settings から取得 (env: USE_SEMANTIC_LAYER)
        if use_semantic_layer is None:
            use_semantic_layer = bool(get_settings().use_semantic_layer)
        self.use_semantic_layer = use_semantic_layer

        key = api_key or os.getenv("GEMINI_API_KEY_V2")
        if not key:
            raise RuntimeError("GEMINI_API_KEY_V2 is not configured for ChatOrchestrator")
        self._client = genai.Client(api_key=key)

        # use_glossary_rag 未指定なら settings から取得 (env: USE_GLOSSARY_RAG)
        if use_glossary_rag is None:
            use_glossary_rag = bool(get_settings().use_glossary_rag)
        self.use_glossary_rag = use_glossary_rag

        # フラグでツール宣言と registry を切り替え
        # list()/dict() でコピーするのは、モジュールレベルの定数に直接 append すると
        # インスタンスを作るたびに宣言が増え続けるため。
        if self.use_semantic_layer:
            declarations = list(CHAT_TOOL_DECLARATIONS_SEMANTIC)
            registry = dict(_get_semantic_tool_registry())
            logger.info("ChatOrchestrator initialized with Semantic Layer tools")
        else:
            declarations = list(CHAT_TOOL_DECLARATIONS)
            registry = dict(CHAT_TOOL_REGISTRY)
            logger.info("ChatOrchestrator initialized with legacy METRIC_MAP tools")

        # Glossary RAG は独立フラグ。Semantic Layer の ON/OFF とは直交する
        if self.use_glossary_rag:
            declarations.append(GLOSSARY_SEARCH_DECL)
            registry["glossary_search_tool"] = glossary_search_tool
            logger.info("glossary RAG enabled")

        self._tools_config = types.Tool(function_declarations=declarations)
        self._tool_registry = registry

        system_prompt = _build_system_prompt(use_semantic=self.use_semantic_layer)

        # Context Caching for system prompt. 本番では Semantic Layer vocab 注入後
        # ~1,900 tokens (>1,024 閾値) となり caching の対象。1 リクエストで tool_use loop
        # を複数回まわすため、削減効果は iteration 数だけ倍加する。
        # 失敗時 (閾値未満・SDK エラー等) は無音で従来 (system_instruction) 経路にフォールバック。
        #
        # Gemini API の制約: cached_content を使う generate_content には
        # system_instruction / tools / tool_config を渡せない。tool_use ループも
        # Cache する場合は tools を Cache 側に含め、generate_content 側からは外す。
        cache_name: Optional[str] = None
        try:
            from backend.app.services.prompt_cache_service import get_or_create_cache
            cache_name = get_or_create_cache(
                prompt_name="chat_orchestrator_system",
                prompt_version=get_prompt_version("chat_orchestrator_system"),
                prefix_text=system_prompt,
                as_system_instruction=True,
                tools=[self._tools_config],
            )
        except Exception as e:
            logger.warning(f"chat_orchestrator_system cache lookup failed: {e}")

        if cache_name:
            self._gen_config = types.GenerateContentConfig(
                cached_content=cache_name,
                temperature=0,
            )
        else:
            self._gen_config = types.GenerateContentConfig(
                tools=[self._tools_config],
                system_instruction=system_prompt,
                temperature=0,
            )

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """tool_use の dispatch。@tool 関数は .invoke(args) で呼べる。"""
        tool_fn = self._tool_registry.get(name)
        if tool_fn is None:
            logger.warning(f"Unknown tool requested by LLM: {name}")
            return {"error": f"Tool {name} not found"}
        try:
            return tool_fn.invoke(args)
        except Exception as e:
            logger.error(f"Tool execution failed: {name}", error=str(e), exc_info=True)
            return {"error": f"Tool {name} failed: {e}"}
    

    async def run(self, user_query: str) -> Dict[str, Any]:
        """非ストリーム実行。テスト・バッチ用途。"""
        guardrail = get_security_guardrail()
        is_safe, reason = guardrail.validate_and_log(user_query)
        if not is_safe:
            raise PromptInjectionError(
                message="申し訳ございませんが、このリクエストにはお応えできません。MLB統計に関する質問をお願いいたします。",
                detected_pattern=reason,
            )

        contents: List[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=user_query)])
        ]
        tool_results_seen: List[Any] = []
        # 呼ばれたツール名。応答生成モードの判定に使う（戻り値のキーで推測しない）
        tool_names_seen: set[str] = set()

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._gen_config,
            )
            cand = (response.candidates or [None])[0]
            if cand is None:
                break

            function_calls = []
            text_parts = []
            for part in (cand.content.parts or []):
                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_parts.append(part.text)

            if not function_calls:
                final_text = _append_sources(
                    "".join(text_parts).strip(), tool_results_seen
                )
                payload = _extract_structured_payload(tool_results_seen)
                return {"final_answer": final_text, **payload}

            # tool_use を contents に積む
            contents.append(types.Content(
                role="model",
                parts=[types.Part(function_call=fc) for fc in function_calls],
            ))
            for fc in function_calls:
                args = dict(fc.args or {})
                result = self._execute_tool(fc.name, args)
                tool_results_seen.append(result)
                tool_names_seen.add(fc.name)
                sanitized = _sanitize_tool_result(result)
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": sanitized},
                    ))],
                ))

            # synthesize_response=False (デフォルト): LLM #2 を呼ばず即 return
            # 用語集 RAG は結果が文章のため例外的に合成させる（run_stream と挙動を揃える）
            if not self.synthesize_response and not _needs_synthesis(tool_names_seen):
                payload = _extract_structured_payload(tool_results_seen)
                return {"final_answer": "", **payload}

        logger.warning("ChatOrchestrator hit MAX_TOOL_ITERATIONS")
        return {
            "final_answer": "ツール呼び出しが上限に達しました。質問を簡潔にして再度お試しください。",
            **_extract_structured_payload(tool_results_seen),
        }


    async def run_stream(
        self,
        user_query: str,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """ストリーミング実行。SSE イベント辞書を yield する。
        旧 run_mlb_agent_stream と同じイベント契約を維持。
        """
        guardrail = get_security_guardrail()
        is_safe, reason = guardrail.validate_and_log(user_query)
        if not is_safe:
            yield {
                "type": "error",
                "error_type": "blocked",
                "message": "申し訳ございませんが、このリクエストにはお応えできません。MLB統計に関する質問をお願いいたします。",
                "detected_pattern": reason,
            }
            return

        # フロント互換のため routing イベントを 1 回だけ送る
        yield {
            "type": "routing",
            "agent_type": "chat",
            "message": "ChatOrchestrator で処理します",
        }

        contents: List[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=user_query)])
        ]
        tool_results_seen: List[Any] = []
        # 呼ばれたツール名。応答生成モードの判定に使う（戻り値のキーで推測しない）
        tool_names_seen: set[str] = set()
        accumulated_answer = ""
        accumulated_llm_ms = 0.0

        for iteration in range(MAX_TOOL_ITERATIONS):
            yield {
                "type": "state_update",
                "node": "oracle",
                "status": "started",
                "message": "質問を分析しています",
                "node_details": "ユーザーの質問を理解し、必要なツールを選択",
                "timestamp": _now_iso(),
                "step_type": "node_start",
            }

            # LLM 呼び出しを LLMLogEntry でラップして BQ に記録する。
            # 1 iteration = 1 LLM 呼び出し = 1 ログ行 (model/tokens/cost/parsed_*)
            entry = LLMLogEntry()
            entry.model = self.model
            entry.feature = f"chat_orchestrator_iter_{iteration}"
            entry.prompt_name = "chat_orchestrator_system"
            entry.prompt_version = get_prompt_version("chat_orchestrator_system")
            entry.user_query = (user_query or "")[:500]

            llm_t0 = time.time()
            function_calls: List[Any] = []
            iter_text_parts: List[str] = []
            last_usage = None
            try:
                stream = self._client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=self._gen_config,
                )

                for chunk in stream:
                    # 各 chunk に usage_metadata が累積で乗ってくる。最後のものを採用。
                    if getattr(chunk, "usage_metadata", None):
                        last_usage = chunk.usage_metadata
                    for cand in (chunk.candidates or []):
                        for part in (cand.content.parts or []):
                            if part.function_call:
                                function_calls.append(part.function_call)
                            elif part.text:
                                accumulated_answer += part.text
                                iter_text_parts.append(part.text)
                                yield {
                                    "type": "token",
                                    "content": part.text,
                                    "node": "synthesizer",
                                }
                entry.success = True
                entry.response_answer = "".join(iter_text_parts) or None

                # function_call の引数を parsed_* カラムに記録 (Orchestrator が解析した結果)
                for fc in function_calls:
                    fc_args = dict(fc.args or {})
                    if fc_args.get("name"):
                        entry.parsed_player_name = fc_args.get("name")
                    if fc_args.get("query_type"):
                        entry.parsed_query_type = fc_args.get("query_type")
                    metrics = fc_args.get("metrics")
                    if metrics:
                        entry.parsed_metrics = json.dumps(metrics, ensure_ascii=False)
                    if fc_args.get("season") is not None:
                        try:
                            entry.parsed_season = int(fc_args["season"])
                        except (TypeError, ValueError):
                            pass

                # usage_metadata からトークン数・コスト算出
                if last_usage:
                    entry.input_tokens = getattr(last_usage, "prompt_token_count", None) or 0
                    entry.output_tokens = getattr(last_usage, "candidates_token_count", None) or 0
                    entry.cached_tokens = getattr(last_usage, "cached_content_token_count", None)
                    entry.estimated_cost_usd = _calc_cost_usd(
                        model=self.model,
                        input_tokens=entry.input_tokens or 0,
                        output_tokens=entry.output_tokens or 0,
                        cached_tokens=entry.cached_tokens or 0,
                    )
                    # Phase 3-A: chat プールに使用量を計上
                    try:
                        total_tokens = (entry.input_tokens or 0) + (entry.output_tokens or 0)
                        if total_tokens > 0:
                            get_token_budget_service().record_usage(total_tokens, pool="chat")
                    except Exception as e:
                        logger.warning(f"token budget record failed (suppressed): {e}")
            except Exception as e:
                entry.success = False
                entry.error_type = type(e).__name__
                entry.error_message = str(e)[:500]
                logger.error(f"ChatOrchestrator LLM call failed: {e}", exc_info=True)
                raise
            finally:
                entry.llm_latency_ms = (time.time() - llm_t0) * 1000.0
                try:
                    get_llm_logger().log(entry)
                except Exception as e:
                    # ロギング失敗は本処理に影響させない
                    logger.warning(f"LLM log write failed (suppressed): {e}")
                accumulated_llm_ms += entry.llm_latency_ms

            yield {
                "type": "state_update",
                "node": "oracle",
                "status": "completed",
                "message": "oracle 完了",
                "timestamp": _now_iso(),
                "step_type": "node_end",
            }

            if not function_calls:
                payload = _extract_structured_payload(tool_results_seen)
                # 出典は LLM の裁量に委ねず機械的に付加する
                final_answer = _append_sources(
                    accumulated_answer.strip(), tool_results_seen
                )
                yield {
                    "type": "final_answer",
                    "answer": final_answer,
                    **payload,
                    "isStrategyReport": False,
                    "strategyData": None,
                    "llm_latency_ms": accumulated_llm_ms,
                }
                # 応答は yield 済み。await せず投げっぱなしにする (レイテンシに影響させない)。
                if should_sample():
                    asyncio.create_task(judge_and_log(
                        request_id or "",
                        user_query,
                        tool_results_seen,
                        final_answer,
                    ))
                return

            # tool_use を contents に積む + 各 tool を実行
            contents.append(types.Content(
                role="model",
                parts=[types.Part(function_call=fc) for fc in function_calls],
            ))
            for fc in function_calls:
                yield {
                    "type": "tool_start",
                    "tool_name": fc.name,
                    "message": f"🔧 {fc.name} を実行中...",
                    "timestamp": _now_iso(),
                    "step_type": "tool_call",
                }
                args = dict(fc.args or {})
                result = self._execute_tool(fc.name, args)
                tool_results_seen.append(result)
                tool_names_seen.add(fc.name)
                output_summary = ""
                if isinstance(result, list):
                    output_summary = f"{len(result)}件のデータを取得"
                yield {
                    "type": "tool_end",
                    "tool_name": fc.name,
                    "message": f"✅ {fc.name} 完了",
                    "output_summary": output_summary,
                    "timestamp": _now_iso(),
                    "step_type": "tool_result",
                }
                sanitized = _sanitize_tool_result(result)
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": sanitized},
                    ))],
                ))

            # ===== 分岐: tool 実行後の応答生成モード =====
            # synthesize_response=False (デフォルト): LLM #2 を呼ばず、tool 生データを Markdown に整形して返す。
            # synthesize_response=True: ループを続け、次の iteration で LLM が応答合成する。
            # 用語集 RAG の結果は生データではなく文章のため、LLM に要約させる。
            # 成績照会（数値の羅列）は機械整形の方が正確かつ安価なので従来通り。
            if not self.synthesize_response and not _needs_synthesis(tool_names_seen):
                payload = _extract_structured_payload(tool_results_seen)
                # 生データを LLM 不使用で Markdown 整形
                formatted_answer = _format_rows_as_markdown(tool_results_seen)
                # tool 戻り値から BQ 累計時間を集計 (ContextVar 非経由)
                bq_latency_ms = sum(
                    res.get("bigquery_latency_ms", 0) or 0
                    for res in tool_results_seen
                    if isinstance(res, dict)
                )
                yield {
                    "type": "final_answer",
                    "answer": formatted_answer,
                    **payload,
                    "isStrategyReport": False,
                    "strategyData": None,
                    "llm_latency_ms": accumulated_llm_ms,
                    "bigquery_latency_ms": bq_latency_ms or None,
                }
                # synthesize_response=False 経路。answer は機械整形のため、
                # judge の 5 項目のうち factual_accuracy / completeness のみが有効。
                if should_sample():
                    asyncio.create_task(judge_and_log(
                        request_id or "",
                        user_query,
                        tool_results_seen,
                        formatted_answer,
                    ))
                return

        logger.warning("ChatOrchestrator stream hit MAX_TOOL_ITERATIONS")
        yield {
            "type": "final_answer",
            "answer": accumulated_answer.strip() or "ツール呼び出しが上限に達しました。質問を簡潔にして再度お試しください。",
            **_extract_structured_payload(tool_results_seen),
            "isStrategyReport": False,
            "strategyData": None,
            "llm_latency_ms": accumulated_llm_ms,
        }


