import os
import json
from backend.app.services.firebase_service import verify_firebase_token
from backend.app.utils.structured_logger import get_logger
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = get_logger("auth")

# 開発環境での認証スキップ（環境変数で制御）
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"


# 認証不要のパス
PUBLIC_PATHS = {
    "/",
    "/health",
    "/debug/routes",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/test",  # テスト用エンドポイント
    "/api/v1/test-post",  # テスト用POSTエンドポイント
}

# Cloud Workflows など内部サービスから呼ばれるパス（OIDC トークンで検証）
INTERNAL_PATHS = {
    "/api/v1/model-registry/retrain",
    "/api/v1/internal/summary/trigger",
}


class FirebaseAuthMiddleware:
    """Firebase IDトークンを検証するASGIミドルウェア"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 開発環境での認証スキップ
        if DISABLE_AUTH:
            logger.warning("⚠️ Authentication disabled (DISABLE_AUTH=true)")
            scope["state"] = scope.get("state", {})
            scope["state"]["user_id"] = "dev_user"
            scope["state"]["user_email"] = "dev@localhost"
            await self.app(scope, receive, send)
            return

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

        token = auth_header[7:]  # "Bearer " を除去

        # 内部パス（Cloud Workflows など）は OIDC トークンで検証
        if path in INTERNAL_PATHS:
            try:
                audience = os.getenv("BACKEND_CLOUD_RUN_URL", "")
                decoded = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    audience=audience,
                )
                caller_email = decoded.get("email", "")
                workflows_sa_email = os.getenv("WORKFLOWS_SA_EMAIL", "")
                if workflows_sa_email and caller_email != workflows_sa_email:
                    logger.warning("OIDC SA mismatch", email=caller_email)
                    await self._send_401(send, "Unauthorized service account")
                    return
                scope["state"] = scope.get("state", {})
                scope["state"]["user_id"] = caller_email
                scope["state"]["user_email"] = caller_email
                logger.info("OIDC auth success", email=caller_email)
            except Exception as e:
                logger.warning("OIDC auth failed", error=str(e))
                await self._send_401(send, "Invalid or expired token")
                return
            await self.app(scope, receive, send)
            return

        try:
            decoded_token = verify_firebase_token(token)
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
