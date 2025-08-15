from fastapi import FastAPI, Request
from backend.app.api.endpoints import players  # Import the players router
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastAPI app instance
app = FastAPI(
    title="MLB Analytics API",
    description="API for MLB Analytics Dashboard V2",
    version="0.1.0",
)

# # デバッグ用ミドルウェア（CORSミドルウェアの前に追加）
# @app.middleware("http")
# async def debug_middleware(request: Request, call_next):
#     logger.info(f"🔍 Request URL: {request.url}")
#     logger.info(f"🔍 Request method: {request.method}")
#     logger.info(f"🔍 Request headers: {dict(request.headers)}")

#     response = await call_next(request)

#     logger.info(f"🔍 Response status: {response.status_code}")
#     logger.info(f"🔍 Response headers: {dict(response.headers)}")

#     return response

# ReactアプリのURLを許可するオリジンとして追加
origins = [
    # "https://fantastic-garbanzo-77jg7grqjgwhx9q6-5173.app.github.dev",
    "http://localhost:5173",  # ローカルReact開発サーバー
    "http://localhost:3000",
]

# "https://mlb-analytics-dashboard-aug2025-907924272679.asia-northeast1.run.app", # StreamlitダッシュボードのURL
# 開発環境でローカルからアクセスする場合など、必要に応じて追加

# "http://localhost:3000", # ローカルReact開発サーバー (別のポート)
# "http://localhost:8080", # ローカルStreamlit (Cloud Runポート)
# "*" # 全てのオリジンを許可 (開発中のみ使用、セキュリティ上の理由で本番環境では制限することを推奨

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # <-- これが True であることを確認
    allow_methods=["*"],  # 全てのHTTPメソッドを許可
    allow_headers=["*"],  # 全てのヘッダーを許可 (Authorizationヘッダーも含む)
)


# Include the players router into FastAPI app
app.include_router(players.router, prefix="/api/v1", tags=["Players"])

# # ★★★ テスト用ルートを追加 ★★★
# @app.get("/api/v1/test", tags=["Test"])
# async def test_endpoint():
#     return {"message": "Test endpoint reached successfully!"}


@app.get("/", summary="API router", description="API router endpoint")
async def read_root():
    return {
        "message": "Welcome to MLB Analytics Dashboard API. Access /api/v1/docs for API documentation."
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "version": "0.1.1"}


@app.get("/debug/routes")
async def list_routes():
    """利用可能なルートを一覧表示"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append(
                {"path": route.path, "methods": list(route.methods), "name": route.name}
            )
    return routes


# 明示的なOPTIONSハンドラーを追加
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    logger.info(f"🔍 OPTIONS request for: {full_path}")
    return {"message": "OK"}
