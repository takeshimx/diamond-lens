from fastapi import FastAPI
from backend.app.api.endpoints import players  # Import the players router
# from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI app instance
app = FastAPI(
    title="MLB Analytics API",
    description="API for MLB Analytics Dashboard V2",
    version="0.1.0"
)

# # StreamlitアプリのURLを許可するオリジンとして追加
# # Cloud RunのStreamlitサービスのURLを正確に指定
# origins = [
#     "https://mlb-analytics-dashboard-aug2025-907924272679.asia-northeast1.run.app", # StreamlitダッシュボードのURL
#     # 開発環境でローカルからアクセスする場合など、必要に応じて追加
#     # "http://localhost:8501", # ローカルStreamlit
#     # "http://localhost:8080", # ローカルStreamlit (Cloud Runポート)
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True, # <-- これが True であることを確認
#     allow_methods=["*"],    # 全てのHTTPメソッドを許可
#     allow_headers=["*"],    # 全てのヘッダーを許可 (Authorizationヘッダーも含む)
# )


# Include the players router into FastAPI app
app.include_router(players.router, prefix="/api/v1", tags=["Players"])

# # ★★★ テスト用ルートを追加 ★★★
# @app.get("/api/v1/test", tags=["Test"])
# async def test_endpoint():
#     return {"message": "Test endpoint reached successfully!"}

@app.get("/", summary="API router", description="API router endpoint")
async def read_root():
    return {"message": "Welcome to MLB Analytics Dashboard API. Access /api/v1/docs for API documentation."}


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "version": "0.1.1"}