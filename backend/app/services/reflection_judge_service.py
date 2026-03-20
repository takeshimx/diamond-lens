"""
LLM as a Judge #3 - Reflection Loop 判断品質評価サービス

Reflection Loop（自己修正）の判断と修正結果を多次元で評価します。
- should_reflect() のトリガー判断は適切だったか
- reflection_node() の修正策は根本原因を特定できたか
- 過修正（over-correction）していないか
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
class ReflectionVerdict:
    """Reflection Loop の品質評価結果"""

    # ケース情報
    case_id: str
    user_query: str
    trigger_reason: str  # "sql_error" | "empty_result" | "unknown_error"

    # 4次元スコア (1-5)
    trigger_appropriateness: int = 0   # トリガー適切性: Reflectionすべきだったか
    root_cause_identification: int = 0  # 根本原因特定: エラーの真因を捉えたか
    correction_quality: int = 0         # 修正品質: 修正策は適切か
    over_correction_risk: int = 0       # 過修正リスク: 不要な変更をしていないか (5=リスクなし)
    overall_score: float = 0.0

    # 判定結果
    passed: bool = False
    reasoning: str = ""
    identified_root_cause: str = ""     # Judgeが特定した根本原因
    suggested_improvement: str = ""     # Judgeの改善提案

    # メタデータ
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-2.0-flash"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


PASS_THRESHOLD = 3.5


class ReflectionJudgeService:
    """Reflection Loop の判断品質を LLM Judge で評価するサービス"""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.api_key = GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY_V2 is not set.")

    def evaluate_reflection(
        self,
        case_id: str,
        user_query: str,
        trigger_reason: str,
        error_context: str,
        pre_reflection_state: Dict[str, Any],
        post_reflection_state: Dict[str, Any],
        retry_count: int = 0,
    ) -> ReflectionVerdict:
        """
        Reflection の判断と修正結果を評価する。

        Args:
            case_id: テストケースID
            user_query: ユーザーの元の質問
            trigger_reason: トリガー理由 ("sql_error" | "empty_result" | "unknown_error")
            error_context: エラーの詳細コンテキスト
            pre_reflection_state: Reflection前の状態（エラーメッセージ、失敗クエリ等）
            post_reflection_state: Reflection後の状態（修正クエリ、結果等）
            retry_count: 現在のリトライ回数
        """
        if not self.api_key:
            return ReflectionVerdict(
                case_id=case_id,
                user_query=user_query,
                trigger_reason=trigger_reason,
                reasoning="API key not configured",
            )

        prompt = self._build_judge_prompt(
            user_query, trigger_reason, error_context,
            pre_reflection_state, post_reflection_state, retry_count,
        )

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(
                response, case_id, user_query, trigger_reason
            )
            verdict.latency_ms = latency_ms
            verdict.retry_count = retry_count
            verdict.judge_model = self.model_name
            return verdict

        except Exception as e:
            logger.error(f"Reflection Judge failed for {case_id}: {e}")
            return ReflectionVerdict(
                case_id=case_id,
                user_query=user_query,
                trigger_reason=trigger_reason,
                reasoning=f"Judge evaluation error: {str(e)}",
            )

    def _build_judge_prompt(
        self,
        user_query: str,
        trigger_reason: str,
        error_context: str,
        pre_state: Dict[str, Any],
        post_state: Dict[str, Any],
        retry_count: int,
    ) -> str:
        """Judge 用の評価プロンプトを構築"""

        pre_json = json.dumps(pre_state, ensure_ascii=False, indent=2, default=str)
        post_json = json.dumps(post_state, ensure_ascii=False, indent=2, default=str)

        return f"""あなたはMLBデータ分析システムの自己修正（Reflection Loop）品質審判です。

エージェントがエラーに遭遇した際のReflection（自己修正）プロセスを評価してください。

## 評価対象
- ユーザーの元の質問: "{user_query}"
- Reflectionのトリガー理由: {trigger_reason}
- リトライ回数: {retry_count}

### エラーコンテキスト
```
{error_context}
```

### Reflection前の状態（失敗時）
```json
{pre_json}
```

### Reflection後の状態（修正後）
```json
{post_json}
```

## Reflectionシステムの仕様
このシステムの should_reflect() は以下のルールで動作しています:
- **リトライする**: SQLシンタックスエラー、カラム名誤認識、空結果（0行）
- **リトライしない**: パーミッション/認証エラー、タイムアウト、データセット/スキーマエラー
- **最大リトライ**: 2回

## 評価基準

### 1. trigger_appropriateness (1-5) - トリガー適切性
Reflectionを発動すべき状況だったか。
- 5: 完全に正しいトリガー判断
- 4: 概ね正しいが、より早く/遅くトリガーすべきだった
- 3: トリガーは妥当だが、別のアプローチが良かった
- 2: 不要なReflectionだった可能性
- 1: 明らかに不要（パーミッションエラー等でリトライしている）

### 2. root_cause_identification (1-5) - 根本原因特定
エラーの根本原因を正しく特定できたか。
- 5: 根本原因を完璧に特定
- 4: 概ね正しい原因特定
- 3: 部分的に正しいが、表層的
- 2: 原因特定が不十分
- 1: 原因を全く特定できていない、または誤認

### 3. correction_quality (1-5) - 修正品質
修正アクション（クエリ修正、別アプローチ等）は適切か。
- 5: 最適な修正で問題を解決
- 4: 効果的な修正だが、改善の余地あり
- 3: 修正は機能するが、非効率または不完全
- 2: 修正が不適切
- 1: 修正がエラーを悪化させた、または全く機能しない

### 4. over_correction_risk (1-5) - 過修正リスク（5がベスト）
不要な条件緩和や無関係な変更をしていないか。
- 5: 必要最小限の修正のみ（リスクなし）
- 4: 軽微な追加変更があるが問題なし
- 3: やや広範な変更で副作用の可能性
- 2: 過修正で意図しない結果を返すリスク
- 1: 完全に別のクエリに書き換え（ユーザーの意図から逸脱）

## 出力形式
{{
    "trigger_appropriateness": <1-5>,
    "root_cause_identification": <1-5>,
    "correction_quality": <1-5>,
    "over_correction_risk": <1-5>,
    "overall_score": <1.0-5.0>,
    "passed": <true/false>,
    "reasoning": "<総合評価を日本語で2-3文>",
    "identified_root_cause": "<Judgeが特定した根本原因>",
    "suggested_improvement": "<改善提案>"
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
        trigger_reason: str,
    ) -> ReflectionVerdict:
        """Gemini の応答を ReflectionVerdict に変換"""

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

        return ReflectionVerdict(
            case_id=case_id,
            user_query=user_query,
            trigger_reason=trigger_reason,
            trigger_appropriateness=clamp(response.get("trigger_appropriateness", 1)),
            root_cause_identification=clamp(response.get("root_cause_identification", 1)),
            correction_quality=clamp(response.get("correction_quality", 1)),
            over_correction_risk=clamp(response.get("over_correction_risk", 1)),
            overall_score=overall,
            passed=overall >= PASS_THRESHOLD,
            reasoning=response.get("reasoning", ""),
            identified_root_cause=response.get("identified_root_cause", ""),
            suggested_improvement=response.get("suggested_improvement", ""),
        )
