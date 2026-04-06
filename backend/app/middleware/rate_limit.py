"""
Multi-tier Rate Limiting Middleware (In-Memory)
- Global: 全リクエスト合計で N req/min
- Per-Session: user_id or IP ごとに M req/min

Redis不要。Cloud Run単一コンテナ内で動作するインメモリカウンター方式。
スケールアウト時はインスタンスごとに独立したカウンターとなるが、
コスト防御目的には十分機能する。
"""
import time
import threading
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend.app.config.settings import get_settings
from backend.app.utils.structured_logger import get_logger
from backend.app.services.monitoring_service import get_monitoring_service
from backend.app.services.llm_logger_service import get_llm_logger, LLMLogEntry

logger = get_logger("rate_limit")


class RateLimitMiddleware:
    """
    ASGI Middleware for global and per-session rate limiting using in-memory counters.
    Fixed-window方式: 1分間ウィンドウ内のリクエスト数をカウント。
    """

    # レートリミットを適用しないパス
    EXEMPT_PATHS = {"/", "/health", "/debug/routes", "/docs", "/openapi.json", "/redoc", "/api/v1/live/games/today"}

    def __init__(self, app: ASGIApp):
        self.app = app
        settings = get_settings()
        self.enabled = settings.rate_limit_enabled
        self.global_limit = settings.rate_limit_global_per_minute
        self.session_limit = settings.rate_limit_session_per_minute
        self.window_seconds = 60  # 1分間のウィンドウ
        self.monitoring = get_monitoring_service()

        # インメモリカウンター: {key: (count, window_id)}
        self._counters: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path

        # 除外パスはスキップ
        if path in self.EXEMPT_PATHS or request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Global rate limit check
        global_key = "ratelimit:global"
        global_count = self._increment(global_key)

        if global_count > self.global_limit:
            retry_after = self._seconds_until_next_window()
            response = self._rate_limit_response(
                "Global rate limit exceeded", retry_after
            )
            await response(scope, receive, send)
            logger.warning("Global rate limit exceeded", count=global_count)
            self.monitoring.record_rate_limit_rejection(
                endpoint=path, limit_type="global"
            )
            self._log_violation(path, "rate_limit_global", scope)
            return

        # --- Per-Session Rate Limit Check ---
        identity = self._get_identity(scope)
        session_key = f"ratelimit:session:{identity}"
        session_count = self._increment(session_key)

        if session_count > self.session_limit:
            retry_after = self._seconds_until_next_window()
            response = self._rate_limit_response(
                "Per-session rate limit exceeded", retry_after
            )
            await response(scope, receive, send)
            logger.warning(
                "Session rate limit exceeded",
                identity=identity,
                count=session_count,
            )
            self.monitoring.record_rate_limit_rejection(
                endpoint=path, limit_type="session"
            )
            self._log_violation(path, "rate_limit_session", scope)
            return

        # 制限内 → 次のミドルウェア/エンドポイントへ
        await self.app(scope, receive, send)

    def _increment(self, key: str) -> int:
        """インメモリカウンターをアトミックにインクリメント"""
        current_window = self._current_window()
        with self._lock:
            stored = self._counters.get(key)
            if stored is None or stored[1] != current_window:
                # 新しいウィンドウ → カウンターリセット
                self._counters[key] = (1, current_window)
                self._cleanup_old_windows(current_window)
                return 1
            else:
                new_count = stored[0] + 1
                self._counters[key] = (new_count, current_window)
                return new_count

    def _cleanup_old_windows(self, current_window: int) -> None:
        """古いウィンドウのカウンターを削除（メモリリーク防止）"""
        stale_keys = [
            k for k, (_, w) in self._counters.items() if w < current_window
        ]
        for k in stale_keys:
            del self._counters[k]

    def _get_identity(self, scope: Scope) -> str:
        """ユーザー識別子を取得: user_id > IP"""
        state = scope.get("state", {})
        user_id = state.get("user_id")
        if user_id and user_id != "anonymous":
            return f"user:{user_id}"

        # IPアドレスフォールバック
        client = scope.get("client")
        if client:
            return f"ip:{client[0]}"
        return "ip:unknown"

    def _current_window(self) -> int:
        """現在の1分間ウィンドウ（UNIXタイムスタンプを60で割った値）"""
        return int(time.time()) // self.window_seconds

    def _seconds_until_next_window(self) -> int:
        """次のウィンドウまでの残り秒数"""
        return self.window_seconds - (int(time.time()) % self.window_seconds)

    def _log_violation(self, path: str, error_type: str, scope: Scope) -> None:
        """レートリミット違反を llm_interaction_logs に記録（LLM関連エンドポイントのみ）"""
        if not path.startswith("/qa/"):
            return
        try:
            state = scope.get("state", {})
            log_entry = LLMLogEntry()
            log_entry.user_id = state.get("user_id", "anonymous")
            log_entry.user_query = "[RATE_LIMIT]"
            log_entry.endpoint = path
            log_entry.success = False
            log_entry.error_type = error_type
            log_entry.error_message = f"{error_type} exceeded for {self._get_identity(scope)}"
            get_llm_logger().log(log_entry)
        except Exception as e:
            logger.warning(f"Failed to log rate limit violation: {e}")

    def _rate_limit_response(self, message: str, retry_after: int) -> JSONResponse:
        """429 Too Many Requests レスポンスを生成"""
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "detail": message,
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
