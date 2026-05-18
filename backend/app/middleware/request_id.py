import uuid
from backend.app.middleware.request_context import (
    get_request_id,  # noqa: F401  re-exported for backward compat
    set_endpoint,
    set_request_id,
    set_trace_id,
)
from backend.app.utils.snowflake import generate_id_str


class RequestIDMiddleware:
    """Pure ASGI middleware for request ID & trace ID tracking.

    BaseHTTPMiddleware だと call_next が別コンテキストで実行され、
    ContextVar の値がエンドポイント側に伝わらないため、
    純粋な ASGI ミドルウェアとして実装しています。

    本ミドルウェアは 2 種類の識別子を扱います:
      - X-Request-ID: 既存（uuid4）。dual-write 期間中は維持
      - X-Trace-Id : 新規（Snowflake）。クライアント・SSE・BQ ログ横断
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        # X-Request-ID: 既存どおり uuid4 を維持（旧ログ互換のため）
        request_id = (
            headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        )

        # X-Trace-Id: ヘッダ優先、なければ Snowflake を新規発行
        trace_id = (
            headers.get(b"x-trace-id", b"").decode() or generate_id_str()
        )

        # ContextVar にセット → 同一リクエスト内のどこからでも取得可能
        set_request_id(request_id)
        set_trace_id(trace_id)
        set_endpoint(scope.get("path", ""))

        # レスポンスヘッダに両方付与
        async def send_with_ids(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode()))
                response_headers.append((b"x-trace-id", trace_id.encode()))
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, receive, send_with_ids)
