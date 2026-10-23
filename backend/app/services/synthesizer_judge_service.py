"""
LLM as a Judge #2 - チャット回答の品質評価サービス

本番チャットの回答を、回答の経路（answer_mode）ごとに異なる基準で評価します。

  - "raw": ツールの生データを機械整形した回答。factual_accuracy / completeness の 2 項目のみ
  - "rag": 検索で引いた文書から LLM が文章を組み立てた回答。5 項目 + context_relevance

採点基準はプロンプトファイル（app/prompts/synthesizer_judge_{raw,rag}_v1.txt）に置き、
prompt_registry 経由で読み込みます。総合点と合否は LLM に出させず、コードで計算します。
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone

from backend.app.config.prompt_registry import get_prompt
from backend.app.services.llm_gateway_service import call_gemini

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_V2")

AnswerMode = Literal["raw", "rag"]


@dataclass
class SynthesizerVerdict:
    """チャット回答の品質評価結果

    フィールド名は BQ online_judge_verdicts の列名と一致させている。
    採点対象外の項目は 0 を記録する（最低点 1 とは区別する）。
    """

    # テストケース情報
    case_id: str
    user_query: str

    # 項目別スコア (1-5、対象外は 0)
    factual_accuracy: int = 0      # 事実の正確さ: 元データとの一致
    analytical_depth: int = 0      # 深さの適合: 質問が求める深さに合っているか (rag のみ)
    language_quality: int = 0      # 文章の質 (rag のみ)
    structure: int = 0             # 構造の適合: 長さに見合った整理か (rag のみ)
    completeness: int = 0          # 網羅性: 質問への過不足
    overall_score: float = 0.0     # 対象項目の平均（コードで計算）

    # 文書の関連性。rag のみ採点し、overall_score には含めない
    context_relevance: int = 0
    retrieval_used: bool = False

    # 判定結果
    passed: bool = False
    reasoning: str = ""
    issues: List[str] = field(default_factory=list)

    # メタデータ。BQ 列名の都合で synthesizer_path に answer_mode ("raw" / "rag") を入れる
    synthesizer_path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-3.6-flash"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


PASS_THRESHOLD = 3.5
# 事実の誤りは他の項目で取り返せないようにする。平均点に関係なくこれ未満は不合格
FACTUAL_ACCURACY_FLOOR = 3

# 経路ごとの総合点の対象項目。context_relevance は材料選びの評価なので含めない
SCORED_DIMENSIONS: Dict[str, List[str]] = {
    "raw": ["factual_accuracy", "completeness"],
    "rag": ["factual_accuracy", "completeness", "analytical_depth", "language_quality", "structure"],
}


class SynthesizerJudgeService:
    """チャット回答の品質を LLM Judge で評価するサービス"""

    def __init__(self, model_name: str = "gemini-3.6-flash"):
        self.model_name = model_name
        self.api_key = GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY_V2 is not set. Synthesizer Judge will not work.")

    def evaluate_output(
        self,
        case_id: str,
        user_query: str,
        source_data: str,
        synthesizer_output: str,
        answer_mode: AnswerMode = "raw",
    ) -> SynthesizerVerdict:
        """
        チャット回答を評価する。

        Args:
            case_id: リクエストID / テストケースID
            user_query: ユーザーの元の質問
            source_data: ツールが返した元データ（JSON文字列）
            synthesizer_output: ユーザーに返した回答テキスト
            answer_mode: "raw"（生データ経路）または "rag"（RAG 文章合成経路）
        """
        if answer_mode not in SCORED_DIMENSIONS:
            raise ValueError(f"unknown answer_mode: {answer_mode}")

        retrieval_used = answer_mode == "rag"

        if not self.api_key:
            return SynthesizerVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning="API key not configured",
                retrieval_used=retrieval_used,
                synthesizer_path=answer_mode,
            )

        prompt = self._build_judge_prompt(user_query, source_data, synthesizer_output, answer_mode)

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(response, case_id, user_query, answer_mode)
            verdict.latency_ms = latency_ms
            verdict.judge_model = self.model_name
            return verdict

        except Exception as e:
            logger.error(f"Synthesizer Judge failed for {case_id}: {e}")
            return SynthesizerVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning=f"Judge evaluation error: {str(e)}",
                retrieval_used=retrieval_used,
                synthesizer_path=answer_mode,
            )

    def _build_judge_prompt(
        self,
        user_query: str,
        source_data: str,
        synthesizer_output: str,
        answer_mode: AnswerMode,
    ) -> str:
        """経路に応じた採点基準のプロンプトを、プロンプトファイルから組み立てる"""
        return get_prompt(
            f"synthesizer_judge_{answer_mode}",
            user_query=user_query,
            source_data=source_data,
            output=synthesizer_output,
        )

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Gemini API を Gateway 経由で呼び出す"""
        text = call_gemini(
            prompt=prompt,
            model=self.model_name,
            response_mime_type="application/json",
            feature="synthesizer_judge",
            user_id="",  # system-initiated batch job
        )
        if not text:
            raise ValueError("Gateway returned no text from Gemini")
        return json.loads(text)

    def _parse_judge_response(
        self,
        response: Dict[str, Any],
        case_id: str,
        user_query: str,
        answer_mode: AnswerMode,
    ) -> SynthesizerVerdict:
        """Gemini の応答を SynthesizerVerdict に変換し、総合点と合否をコードで計算する"""

        def clamp(val, min_v=1, max_v=5):
            try:
                return max(min_v, min(max_v, int(val)))
            except (TypeError, ValueError):
                return min_v

        scored = SCORED_DIMENSIONS[answer_mode]
        # 対象項目はキー欠落時に最低点 1、対象外の項目は 0（評価対象外）
        scores = {dim: clamp(response.get(dim, 1)) for dim in scored}

        overall = round(sum(scores.values()) / len(scores), 2)
        passed = (
            overall >= PASS_THRESHOLD
            and scores["factual_accuracy"] >= FACTUAL_ACCURACY_FLOOR
        )

        issues = response.get("issues", [])
        if not isinstance(issues, list):
            issues = []

        retrieval_used = answer_mode == "rag"
        context_relevance = (
            clamp(response.get("context_relevance", 0), min_v=0) if retrieval_used else 0
        )

        return SynthesizerVerdict(
            case_id=case_id,
            user_query=user_query,
            factual_accuracy=scores.get("factual_accuracy", 0),
            analytical_depth=scores.get("analytical_depth", 0),
            language_quality=scores.get("language_quality", 0),
            structure=scores.get("structure", 0),
            completeness=scores.get("completeness", 0),
            context_relevance=context_relevance,
            retrieval_used=retrieval_used,
            overall_score=overall,
            passed=passed,
            reasoning=response.get("reasoning", ""),
            issues=issues,
            synthesizer_path=answer_mode,
        )
