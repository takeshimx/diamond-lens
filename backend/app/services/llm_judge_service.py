"""
LLM as a Judge - パース精度評価サービス
LLMを「審判」として使い、パース結果を多次元で意味的に評価します。
既存のルールベース評価（evaluate_llm_accuracy.py）を補完する目的です。
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
class JudgeVerdict:
    """LLM Judge の評価結果を格納するデータクラス"""

    # テストケース情報
    case_id: str
    user_query: str

    # 次元別スコア (1-5)
    query_type_accuracy: int = 0
    metrics_accuracy: int = 0
    entity_resolution: int = 0
    intent_understanding: int = 0
    overall_score: float = 0.0
    # 判定結果
    passed: bool = False
    reasoning: str = ""
    failure_category: Optional[str] = None  # synonym_mismatch, entity_error, missing_context, etc.

    # メタデータ
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-2.0-flash"
    latency_ms: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# 合格判定の閾値
PASS_THRESHOLD = 3.5  # overall_score がこれ以上なら PASS


class LLMJudgeService:
    """LLM を評価者（Judge）として使用してパース精度を判定するサービス"""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.api_key = GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY_V2 is not set. LLM Judge will not work.")
    
    def evaluate_parse_result(
        self,
        case_id: str,
        user_query: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> JudgeVerdict:
        """
        LLM Judge が expected vs actual を多次元評価する。
        Args:
            case_id: テストケースID (例: "GD-001")
            user_query: ユーザーの元の質問
            expected: ゴールデンデータセットの期待値
            actual: LLMパーサーが実際に出力した結果
        Returns:
            JudgeVerdict: 多次元評価結果
        """
        if not self.api_key:
            return JudgeVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning="API key not configured",
            )
        
        prompt = self._build_judge_prompt(user_query, expected, actual)

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(response, case_id, user_query)
            verdict.latency_ms = latency_ms
            verdict.judge_model = self.model_name
            return verdict
        except Exception as e:
            logger.error(f"LLM Judge evaluation failed for {case_id}: {e}")
            return JudgeVerdict(
                case_id=case_id,
                user_query=user_query,
                reasoning=f"Judge evaluation error: {str(e)}",
            )
    
    def _build_judge_prompt(
        self,
        user_query: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> str:
        """Judge用の評価プロンプトを構築"""

        # METRIC_MAPの登録キー一覧をプロンプトに注入
        valid_metric_keys = self._get_valid_metric_keys()

        return f"""あなたはMLBデータ分析システムの品質評価の審判（Judge）です。
