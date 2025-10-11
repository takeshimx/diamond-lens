from fastapi import FastAPI, Request
from backend.app.api.endpoints.router import api_router  # For Development, add backend. path
# from backend.app.api.endpoints import ai_analytics_endpoints  # For Development, add backend. path
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from backend.app.utils.structured_logger import get_logger
from backend.app.services.monitoring_service import get_monitoring_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger("diamond-lens")
monitoring = get_monitoring_service()

# Create the FastAPI app instance
app = FastAPI(
    title="MLB Analytics API",
    description="API for MLB Analytics Dashboard V2",
    version="0.1.0",
)

# Monitoring middleware for request tracking
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    start_time = time.time() # ← 前処理: 開始時刻記録

    # Log request start
    structured_logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown"
    )

    # Process request
    response = await call_next(request) # ← 実際のエンドポイント処理

    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000 # ← 後処理: レイテンシ計算

    # Log request completion
    structured_logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=round(latency_ms, 2)
    )

    # Record metrics
    monitoring.record_api_latency(
        endpoint=request.url.path,
        latency_ms=latency_ms,
        status_code=response.status_code
    )

    return response

# ReactアプリのURLを許可するオリジンとして追加
origins = [
    "https://mlb-diamond-lens-frontend-907924272679.asia-northeast1.run.app", # React app at Cloud run
    "http://localhost:5173",  # ローカルReact開発サーバー
    "http://localhost:5174",  # ローカルReact開発サーバー (alternative port)
    "http://localhost:3000",
]

# "*" # 全てのオリジンを許可 (開発中のみ使用、セキュリティ上の理由で本番環境では制限することを推奨

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # <-- これが True であることを確認
    allow_methods=["*"],  # 全てのHTTPメソッドを許可
    allow_headers=["*"],  # 全てのヘッダーを許可 (Authorizationヘッダーも含む)
)


# Include the players router into FastAPI app
app.include_router(api_router, prefix="/api/v1", tags=["Players"])


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
