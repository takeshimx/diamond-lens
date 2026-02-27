import json
from backend.app.services.firebase_service import verify_firebase_token
from backend.app.utils.structured_logger import get_logger

logger = get_logger("auth")

# 認証不要のパス
PUBLIC_PATHS = {"/", "/health", "/debug/routes", "/docs", "/openapi.json", "/redoc"}


class FirebaseAuthMiddleware:
    """Firebase IDトークンを検証するASGIミドルウェア"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 公開パスはスキップ
        if path in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        # OPTIONSリクエスト（CORSプリフライト）はスキップ
        method = scope.get("method", "")
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Authorizationヘッダーからトークンを取得
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if not auth_header.startswith("Bearer "):
            await self._send_401(send, "Missing or invalid Authorization header")
            return

        id_token = auth_header[7:]  # "Bearer " を除去

        try:
            decoded_token = verify_firebase_token(id_token)
            # user_id を scope に保存（エンドポイントから参照可能）
            scope["state"] = scope.get("state", {})
            scope["state"]["user_id"] = decoded_token["uid"]
            scope["state"]["user_email"] = decoded_token.get("email", "")
            logger.info("Auth success", user_id=decoded_token["uid"])
        except Exception as e:
            logger.warning("Auth failed", error=str(e))
            await self._send_401(send, "Invalid or expired token")
            return

        await self.app(scope, receive, send)

    async def _send_401(self, send, detail: str):
        body = json.dumps({"detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
