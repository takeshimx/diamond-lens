"""
LLM as a Judge #5 - Data Drift アラート品質評価サービス

統計的ドリフト検知結果を LLM が解釈し、
「本当に対応が必要なドリフトか」を判定するセカンドオピニオン層。
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
class DriftAlertVerdict:
    """ドリフトアラートの品質評価結果"""

    # レポート情報
    report_id: str
    model_type: str
    drift_type: str  # "feature" | "prediction" | "concept"

    # 4次元スコア (1-5)
    statistical_validity: int = 0     # 統計的妥当性: 検定結果は信頼できるか
    practical_significance: int = 0   # 実用的重要性: モデル性能に影響するか
    actionability: int = 0            # 対応可能性: 具体的な対応が取れるか
    domain_relevance: int = 0         # ドメイン関連性: 野球分析の文脈で意味があるか
    overall_score: float = 0.0

    # 判定結果
    action_required: bool = False     # 対応が必要か
    recommended_action: str = ""      # "retrain" | "monitor" | "ignore"
    reasoning: str = ""
    risk_factors: List[str] = field(default_factory=list)

    # メタデータ
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    judge_model: str = "gemini-2.0-flash"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# action_required の閾値
ACTION_THRESHOLD = 3.5


class DriftAlertJudgeService:
    """ドリフトアラートの品質を LLM Judge で評価するサービス"""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.api_key = GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY_V2 is not set.")

    def evaluate_drift_report(
        self,
        drift_report: Dict[str, Any],
    ) -> DriftAlertVerdict:
        """
        DriftReport の内容を LLM Judge が評価する。

        Args:
            drift_report: DriftReport.to_dict() の出力
        """
        report_id = drift_report.get("report_id", "unknown")
        model_type = drift_report.get("model_type", "unknown")
        drift_type = drift_report.get("drift_type", "feature")

        if not self.api_key:
            return DriftAlertVerdict(
                report_id=report_id,
                model_type=model_type,
                drift_type=drift_type,
                reasoning="API key not configured",
            )

        prompt = self._build_judge_prompt(drift_report)

        start_time = datetime.now()
        try:
            response = self._call_gemini(prompt)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            verdict = self._parse_judge_response(
                response, report_id, model_type, drift_type
            )
            verdict.latency_ms = latency_ms
            verdict.judge_model = self.model_name
            return verdict

        except Exception as e:
            logger.error(f"Drift Alert Judge failed for {report_id}: {e}")
            return DriftAlertVerdict(
                report_id=report_id,
                model_type=model_type,
                drift_type=drift_type,
                reasoning=f"Judge evaluation error: {str(e)}",
            )

    def _build_judge_prompt(self, drift_report: Dict[str, Any]) -> str:
        """Judge 用の評価プロンプトを構築"""

        model_type = drift_report.get("model_type", "")
        drift_type = drift_report.get("drift_type", "")
        baseline = drift_report.get("baseline_season", "")
        target = drift_report.get("target_season", "")

        # モデル別のドメインコンテキストを注入
        domain_context = self._get_domain_context(model_type)

        report_json = json.dumps(drift_report, ensure_ascii=False, indent=2)

        return f"""あなたはMLBデータ分析システムのMLOpsエンジニアであり、データドリフト検知結果の品質審判です。

以下の統計的ドリフト検知レポートを分析し、「本当に対応が必要なドリフトか」を判定してください。

## ドリフト検知レポート
- モデル: {model_type}
- ドリフト型: {drift_type}
- 比較期間: {baseline} → {target}

```json
{report_json}
```

## モデルのドメインコンテキスト
{domain_context}

## 統計指標の解釈ガイド
- **KS検定**: p値 < 0.05 で統計的に有意だが、サンプルサイズが大きいと微小な差異でも有意になりやすい
- **PSI**: < 0.1 安定、0.1-0.2 軽度変化、> 0.2 有意な変化
- **平均値シフト**: MLBでは年度間で±5%程度の変動は自然（ルール変更・ボール変更等）
- **RMSE変化**: 10%未満の変化は許容範囲内のことが多い
- **相関低下**: 0.05未満の低下は統計的ノイズの可能性が高い

## 評価基準

### 1. statistical_validity (1-5) - 統計的妥当性
検定結果は信頼できるか。サンプルサイズ、多重検定の影響等。
- 5: 十分なサンプルサイズでの有意な検出
- 4: 概ね信頼できるが軽微な懸念あり
- 3: サンプルサイズ不足や境界的な結果
- 2: 信頼性に疑問
- 1: 統計的に無意味

