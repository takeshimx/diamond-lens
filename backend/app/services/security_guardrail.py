"""
Security Guardrail Service
LLM に到達する前にプロンプトインジェクション・オフトピックリクエストを検知・ブロックする。
"""

import re
import logging
from typing import Tuple
from backend.app.services.llm_logger_service import get_llm_logger, LLMLogEntry
from backend.app.middleware.request_context import get_request_id

logger = logging.getLogger(__name__)


class SecurityGuardrail:
    """
    ユーザー入力に対する3段階のセキュリティチェックを提供する。

    Layer 1: Injection パターン検知（正規表現）
    Layer 2: オフトピック検知（MLBドメイン外のリクエスト）
    Layer 3: 入力長・構造の異常検知
    """

        # ---- Layer 1: プロンプトインジェクション検知パターン ----
    INJECTION_PATTERNS = [
        # === システムプロンプトの上書き試行 ===
        # 英語
        (r"(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
         "system_prompt_override"),
        # 日本語
        (r"(前の|上記の|これまでの|今までの|以前の)(指示|命令|ルール|プロンプト|設定).*(無視|忘れ|従わな|破棄|取り消)",
         "system_prompt_override"),
        (r"(指示|命令|ルール|プロンプト).*(全て|すべて|全部).*(無視|忘れ|リセット)",
         "system_prompt_override"),

        # === ロール再割り当て ===
        # 英語
        (r"(?i)you\s+are\s+now\s+a",
         "role_reassignment"),
        (r"(?i)(new\s+instructions?|your\s+new\s+role|act\s+as\s+if)",
         "role_reassignment"),
        # 日本語
        (r"(あなたは|お前は|君は).*(今から|これから|以後).*(として|になって|に変わ|で振る舞)",
         "role_reassignment"),
        (r"(新しい|別の)(役割|ロール|キャラ|人格|モード).*(切り替|変更|設定|なって)",
         "role_reassignment"),

        # === 情報漏洩の試行 ===
        # 英語
        (r"(?i)(reveal|show|display|output|print)\s+(me\s+)?(your\s+|the\s+)?(system\s+)?(prompt|instructions|rules|configuration)",
         "info_extraction"),
        (r"(?i)what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules)",
         "info_extraction"),
        # 日本語
        (r"(システム|内部)(プロンプト|指示|命令|設定|ルール).*(教えて|見せて|表示|出力|開示)",
         "info_extraction"),
        (r"(プロンプト|指示|命令|設定).*(何|どんな|どういう).*(です|ですか|なの|？|\?)",
         "info_extraction"),
        (r"(裏の|隠された|秘密の)(指示|命令|プロンプト|設定)",
         "info_extraction"),

        # === コード実行の試行 ===
        # 英語
        (r"(?i)(execute|run|eval)\s+(this\s+)?(code|command|script|python|javascript|sql)",
         "code_execution"),
        (r"(?i)(import\s+os|subprocess|__import__|exec\(|eval\()",
         "code_execution"),
        # 日本語
        (r"(このコード|スクリプト|コマンド).*(実行|走らせ|動かし|評価)",
         "code_execution"),

        # === SQLインジェクション（LLMプロンプト経由） ===
        (r"(?i)(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+.+\s+SET|ALTER\s+TABLE)",
         "sql_injection"),
        (r"(?i)(UNION\s+SELECT|;\s*SELECT|--\s*$)",
         "sql_injection"),
        # 日本語（SQLキーワードは英語だが、日本語文中に混ぜるケース）
        (r"(?i)(テーブル|データ).*(削除|消して|DROP|DELETE)",
         "sql_injection"),

        # === Jailbreak テンプレート ===
        # 英語
        (r"(?i)(DAN|do\s+anything\s+now|jailbreak|bypass\s+.{0,20}(filter|safety|guardrail))",
         "jailbreak_attempt"),
        (r"(?i)(pretend\s+(you\s+)?(are|have)\s+no\s+(restrictions|limitations|rules))",
         "jailbreak_attempt"),
        # 日本語
        (r"(制限|制約|規制|フィルター|ガードレール|安全装置).*(解除|外して|無効|無くして|なしで|オフ|取り除|突破|回避)",
         "jailbreak_attempt"),
        (r"(制限|ルール|制約).*(ない|なし|無い)(ふり|つもり|として|モード)",
         "jailbreak_attempt"),
        (r"(何でも|なんでも)(答えて|教えて|できる|やって).*(制限|制約|ルール).*(なし|無し|関係なく|気にせず)",
         "jailbreak_attempt"),
    ]

    # ---- Layer 2: オフトピック検知 ----
    # MLB関連キーワード（日本語 + 英語）
    MLB_DOMAIN_KEYWORDS = [
        # 日本語キーワード
        "打率", "本塁打", "防御率", "奪三振", "打撃", "投手", "投球", "打者",
        "ホームラン", "安打", "盗塁", "出塁率", "長打率", "OPS",
        "得点圏", "ランナー", "満塁", "イニング", "球種", "球速",
        "成績", "スタッツ", "ランキング", "対戦", "対決", "シーズン",
        "大谷", "選手", "リーグ", "チーム", "野球", "メジャー",
        # 英語キーワード
        "batting", "pitching", "ERA", "HR", "RBI", "AVG",
        "OBP", "SLG", "WAR", "WHIP", "strikeout", "hit",
        "homerun", "home run", "pitcher", "batter", "player",
        "MLB", "baseball", "season", "stats", "matchup",
        "ohtani", "judge", "trout", "darvish",
        # 数値・シーズン関連
        "2024", "2025", "2026",
    ]

    # 明らかにオフトピックなパターン
    OFF_TOPIC_PATTERNS = [
        (r"(?i)(write\s+(me\s+)?a\s+(poem|story|essay|song|letter))", "creative_writing"),
        (r"(?i)(recipe|cook|料理|レシピ)", "cooking"),
        (r"(?i)(translate|翻訳)\s+.{20,}", "translation_service"),
        (r"(?i)(hack|exploit|phishing|malware|password\s+crack)", "malicious_intent"),
        (r"(?i)(bitcoin|crypto|stock\s+market|投資|仮想通貨)", "financial"),
    ]

    # ---- Layer 3: 構造的な異常検知 ----
    MAX_QUERY_LENGTH = 500  # MLBクエリとして妥当な最大文字数
    MAX_LINE_COUNT = 5       # 複数行のプロンプトは通常不要

    def validate(self, query: str) -> Tuple[bool, str]:
        """
        ユーザークエリの安全性を検証する。

        Args:
            query: ユーザーからの入力文字列

        Returns:
            Tuple[bool, str]: (安全かどうか, 拒否理由またはパターン名)
            安全な場合は (True, "ok") を返す。
        """
        # Layer 3: 構造チェック（最も軽量なので最初に実行）
        is_safe, reason = self._check_structure(query)
        if not is_safe:
            return False, reason

        # Layer 1: インジェクションパターン検知
        is_safe, reason = self._check_injection_patterns(query)
        if not is_safe:
            return False, reason

        # Layer 2: オフトピック検知
        is_safe, reason = self._check_off_topic(query)
        if not is_safe:
            return False, reason

        return True, "ok"
    
    def _check_structure(self, query: str) -> Tuple[bool, str]:
        """Layer 3: 入力の構造的な異常を検知"""
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, "query_too_long"

        if query.count("\n") > self.MAX_LINE_COUNT:
            return False, "excessive_line_breaks"

        # 空文字チェック
        if not query or not query.strip():
            return False, "empty_query"

        return True, "ok"
    
    def _check_injection_patterns(self, query: str) -> Tuple[bool, str]:
        """Layer 1: 正規表現によるインジェクションパターン検知"""
        for pattern, pattern_name in self.INJECTION_PATTERNS:
            if re.search(pattern, query):
                logger.warning(
                    f"🚨 Injection pattern detected: {pattern_name}",
                    extra={"query_preview": query[:100], "pattern": pattern_name}
                )
                return False, pattern_name

        return True, "ok"
    
    def _check_off_topic(self, query: str) -> Tuple[bool, str]:
        """Layer 2: MLBドメイン外のリクエストを検知"""
        query_lower = query.lower()

        # まずMLBキーワードが含まれているか確認
        has_mlb_keyword = any(
            keyword.lower() in query_lower for keyword in self.MLB_DOMAIN_KEYWORDS
        )

        # MLBキーワードが1つでもあれば通過（ドメイン内と判断）
        if has_mlb_keyword:
            return True, "ok"

        # MLBキーワードがない場合、明確なオフトピックパターンをチェック
        for pattern, pattern_name in self.OFF_TOPIC_PATTERNS:
            if re.search(pattern, query):
                logger.warning(
                    f"🚫 Off-topic request detected: {pattern_name}",
                    extra={"query_preview": query[:100], "pattern": pattern_name}
                )
                return False, f"off_topic:{pattern_name}"

        # MLBキーワードなし＆明確なオフトピックパターンなし → 一旦通過させる
        # （曖昧なクエリを誤ってブロックしないため）
        return True, "ok"
    
    def validate_and_log(self, query: str) -> Tuple[bool, str]:
        """
        検証を行い、ブロックした場合はBigQueryにインシデントログを記録する。

        Args:
            query: ユーザークエリ

        Returns:
            Tuple[bool, str]: (安全かどうか, 拒否理由)
        """
        is_safe, reason = self.validate(query)

        if not is_safe:
            self._log_incident(query, reason)

        return is_safe, reason
    
    def _log_incident(self, query: str, detected_pattern: str):
        """ブロックしたインシデントをBigQueryに記録する"""
        try:
            llm_logger = get_llm_logger()
            log_entry = LLMLogEntry()
            log_entry.request_id = get_request_id()
            log_entry.user_query = query[:200]  # プライバシー配慮で先頭200文字のみ
            log_entry.success = False
            log_entry.error_type = "injection_attempt"
            log_entry.error_message = f"Guardrail blocked: {detected_pattern}"
            log_entry.endpoint = "/qa/agentic-stats"
            llm_logger.log(log_entry)
        except Exception as e:
            # ログ失敗でもメインフローは止めない
            logger.error(f"Failed to log guardrail incident: {e}")


# シングルトンインスタンス
_guardrail_instance = None

def get_security_guardrail() -> SecurityGuardrail:
    """シングルトンの SecurityGuardrail を取得"""
    global _guardrail_instance
    if _guardrail_instance is None:
        _guardrail_instance = SecurityGuardrail()
    return _guardrail_instance

