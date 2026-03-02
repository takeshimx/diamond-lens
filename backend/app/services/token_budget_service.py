"""
Daily LLM Token Budget Tracking (In-Memory)
インメモリで日次トークン使用量を記録し、予算超過を検出する。
Redis不要。Cloud Runコンテナ再起動時にリセットされるが、
コスト防御目的には十分機能する。
"""
import threading
from datetime import datetime, timezone
from backend.app.config.settings import get_settings
from backend.app.utils.structured_logger import get_logger

logger = get_logger("token-budget")


class TokenBudgetService:

    def __init__(self):
        settings = get_settings()
        self.daily_budget = settings.llm_daily_token_budget
        self._usage: int = 0
        self._current_date: str = ""
        self._lock = threading.Lock()

    def _today(self) -> str:
        """今日の日付文字列（UTC基準）"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_if_new_day(self) -> None:
        """日付が変わっていたらカウンターをリセット"""
        today = self._today()
        if self._current_date != today:
            self._usage = 0
            self._current_date = today

    def record_usage(self, tokens_used: int) -> None:
        """トークン使用量を記録"""
        with self._lock:
            self._reset_if_new_day()
            self._usage += tokens_used

    def get_usage(self) -> int:
        """本日のトークン使用量を取得"""
        with self._lock:
            self._reset_if_new_day()
            return self._usage

    def is_budget_exceeded(self) -> bool:
        """予算超過かどうかを判定"""
        return self.get_usage() >= self.daily_budget

    def get_remaining(self) -> int:
        """残りトークン数"""
        return max(0, self.daily_budget - self.get_usage())


_instance = None


def get_token_budget_service() -> TokenBudgetService:
    global _instance
    if _instance is None:
        _instance = TokenBudgetService()
    return _instance
