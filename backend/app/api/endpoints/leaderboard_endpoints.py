from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
import logging

# サービス層とスキーマをインポート
from backend.app.services.leaderboard_service import *
# from backend.app.services.stats_service import get_batter_performance_flags
from backend.app.api.schemas import (
    PlayerBattingSeasonStats,
    PlayerBattingSplitStats,
    PlayerPitchingSeasonStats,
    PlayerBatterPerformanceFlags
)

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
router = APIRouter(tags=["leaderboards"])

@router.get(
    "/leaderboards/batting",
    response_model=List[PlayerBattingSeasonStats],
    summary="打撃リーダーボードを取得",
    description="指定されたシーズン、リーグ、最小打席数で打撃リーダーボードデータを取得します。",
    tags=["leaderboards"]
)
async def get_batting_leaderboard_endpoint(
    season: int = Query(..., description="取得するシーズン (年)"),
    league: str = Query("MLB", description="リーグ (MLB, AL, NL)", regex="^(MLB|AL|NL)$"),
    min_pa: int = Query(..., ge=1, description="最小打席数"),
    metric_order: str = Query("ops", description="Metric for ordering the leaderboard (e.g., 'ops', 'avg', 'hr', etc.)")
):
    """
    指定されたシーズン、リーグ、最小打席数で打撃リーダーボードを取得します。
    データが見つからない場合は404エラーを返します。
    """
    
    # Get data from the service layer
    leaderboard_data = get_batting_leaderboard(season, league, min_pa, metric_order)

    # If no data is found, raise a 404 error
    if leaderboard_data is None:
        raise HTTPException(status_code=404, detail="Batting leaderboard data not found for the specified parameters.")

    # Return the list of leaderboard items
    return leaderboard_data


# @router.get(
#     "/leaderboards/batting-splits",
#     response_model=List[PlayerBattingSplitStats],
#     summary="バッターのスプリット統計リーダーボードを取得",
#     description="指定されたシーズン、リーグ、最小打席数でバッターのスプリット統計リーダーボードを取得します。",
#     tags=["leaderboards"]
# )
# async def get_batter_split_stats_leaderboard_endpoint(
#     season: int = Query(..., description="取得するシーズン (年)"),
#     league: str = Query("MLB", description="リーグ (MLB, AL, NL)", regex="^(MLB|AL|NL)$"),
#     min_pa: int = Query(..., ge=1, description="最小打席数"),
#     split_type: str = Query("RISP", description="スプリットの種類 (例: 'RISP', 'Bases Loaded', 'Runner on 1B', etc.)")
#     # metric_order: str = Query("avg", description="Metric for ordering the leaderboard (e.g., 'avg_at_risp', 'grandslam', 'homeruns_at_runner_on_1b', etc.)")
# ):
#     """
#     指定されたシーズン、リーグ、最小打席数でバッターのスプリット統計リーダーボードを取得します。
#     データが見つからない場合は404エラーを返します。
#     """

#     # ★★★ デバッグログの追加 ★★★
#     logger.debug(f"Reached get_batter_split_stats_leaderboard_endpoint. Params: season={season}, league={league}, min_pa={min_pa}, split_type={split_type}")
#     # ★★★ ここまで ★★★

#     # Get data from the service layer
#     leaderboard_data = get_batter_split_stats_leaderboard(season, league, min_pa, split_type)

#     # If no data is found, raise a 404 error
#     if leaderboard_data is None:
#         raise HTTPException(status_code=404, detail="Batter split stats leaderboard data not found for the specified parameters.")
    
#     # Return the list of leaderboard items
#     return leaderboard_data


@router.get(
    "/leaderboards/pitching",
    response_model=List[PlayerPitchingSeasonStats],
    summary="投球リーダーボードを取得",
    description="指定されたシーズン、リーグ、最小投球回で投球リーダーボードのトップ20選手を取得します。",
    tags=["leaderboards"]
)
async def get_pitching_leaderboard_endpoint(
    season: int = Query(..., description="取得したいシーズン年"),
    league: str = Query("MLB", description="リーグ (MLB, AL, NL)", regex="^(MLB|AL|NL)$"),
    min_ip: int = Query(..., ge=1, description="最小投球回"),
    metric_order: str = Query("era", description="")
):
    """
    指定されたシーズン、リーグ、最小投球回で投球リーダーボードのトップ20選手を取得します。
    データが見つからない場合は404エラーを返します。
    """
    # Get data from the service layer
    leaderboard_data = get_pitching_leaderboard(season, league, min_ip, metric_order)

    # If no data is found, raise a 404 error
    if leaderboard_data is None:
        raise HTTPException(status_code=404, detail="Pitching leaderboard data not found for the specified parameters.")

    # Return the list of leaderboard items
    return leaderboard_data


