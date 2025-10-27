from fastapi import APIRouter
from .player_endpoints import router as player_router
from .leaderboard_endpoints import router as leaderboard_router
from .statcast_endpoints import router as statcast_router
from .performance_analytics_endpoints import router as performance_router
from .ai_analytics_endpoints import router as ai_router
from .statistics_endpoints import router as statistics_router
from .segmentation_endpoints import router as segmentation_router
from .pitcher_fatigue_endpoints import router as pitcher_fatigue_router
from .pitcher_substition_ml_endpoints import router as pitcher_substitution_ml_router

# メインのAPIルーターを作成
api_router = APIRouter()

# 各エンドポイントのルーターを統合
api_router.include_router(player_router)
api_router.include_router(leaderboard_router)
api_router.include_router(statcast_router)
api_router.include_router(performance_router)
api_router.include_router(ai_router)
api_router.include_router(statistics_router)
api_router.include_router(segmentation_router)
api_router.include_router(pitcher_fatigue_router)
api_router.include_router(pitcher_substitution_ml_router)