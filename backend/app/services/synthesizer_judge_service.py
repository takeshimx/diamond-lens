"""
LLM as a Judge #2 - Synthesizer 出力品質評価サービス

Synthesizer が生成した分析レポートや回答の品質を多次元で評価します。
パース精度評価（llm_judge_service.py）と並行して使用します。
"""

import os
import json
import logging
import requests
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_V2")


@dataclass
class SynthesizerVerdict:
    """Synthesizer 出力の品質評価結果"""

    # テストケース情報
    case_id: str
    user_query: str

    # 5次元スコア (1-5)
    factual_accuracy: int = 0      # 事実正確性: データとの整合性
    analytical_depth: int = 0      # 分析深度: 「なぜ」への言及
    language_quality: int = 0      # 日本語品質: 自然さ、冗長さの回避
    structure: int = 0             # 構造: Markdown構造の適切さ
    completeness: int = 0          # 完全性: 質問への過不足ない回答
    overall_score: float = 0.0

    # 判定結果
    passed: bool = False
    reasoning: str = ""
    issues: List[str] = field(default_factory=list)  # 具体的な問題点リスト

    # メタデータ
    synthesizer_path: str = ""     # "agent" or "simple"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-2.0-flash"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


PASS_THRESHOLD = 3.5


class SynthesizerJudgeService:
    """Synthesizer 出力の品質を LLM Judge で評価するサービス"""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
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
        synthesizer_path: str = "agent",
    ) -> SynthesizerVerdict:
        """
        Synthesizer の出力を多次元評価する。

        Args:
            case_id: テストケースID
            user_query: ユーザーの元の質問
            source_data: Synthesizer に渡された元データ（JSON文字列）
            synthesizer_output: Synthesizer が生成した回答テキスト
            synthesizer_path: "agent" or "simple"
        """
        if not self.api_key:
            return SynthesizerVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning="API key not configured",
            )

        prompt = self._build_judge_prompt(
            user_query, source_data, synthesizer_output, synthesizer_path
        )

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(response, case_id, user_query)
            verdict.latency_ms = latency_ms
            verdict.synthesizer_path = synthesizer_path
            verdict.judge_model = self.model_name
            return verdict

        except Exception as e:
            logger.error(f"Synthesizer Judge failed for {case_id}: {e}")
            return SynthesizerVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning=f"Judge evaluation error: {str(e)}",
            )

    def _build_judge_prompt(
        self,
        user_query: str,
        source_data: str,
        synthesizer_output: str,
        synthesizer_path: str,
    ) -> str:
        """Judge 用の評価プロンプトを構築"""

        # パスに応じて期待される出力形式を切り替え
        if synthesizer_path == "agent":
            format_expectation = """
            Agent Flow の出力に求められる品質:
            - Markdown構造化（###見出し、箇条書き）
            - プロのMLBアナリストとしての分析視点
            - 冗長表現の回避、核心を突く記述"""
        else:
            format_expectation = """
            Simple Flow の出力に求められる品質:
            - 自然な文章での回答（表形式ではなく）
            - 「予測されています」等の推測表現は不可、断定的に事実を述べる
            - 簡潔で分かりやすい日本語"""

        return f"""あなたはMLBデータ分析システムの Synthesizer（最終回答生成）品質審判です。
ユーザーの質問に対して生成された回答を、元データと照らし合わせて多次元で評価してください。

## 評価対象
- ユーザーの質問: "{user_query}"
- 元データ (Synthesizerに渡されたデータ):
```json
{source_data}
```
- Synthesizer の出力:
```
{synthesizer_output}
```

## 出力形式の期待値
{format_expectation}

## 評価基準

### 1. factual_accuracy (1-5) - 事実正確性
元データとの整合性。数値の転記ミス、存在しない選手名の捏造等がないか。
- 5: 全数値・事実がデータと完全一致
- 4: 些細な丸め誤差があるが事実上正確
- 3: 一部の数値が不正確
- 2: 複数の事実誤認
- 1: データと大きく乖離、または捏造あり

### 2. analytical_depth (1-5) - 分析深度
単なるデータの朗読ではなく、「なぜ」「その意味は」に言及しているか。
- 5: 優れた分析的洞察を含む
- 4: 基本的な分析コメントあり
- 3: データの要約のみ（朗読に近い）
- 2: 情報が断片的で分析なし
- 1: 意味のある情報がほぼない

### 3. language_quality (1-5) - 日本語品質
自然で流暢な日本語か。主語の連続使用、冗長表現、不自然な書き出しがないか。
- 5: プロのスポーツライターレベル
- 4: 自然で読みやすい
- 3: やや不自然だが理解可能
- 2: 冗長、同じ主語の連続、機械的
- 1: 不自然な日本語で読みにくい

### 4. structure (1-5) - 構造
適切な見出し、箇条書き、段落分けができているか。
- 5: 情報が完璧に整理されている
- 4: 概ね適切な構造
- 3: 最低限の構造はあるが改善余地あり
- 2: 構造が不十分
- 1: 構造化されていない長文

### 5. completeness (1-5) - 完全性
ユーザーの質問に対して過不足なく回答できているか。
- 5: 質問に完全に回答＋有益な補足
- 4: 質問に完全に回答
- 3: 主要な部分は回答だが一部欠落
- 2: 回答が不完全
- 1: 質問に答えていない

## 出力形式
以下のJSONを返してください:
{{
    "factual_accuracy": <1-5>,
    "analytical_depth": <1-5>,
    "language_quality": <1-5>,
    "structure": <1-5>,
    "completeness": <1-5>,
    "overall_score": <1.0-5.0の小数>,
    "passed": <true/false>,
    "reasoning": "<総合的な判定理由を日本語で1-2文>",
    "issues": ["<具体的な問題点1>", "<問題点2>"]
}}"""

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Gemini API を呼び出す"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()

        if result.get("candidates"):
            json_string = result["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(json_string)

        raise ValueError("No candidates in Gemini response")

    def _parse_judge_response(
        self,
        response: Dict[str, Any],
        case_id: str,
        user_query: str,
    ) -> SynthesizerVerdict:
        """Gemini の応答を SynthesizerVerdict に変換"""

        def clamp(val, min_v=1, max_v=5):
            try:
                return max(min_v, min(max_v, int(val)))
            except (TypeError, ValueError):
                return min_v

        def clamp_float(val, min_v=1.0, max_v=5.0):
            try:
                return max(min_v, min(max_v, float(val)))
            except (TypeError, ValueError):
                return min_v

        overall = clamp_float(response.get("overall_score", 1.0))
        issues = response.get("issues", [])
        if not isinstance(issues, list):
            issues = []

        return SynthesizerVerdict(
            case_id=case_id,
            user_query=user_query,
            factual_accuracy=clamp(response.get("factual_accuracy", 1)),
            analytical_depth=clamp(response.get("analytical_depth", 1)),
            language_quality=clamp(response.get("language_quality", 1)),
            structure=clamp(response.get("structure", 1)),
            completeness=clamp(response.get("completeness", 1)),
            overall_score=overall,
            passed=overall >= PASS_THRESHOLD,
            reasoning=response.get("reasoning", ""),
            issues=issues,
        )