# @router.get(
#     "/leaderboards/team-batting",
#     response_model=List[TeamBattingStatsLeaderboard],
#     summary="チーム打撃リーダーボードを取得",
#     description="指定されたシーズン、リーグ、チーム打撃リーダーボードを取得します。",
#     tags=["leaderboards"]
# )
# async def get_team_batting_stats_leaderboard_endpoint(
#     season: int = Query(..., description="取得するシーズン (年)"),
#     league: Optional[str] = Query("MLB", description="リーグ (MLB, AL, NL)", regex="^(MLB|AL|NL)$"),
#     metric_order: str = Query("ops", description="Metric for ordering the leaderboard (e.g., 'ops', 'avg', 'hr', etc.)")
# ):
#     """
#     指定されたシーズン、リーグ、チーム打撃リーダーボードを取得します。
#     データが見つからない場合は404エラーを返します。
#     """

#     # # ★★★ デバッグログの追加 ★★★
#     # logger.debug(f"Reached get_team_batting_leaderboard_endpoint. Params: season={season}, league={league}, metric_order={metric_order}")
#     # # ★★★ ここまで ★★★

#     # Get data from the service layer
#     batting_leaderboard_data = get_team_batting_stats_leaderboard(season, league, metric_order)

#     # If no data is found, raise a 404 error
#     if batting_leaderboard_data is None:
#         raise HTTPException(status_code=404, detail="Team batting leaderboard data not found for the specified parameters.")
    
#     # Return the list of leaderboard items
#     return batting_leaderboard_data


# @router.get(
#     "/leaderboards/team-pitching",
#     response_model=List[TeamPitchingStatsLeaderboard],
#     summary="チーム投球リーダーボードを取得",
#     description="指定されたシーズン、リーグ、チーム投球リーダーボードを取得します。",
#     tags=["leaderboards"]
# )
# async def get_team_pitching_stats_leaderboard_endpoint(
#     season: int = Query(..., description="取得するシーズン (年)"),
#     league: Optional[str] = Query("MLB", description="リーグ (MLB, AL, NL)", regex="^(MLB|AL|NL)$"),
#     metric_order: str = Query("era", description="Metric for ordering the leaderboard (e.g., 'era', 'whip', 'k/9', etc.)")
# ):
#     """
#     指定されたシーズン、リーグ、チーム投球リーダーボードを取得します。
#     データが見つからない場合は404エラーを返します。
#     """

#     # Get data from the service layer
#     pitching_leaderboard_data = get_team_pitching_stats_leaderboard(season, league, metric_order)

#     # If no data is found, raise a 404 error
#     if pitching_leaderboard_data is None:
#         raise HTTPException(status_code=404, detail="Team pitching leaderboard data not found for the specified parameters.")
    
#     # Return the list of leaderboard items
#     return pitching_leaderboard_data


# # Router for batter performance flags
# @router.get(
#     "/leaderboards/batter-performance-flags",
#     response_model=List[PlayerBatterPerformanceFlags],
#     summary="選手の打撃パフォーマンスフラグを取得",
#     description="指定された選手IDに基づいて、打撃パフォーマンスフラグを取得します。",
#     tags=["leaderboards"]
# )
# async def get_batter_performance_flags_endpoint(
#     query_date: Optional[str] = Query(None, description="取得するフラグの基準日 (YYYY-MM-DD形式)"),
#     days: int = Query(7, description="フラグを取得する日数の範囲。デフォルトは7日間")
#     # season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象")
# ):
#     """
#     指定された選手の打撃パフォーマンスフラグを取得します。
#     シーズンを指定しない場合は、全シーズンのフラグを返します。
#     フラグが見つからない場合は404エラーを返します。
#     """
#     # Get data from the service layer
#     batter_performance_flags = get_batter_performance_flags(query_date=query_date, days=days)

#     # # Debug log to check if the function was reached
#     # logger.debug(f"Reached get_batter_performance_flags_endpoint. Data: {batter_performance_flags}")

#     # If no data is found, raise a 404 error
#     if batter_performance_flags is None:
#         raise HTTPException(status_code=404, detail=f"Performance flags not found.")

#     # Return the list of performance flags
#     return batter_performance_flags

