from fastapi import APIRouter
from .player_endpoints import router as player_router
from .leaderboard_endpoints import router as leaderboard_router
# from .statcast_endpoints import router as statcast_router
# from .zone_endpoints import router as zone_router
from .performance_analytics_endpoints import router as performance_router
# from .ranking_endpoints import router as ranking_router
from .ai_analytics_endpoints import router as ai_router
# from .utility_endpoints import router as utility_router

# メインのAPIルーターを作成
api_router = APIRouter()

# 各エンドポイントのルーターを統合
api_router.include_router(player_router)
api_router.include_router(leaderboard_router)
# api_router.include_router(statcast_router)
# api_router.include_router(zone_router)
api_router.include_router(performance_router)
# api_router.include_router(ranking_router)
api_router.include_router(ai_router)
# api_router.include_router(utility_router)