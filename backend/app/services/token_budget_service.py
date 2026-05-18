"""
Daily LLM Token Budget Tracking (In-Memory)
インメモリで日次トークン使用量をプール別に記録し、予算超過を検出する。
Redis不要。Cloud Runコンテナ再起動時にリセットされるが、コスト防御目的には十分機能する。

Phase 3-A: プール分離
  - "chat":   ChatOrchestrator 経由 (チャット機能)
  - "report": StrategyAgent / strategy-report エンドポイント経由 (レポート機能)
  - "shared": 上記合算の hard cap (旧 llm_daily_token_budget 互換)
"""
import threading
from datetime import datetime, timezone
from typing import Dict, Literal

from backend.app.config.settings import get_settings
from backend.app.utils.structured_logger import get_logger

logger = get_logger("token-budget")

Pool = Literal["chat", "report", "shared"]


class TokenBudgetService:

    def __init__(self):
        settings = get_settings()
        # プール別予算
        self.daily_budget: Dict[str, int] = {
            "chat": settings.llm_daily_token_budget_chat,
            "report": settings.llm_daily_token_budget_report,
            "shared": settings.llm_daily_token_budget,  # 合算 hard cap
        }
        # プール別使用量
        self._usage: Dict[str, int] = {"chat": 0, "report": 0}
        self._current_date: str = ""
        self._lock = threading.Lock()

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_if_new_day(self) -> None:
        today = self._today()
        if self._current_date != today:
            self._usage = {"chat": 0, "report": 0}
            self._current_date = today

    def record_usage(self, tokens_used: int, pool: Pool = "chat") -> None:
        """指定プールにトークン使用量を記録する。

        Args:
            tokens_used: 加算するトークン数
            pool: "chat" または "report"。"shared" は記録不可 (合算は派生値)
        """
        if pool == "shared":
            raise ValueError(
                "'shared' プールには直接記録できません。chat か report を指定してください"
            )
        with self._lock:
            self._reset_if_new_day()
            self._usage[pool] += tokens_used
            logger.info(
                "token_budget_recorded",
                pool=pool,
                tokens=tokens_used,
                pool_usage=self._usage[pool],
                pool_remaining=max(0, self.daily_budget[pool] - self._usage[pool]),
            )

    def get_usage(self, pool: Pool = "chat") -> int:
        """指定プールの本日の使用量を取得。"""
        with self._lock:
            self._reset_if_new_day()
            if pool == "shared":
                return self._usage["chat"] + self._usage["report"]
            return self._usage[pool]

    def is_budget_exceeded(self, pool: Pool = "chat") -> bool:
        """指定プールが予算超過かどうかを判定。
        プール別上限 OR 合算 hard cap のいずれか超過なら True。
        """
        if pool == "shared":
            return self.get_usage("shared") >= self.daily_budget["shared"]
        return (
            self.get_usage(pool) >= self.daily_budget[pool]
            or self.get_usage("shared") >= self.daily_budget["shared"]
        )

    def get_remaining(self, pool: Pool = "chat") -> int:
        """指定プールの残りトークン数"""
        return max(0, self.daily_budget[pool] - self.get_usage(pool))


_instance = None


def get_token_budget_service() -> TokenBudgetService:
    global _instance
    if _instance is None:
        _instance = TokenBudgetService()
    return _instance
