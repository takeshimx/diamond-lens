import uuid
from backend.app.middleware.request_context import set_request_id, get_request_id


class RequestIDMiddleware:
    """Pure ASGI middleware for request ID tracking.

    BaseHTTPMiddleware だと call_next が別コンテキストで実行され、
    ContextVar の値がエンドポイント側に伝わらないため、
    純粋な ASGI ミドルウェアとして実装しています。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # リクエストヘッダーから X-Request-ID を取得、なければ新規生成
        headers = dict(scope.get("headers", []))
        request_id = (
            headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        )

        # ContextVar にセット → 同一リクエスト内のどこからでも取得可能
        set_request_id(request_id)

        # レスポンスヘッダーに X-Request-ID を付与
        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)