ユーザーの質問に対するLLMパーサーの出力を、期待値と比較して多次元で評価してください。
## 評価対象
- ユーザーの質問: "{user_query}"
- 期待値 (Expected): {json.dumps(expected, ensure_ascii=False, indent=2)}
- 実際の出力 (Actual): {json.dumps(actual, ensure_ascii=False, indent=2)}
## 重要なシステム制約
このシステムでは、`metrics` フィールドの値は以下の METRIC_MAP に登録されたキーのいずれかでなければなりません。
登録されていないキー（例: "avg", "hr", "k" 等の略称）を使用すると、後続のSQL構築が失敗します。
**登録済みキー一覧**: {valid_metric_keys}
**特別キーワード**: "main_stats" は展開用の特別キーワードとして許可
つまり、LLMパーサーが "avg" を返した場合、野球用語としては打率を意味しますが、
システム上は "batting_average" でなければ動作しないため、これは正当なエラーです。
## 評価基準
### 1. query_type_accuracy (1-5)
クエリタイプの分類が正しいか。
- 5: 完全一致
- 4: 意味的に同等（例: season_batting と batting_splits の境界ケース）
- 3: 部分的に正しい
- 1-2: 明らかに誤分類
### 2. metrics_accuracy (1-5)
メトリクスの抽出が正しいか。上記の METRIC_MAP 登録キーとの一致で判定してください。
- 5: 全メトリクスが METRIC_MAP の登録キーと完全一致、かつ期待値と一致
- 4: 登録キーは正しいが、不要なメトリクスが追加されている
- 3: 一部のメトリクスが未登録キー（略称等）になっている
- 2: 主要メトリクスが未登録キーになっている
- 1: 根本的に間違い
### 3. entity_resolution (1-5)
選手名の解決が正しいか。日本語 → 英語フルネームの変換精度。
- 5: 完全一致
- 4: 表記揺れ（Jr. の有無等）があるが同一人物
- 3: 姓名の順序が異なるが識別可能
- 1-2: 別人、または解決できていない
- N/A: 選手名が関係ない場合は5
### 4. intent_understanding (1-5)
ユーザーの全体的な意図を正しく理解しているか。
season, limit, order_by, output_format, split_type などの補助パラメータを含む総合判断。
- 5: 完全に意図を捉えている
- 4: 些細な差異あるが、本質的に正しい
- 3: 概ね正しいが重要なニュアンスを見落としている
- 1-2: 意図を大幅に誤解している
## 失敗カテゴリ（overall_score が 3.5 未満の場合のみ）
以下から最も当てはまるものを1つ選んでください:
- "unregistered_metric_key": METRIC_MAP に登録されていない略称・別名を使用した
- "entity_resolution_error": 選手名の変換ミス
- "missing_context": 年度やランキング条件の欠落
- "schema_violation": JSONスキーマ違反
- "over_extraction": 不要なパラメータの過剰抽出
- "type_misclassification": query_type の誤分類
- "none": 失敗なし
## 出力形式
以下のJSONを返してください:
{{
    "query_type_accuracy": <1-5>,
    "metrics_accuracy": <1-5>,
    "entity_resolution": <1-5>,
    "intent_understanding": <1-5>,
    "overall_score": <1.0-5.0の小数>,
    "passed": <true/false>,
    "reasoning": "<判定理由を日本語で1-2文>",
    "failure_category": "<カテゴリ名 or null>"
}}"""

    @staticmethod
    def _get_valid_metric_keys() -> str:
        """METRIC_MAP から登録済みキー一覧を取得してプロンプト用にフォーマット"""
        try:
            from backend.app.config.query_maps import METRIC_MAP
            keys = sorted(METRIC_MAP.keys())
            return json.dumps(keys, ensure_ascii=False)
        except ImportError:
            # テスト環境等でインポートできない場合のフォールバック
            return json.dumps([
                "homerun", "batting_average", "on_base_percentage",
                "slugging_percentage", "on_base_plus_slugging", "at_bats",
                "hits", "runs_batted_in", "stolen_bases", "strikeouts",
                "games", "war", "era", "whip", "fip", "wins",
                "innings_pitched", "games_started", "hits_allowed",
                "runs", "earned_runs", "base_on_balls",
                "batting_average_against"
            ])
    
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
    ) -> JudgeVerdict:
        """Gemini の応答を JudgeVerdict に変換"""
        # スコアのクランプ (1-5)
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

        return JudgeVerdict(
            case_id=case_id,
            user_query=user_query,
            query_type_accuracy=clamp(response.get("query_type_accuracy", 1)),
            metrics_accuracy=clamp(response.get("metrics_accuracy", 1)),
            entity_resolution=clamp(response.get("entity_resolution", 1)),
            intent_understanding=clamp(response.get("intent_understanding", 1)),
            overall_score=overall,
            passed=overall >= PASS_THRESHOLD,
            reasoning=response.get("reasoning", ""),
            failure_category=response.get("failure_category"),
        )


# Singleton
_judge_instance: Optional[LLMJudgeService] = None

def get_llm_judge() -> LLMJudgeService:
    """LLMJudgeServiceのシングルトンインスタンスを取得"""
    global _judge_instance
    if _judge_instance is None:
        _judge_instance = LLMJudgeService()
    return _judge_instance