"""
LLM as a Judge #4 - Supervisor ルーティング品質評価サービス

Supervisor Agent のルーティング判断（batter/pitcher/stats/matchup）を
LLM Judge が多次元で評価します。

ルーティングプロンプト (routing_v1.txt) の分類ルール:
- batter: 打撃成績、本塁打王、打率ランキング、状況別打撃
- pitcher: 投球成績、防御率、奪三振王、WHIP等
- matchup: 特定の打者vs投手の対戦成績
- stats: その他（チーム成績、リーグ全体等）
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

# 有効なルーティング先
VALID_ROUTES = ("batter", "pitcher", "stats", "matchup")


@dataclass
class RoutingVerdict:
    """ルーティング判断の品質評価結果"""

    # ケース情報
    case_id: str
    user_query: str
    actual_route: str       # Supervisorが選んだルーティング先
    expected_route: str     # 正解のルーティング先（ゴールデンデータセット）

    # 3次元スコア (1-5)
    route_accuracy: int = 0          # ルーティング正確性: 正しいエージェントを選んだか
    ambiguity_handling: int = 0      # 曖昧性対応: 曖昧なクエリへの対応は適切か
    reasoning_quality: int = 0       # 判断根拠の質: 分類理由は論理的か
    overall_score: float = 0.0

    # 判定結果
    passed: bool = False
    is_exact_match: bool = False     # actual_route == expected_route
    reasoning: str = ""
    ambiguity_notes: str = ""        # 曖昧性に関する注記（二刀流選手等）

    # メタデータ
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-2.0-flash"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


PASS_THRESHOLD = 3.5


class RoutingJudgeService:
    """Supervisor ルーティングの品質を LLM Judge で評価するサービス"""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.api_key = GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY_V2 is not set.")

    def evaluate_routing(
        self,
        case_id: str,
        user_query: str,
        actual_route: str,
        expected_route: str,
    ) -> RoutingVerdict:
        """
        Supervisor のルーティング判断を評価する。

        Args:
            case_id: テストケースID
            user_query: ユーザーの元の質問
            actual_route: Supervisorの実際のルーティング先
            expected_route: 正解のルーティング先
        """
        is_exact_match = actual_route == expected_route

        if not self.api_key:
            return RoutingVerdict(
                case_id=case_id,
                user_query=user_query,
                actual_route=actual_route,
                expected_route=expected_route,
                is_exact_match=is_exact_match,
                reasoning="API key not configured",
            )

        prompt = self._build_judge_prompt(
            user_query, actual_route, expected_route
        )

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(
                response, case_id, user_query, actual_route, expected_route
            )
            verdict.latency_ms = latency_ms
            verdict.is_exact_match = is_exact_match
            verdict.judge_model = self.model_name
            return verdict

        except Exception as e:
            logger.error(f"Routing Judge failed for {case_id}: {e}")
            return RoutingVerdict(
                case_id=case_id,
                user_query=user_query,
                actual_route=actual_route,
                expected_route=expected_route,
                is_exact_match=is_exact_match,
                reasoning=f"Judge evaluation error: {str(e)}",
            )

    def _build_judge_prompt(
        self,
        user_query: str,
        actual_route: str,
        expected_route: str,
    ) -> str:
        """Judge 用の評価プロンプトを構築"""

        return f"""あなたはMLBデータ分析システムの Supervisor ルーティング品質審判です。

ユーザーの質問に対して、Supervisor Agent が選択したルーティング先が適切かを評価してください。

## 評価対象
- ユーザーの質問: "{user_query}"
- Supervisorのルーティング先: **{actual_route}**
- 期待されるルーティング先: **{expected_route}**

## ルーティングルール（routing_v1.txt より）
- **batter**: 打撃成績、本塁打王、打率ランキング、状況別打撃など。「〜王は誰？」「トップは？」などの現在のランキング質問も含む。
- **pitcher**: 投球成績、防御率、奪三振王、WHIPランキング、状況別スタッツ等。「最多〜は誰？」などの現在のランキング質問も含む。
- **matchup**: 対戦成績（特定の打者vs投手の過去の対決履歴）
- **stats**: その他（チーム成績、リーグ全体など）

## 注意事項
- **二刀流選手**（大谷翔平等）: 質問内容によってbatter/pitcherどちらも正解になりうる。
  質問が打撃に関するなら batter、投球に関するなら pitcher が正解。
  曖昧な場合（「大谷翔平の成績」等）はどちらも許容される可能性がある。
- **ランキング質問**: 「HR王は？」→ batter、「奪三振王は？」→ pitcher
- **比較質問**: 「AとBの打率を比較」→ batter、「AとBの対戦成績」→ matchup

## 評価基準

### 1. route_accuracy (1-5) - ルーティング正確性
正しいエージェントを選択したか。
- 5: 完全に正しいルーティング
- 4: 正しいが、より適切な選択肢があった
- 3: 許容範囲だが最適ではない（曖昧なケースで別の選択肢を選んだ）
- 2: 誤ったルーティングだが、関連性はある
- 1: 完全に誤ったルーティング

### 2. ambiguity_handling (1-5) - 曖昧性対応
曖昧なクエリに対する対応の適切さ（明確なクエリには5を付与）。
- 5: 曖昧さがない、または曖昧さを適切に解決
- 4: 概ね適切な対応だが改善の余地あり
- 3: 曖昧さの対応が中途半端
- 2: 曖昧なクエリを誤って解釈
- 1: 明らかに誤った解釈

### 3. reasoning_quality (1-5) - 判断根拠の質
ルーティング判断の論理的妥当性。
- 5: 判断根拠が明確で論理的
- 4: 概ね論理的
- 3: 根拠はあるが不十分
- 2: 根拠が不明確
- 1: 根拠がない、または矛盾

## 出力形式
{{
    "route_accuracy": <1-5>,
    "ambiguity_handling": <1-5>,
    "reasoning_quality": <1-5>,
    "overall_score": <1.0-5.0>,
    "passed": <true/false>,
    "reasoning": "<ルーティング判断の評価を日本語で1-2文>",
    "ambiguity_notes": "<曖昧性がある場合の注記（なければ空文字）>"
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
        actual_route: str,
        expected_route: str,
    ) -> RoutingVerdict:
        """Gemini の応答を RoutingVerdict に変換"""

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

        return RoutingVerdict(
            case_id=case_id,
            user_query=user_query,
            actual_route=actual_route,
            expected_route=expected_route,
            route_accuracy=clamp(response.get("route_accuracy", 1)),
            ambiguity_handling=clamp(response.get("ambiguity_handling", 1)),
            reasoning_quality=clamp(response.get("reasoning_quality", 1)),
            overall_score=overall,
            passed=overall >= PASS_THRESHOLD,
            reasoning=response.get("reasoning", ""),
            ambiguity_notes=response.get("ambiguity_notes", ""),
        )