### 2. practical_significance (1-5) - 実用的重要性
検出されたドリフトがモデル性能に実際に影響するか。
- 5: モデル性能に重大な影響が予想される
- 4: 中程度の影響が予想される
- 3: 軽微な影響の可能性
- 2: モデル性能への影響は限定的
- 1: 実用上ほぼ無影響

### 3. actionability (1-5) - 対応可能性
具体的な対応アクション（再学習、特徴量調整等）が取れるか。
- 5: 明確な対応策がある（例: 新データで再学習）
- 4: 対応策がほぼ明確
- 3: 対応策はあるが効果が不確実
- 2: 対応が困難
- 1: 対応不要または対応策なし

### 4. domain_relevance (1-5) - ドメイン関連性
MLBの文脈で、このドリフトに意味があるか。
- 5: 野球分析上重大（例: ボール変更による球速分布シフト）
- 4: 関連性が高い
- 3: ある程度関連がある
- 2: MLBの文脈では軽微
- 1: ルール変更や自然変動で説明可能

## 出力形式
{{
    "statistical_validity": <1-5>,
    "practical_significance": <1-5>,
    "actionability": <1-5>,
    "domain_relevance": <1-5>,
    "overall_score": <1.0-5.0>,
    "action_required": <true/false>,
    "recommended_action": "<retrain | monitor | ignore>",
    "reasoning": "<判定理由を日本語で2-3文>",
    "risk_factors": ["<リスク要因1>", "<リスク要因2>"]
}}"""

    @staticmethod
    def _get_domain_context(model_type: str) -> str:
        """モデル別のドメインコンテキストを返す"""
        contexts = {
            "batter_segmentation": (
                "打者セグメンテーション（KMeans）: OPS, ISO, K率, BB率でクラスタリング。"
                "年度間で打高/投高の傾向が変わると分布シフトは自然に起こりうる。"
                "ただし、クラスタの意味（パワーヒッター、コンタクトヒッター等）が"
                "変わるほどのドリフトは再学習が必要。"
            ),
            "pitcher_segmentation": (
                "投手セグメンテーション（KMeans）: ERA, K/9, GB%でクラスタリング。"
                "ルール変更（ピッチクロック等）の影響で投手スタッツが年度間でシフトする"
                "ことは想定内だが、セグメントの定義自体が変わるほどなら再学習推奨。"
            ),
            "stuff_plus": (
                "Stuff+（XGBoost）: 球速、回転数、変化量等の球質指標から失点期待値を予測。"
                "Hawk-Eyeシステムのアップデートやボール仕様変更で入力分布が変わる可能性がある。"
                "特に release_speed と release_spin_rate は計測精度に直結する重要特徴量。"
                "arm_angle も近年のMLBでは戦術的に極めて重要（長身左腕の変則アームアングルは"
                "対左打者の三振率に直結）であり、ドリフト検出時は注意が必要。"
            ),
            "pitching_plus": (
                "Pitching+（XGBoost）: Stuff+にコマンド指標（plate_x, plate_z）を追加。"
                "コマンド分布はボール変更よりも選手構成の変化に影響されやすい。"
            ),
            "pitching_plus_plus": (
                "Pitching++（XGBoost）: Pitching+にシーケンス特徴量を追加。"
                "prev_pitch_type や speed_diff は戦術トレンドの変化を反映するため、"
                "ドリフトが検出されても即座に再学習が必要とは限らない。"
            ),
        }
        return contexts.get(model_type, "ドメインコンテキスト情報なし")

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
        report_id: str,
        model_type: str,
        drift_type: str,
    ) -> DriftAlertVerdict:
        """Gemini の応答を DriftAlertVerdict に変換"""

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
        risk_factors = response.get("risk_factors", [])
        if not isinstance(risk_factors, list):
            risk_factors = []

        recommended = response.get("recommended_action", "monitor")
        if recommended not in ("retrain", "monitor", "ignore"):
            recommended = "monitor"

        return DriftAlertVerdict(
            report_id=report_id,
            model_type=model_type,
            drift_type=drift_type,
            statistical_validity=clamp(response.get("statistical_validity", 1)),
            practical_significance=clamp(response.get("practical_significance", 1)),
            actionability=clamp(response.get("actionability", 1)),
            domain_relevance=clamp(response.get("domain_relevance", 1)),
            overall_score=overall,
            action_required=overall >= ACTION_THRESHOLD,
            recommended_action=recommended,
            reasoning=response.get("reasoning", ""),
            risk_factors=risk_factors,
        )