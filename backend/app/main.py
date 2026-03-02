from fastapi import FastAPI, Request
from backend.app.api.endpoints.router import api_router  # For Development, add backend. path
# from backend.app.api.endpoints import ai_analytics_endpoints  # For Development, add backend. path
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from backend.app.utils.structured_logger import get_logger
from backend.app.services.monitoring_service import get_monitoring_service
from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.middleware.firebase_auth import FirebaseAuthMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from backend.app.api.rate_limit import limiter
from backend.app.middleware.rate_limit import RateLimitMiddleware


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

# Add rate limiting to the FastAPI app
app.state.limiter = limiter


async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Per-Endpoint レートリミット超過時の429レスポンス（slowapi用）"""
    structured_logger.warning(
        "Endpoint rate limit exceeded",
        path=request.url.path,
        detail=str(exc.detail),
    )
    monitoring.record_rate_limit_rejection(
        endpoint=request.url.path, limit_type="endpoint"
    )

    # llm_interaction_logs に記録
    from backend.app.services.llm_logger_service import get_llm_logger, LLMLogEntry
    log_entry = LLMLogEntry()
    log_entry.user_id = getattr(request.state, "user_id", "anonymous")
    log_entry.user_query = "[RATE_LIMIT]"
    log_entry.endpoint = request.url.path
    log_entry.success = False
    log_entry.error_type = "rate_limit_endpoint"
    log_entry.error_message = str(exc.detail)
    get_llm_logger().log(log_entry)

    return JSONResponse(
        status_code=429,
        content={
            "error": "Too Many Requests",
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": 60,
        },
        headers={"Retry-After": "60"},
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # <-- これが True であることを確認
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # DO NOT add " *" to allow_methods
    allow_headers=["Content-Type", "Authorization"],  # DO NOT add " *" to allow_headers
    expose_headers=['X-Request-ID'] # Frontend can read this header
)

# 重要: add_middleware は「後に登録したものが先に実行される」ので、
# RateLimitMiddleware は FirebaseAuth の後（= Auth完了後）に実行されます。これにより user_id が使えます。

# Firebase認証ミドルウェア
app.add_middleware(FirebaseAuthMiddleware)

app.add_middleware(RateLimitMiddleware)

# RequestIDMiddleware: 最後に登録 = 最も外側で実行される
app.add_middleware(RequestIDMiddleware)


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
