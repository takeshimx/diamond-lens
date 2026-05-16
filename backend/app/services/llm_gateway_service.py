"""
LLM Gateway Service
全 LLM 呼び出しの単一窓口。google-genai SDK 経由で Gemini を呼び出し、
トークン抽出・コスト計算・BQロギングを集約する。

設計原則:
- 「LLMを呼ぶ＝gatewayを通す＝コストログが必ず書かれる」を構造的に担保
- try-finally で成功/失敗・例外時も必ず log を書く
- 戻り値は既存 _make_request と互換 (テキストまたは None)、Phase3 の機械的移行を担保
- 例外は内部で握り、None を返す (既存 Caller の None 判定パターンを維持)
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.app.services.llm_logger_service import LLMLogEntry, get_llm_logger

logger = logging.getLogger(__name__)

# .env を明示的にロード（ai_service.py 等と同じパターン）
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_V2", "")
DEFAULT_MODEL = "gemini-2.5-flash"

# ==================================
# PRICING Map
# ==================================
# Source: https://ai.google.dev/gemini-api/docs/pricing (Paid tier, verified 2026-05-16)
PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {
        "input_per_1m_usd": 0.30,
        "output_per_1m_usd": 2.50,
        "cached_per_1m_usd": 0.03,
    },
    "gemini-2.0-flash": {
        "input_per_1m_usd": 0.10,
        "output_per_1m_usd": 0.40,
        "cached_per_1m_usd": 0.025,
    },
}


def _calc_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    """モデル別価格表からUSDコストを算出。未登録モデルは0を返す。"""
    p = PRICING.get(model)
    if not p:
        logger.warning(f"PRICING not defined for model: {model}")
        return 0.0
    non_cached_input = max(0, input_tokens - cached_tokens)
    return (
        non_cached_input * p["input_per_1m_usd"] / 1_000_000
        + cached_tokens * p["cached_per_1m_usd"] / 1_000_000
        + output_tokens * p["output_per_1m_usd"] / 1_000_000
    )


# ==================================
# Lazy genai client
# ==================================
_genai_client: Optional[genai.Client] = None


def _get_genai_client() -> genai.Client:
    """genai SDK クライアントを lazy 初期化 (起動時に API key 未設定でも import を許容)"""
    global _genai_client
    if _genai_client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


# ==================================
# Gateway 本体
# ==================================
def call_gemini(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    response_mime_type: str = "text/plain",
    feature: Optional[str] = None,
    user_id: str = "",
    endpoint: Optional[str] = None,
    request_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
) -> Optional[str]:
    """
    Gemini テキスト生成の単一窓口。

    Args:
        prompt: LLM へのプロンプト
        model: gemini-2.5-flash / gemini-2.0-flash 等
        response_mime_type: "text/plain" or "application/json"
        feature: ダッシュボード集計用タグ (例 "ai_summary", "routing_judge")
        user_id: Firebase UID 等 (集計用に caller から伝搬)
        endpoint: 呼び出し元 API パス (任意)
        request_id: HTTP リクエスト ID (任意)
        prompt_version: prompt registry から取得した version (任意)

    Returns:
        生成テキスト、または失敗時 None (既存 _make_request と互換)
    """
    entry = LLMLogEntry()
    entry.user_id = user_id
    entry.model = model
    entry.endpoint = endpoint
    entry.request_id = request_id
    entry.feature = feature
    entry.prompt_version = prompt_version
    entry.user_query = prompt[:500]  # プロンプト先頭500文字（全文は冗長）

    text: Optional[str] = None
    t0 = time.time()
    try:
        client = _get_genai_client()
        config = types.GenerateContentConfig(response_mime_type=response_mime_type)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        # usage_metadata 抽出
        um = response.usage_metadata
        entry.input_tokens = (um.prompt_token_count if um else None) or 0
        entry.output_tokens = (um.candidates_token_count if um else None) or 0
        entry.cached_tokens = (
            getattr(um, "cached_content_token_count", None) if um else None
        )

        # コスト計算
        entry.estimated_cost_usd = _calc_cost_usd(
            model=model,
            input_tokens=entry.input_tokens or 0,
            output_tokens=entry.output_tokens or 0,
            cached_tokens=entry.cached_tokens or 0,
        )

        text = response.text
        if text is None:
            entry.success = False
            entry.error_type = "no_text"
            entry.error_message = "SDK returned response with text=None"
            logger.warning("Gemini SDK returned no text")
        else:
            entry.success = True

    except Exception as e:
        entry.success = False
        entry.error_type = type(e).__name__
        entry.error_message = str(e)[:500]
        logger.error(f"Gemini gateway call failed: {e}", exc_info=True)
        text = None

    finally:
        entry.llm_latency_ms = (time.time() - t0) * 1000.0
        try:
            get_llm_logger().log(entry)
        except Exception as e:
            # ロギング失敗はアプリ機能に影響させない
            logger.error(f"Failed to log gateway entry: {e}")

    return text


# ==================================
# LangChain Usage Callback
# ==================================
# ChatGoogleGenerativeAI など LangChain LLM ラッパーは call_gemini() を経由しない。
# 同等の BQ ログを実現するため、LangChain callback 機構で on_llm_end を捕まえる。

try:
    from langchain_core.callbacks import BaseCallbackHandler
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    BaseCallbackHandler = object  # type: ignore
    _LANGCHAIN_AVAILABLE = False


class LangchainUsageCallback(BaseCallbackHandler):
    """LangChain ChatGoogleGenerativeAI 用のコスト・トークン計測 callback。
    各 LLM 呼び出しの終了時 (on_llm_end) に LLMLogEntry を組み立てて BQ に書く。

    Usage:
        cb = LangchainUsageCallback(feature="strategy_report", model="gemini-2.5-flash")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", callbacks=[cb], ...)
    """

    def __init__(
        self,
        feature: str,
        model: str,
        user_id: str = "",
        endpoint: Optional[str] = None,
    ):
        super().__init__() if _LANGCHAIN_AVAILABLE else None
        self.feature = feature
        self.model = model
        self.user_id = user_id
        self.endpoint = endpoint
        self._start_time: Optional[float] = None

    # LangChain は chat-style では on_chat_model_start を呼ぶ
    def on_chat_model_start(self, serialized, messages, **kwargs):
        self._start_time = time.time()

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._start_time = time.time()

    def _extract_usage(self, response) -> Dict[str, int]:
        """LangChain LLMResult から (input, output) トークン数を抽出。複数 path に対応。"""
        in_t, out_t = 0, 0
        try:
            # Path 1: response.llm_output["token_usage"] (OpenAI 互換 path)
            if getattr(response, "llm_output", None):
                tu = (response.llm_output or {}).get("token_usage") or {}
                in_t = tu.get("prompt_token_count") or tu.get("input_tokens") or in_t
                out_t = tu.get("candidates_token_count") or tu.get("output_tokens") or out_t

            # Path 2: response.generations[0][0].message.usage_metadata (Gemini 経路の主流)
            gens = getattr(response, "generations", None) or []
            if gens and gens[0]:
                first = gens[0][0]
                msg = getattr(first, "message", None)
                um = getattr(msg, "usage_metadata", None) if msg else None
                if um:
                    in_t = in_t or um.get("input_tokens") or 0
                    out_t = out_t or um.get("output_tokens") or 0
                # Path 3: generation_info
                gi = getattr(first, "generation_info", None) or {}
                um2 = gi.get("usage_metadata") or {}
                in_t = in_t or um2.get("prompt_token_count") or 0
                out_t = out_t or um2.get("candidates_token_count") or 0
        except Exception as e:
            logger.warning(f"LangchainUsageCallback: failed to extract usage: {e}")
        return {"input_tokens": int(in_t or 0), "output_tokens": int(out_t or 0)}

    def on_llm_end(self, response, **kwargs):
        entry = LLMLogEntry()
        entry.user_id = self.user_id
        entry.feature = self.feature
        entry.endpoint = self.endpoint
        entry.model = self.model

        usage = self._extract_usage(response)
        entry.input_tokens = usage["input_tokens"]
        entry.output_tokens = usage["output_tokens"]
        entry.estimated_cost_usd = _calc_cost_usd(
            model=self.model,
            input_tokens=entry.input_tokens or 0,
            output_tokens=entry.output_tokens or 0,
        )
        if self._start_time:
            entry.llm_latency_ms = (time.time() - self._start_time) * 1000.0
        entry.success = True

        try:
            get_llm_logger().log(entry)
        except Exception as e:
            logger.error(f"LangchainUsageCallback: log failed: {e}")

    def on_llm_error(self, error, **kwargs):
        entry = LLMLogEntry()
        entry.user_id = self.user_id
        entry.feature = self.feature
        entry.endpoint = self.endpoint
        entry.model = self.model
        entry.success = False
        entry.error_type = type(error).__name__
        entry.error_message = str(error)[:500]
        if self._start_time:
            entry.llm_latency_ms = (time.time() - self._start_time) * 1000.0
        try:
            get_llm_logger().log(entry)
        except Exception as e:
            logger.error(f"LangchainUsageCallback: error-log failed: {e}")
