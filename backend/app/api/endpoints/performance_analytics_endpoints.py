from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
import logging

# サービス層とスキーマをインポート
from backend.app.services.stats_service import ( # For Development, add backend. path
    get_batter_monthly_offensive_stats, get_batter_performance_at_risp,
    get_season_batting_stats, get_monthly_batting_stats,
    get_season_pitching_stats
)
from backend.app.api.schemas import (
    PlayerMonthlyOffensiveStats,
    PlayerBatterPerformanceAtRISPMonthly,
    PlayerBattingSeasonStats,
    PlayerMonthlyBattingStats,
    PlayerPitchingSeasonStats
)

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
router = APIRouter(tags=["performance-analytics"])


@router.get(
    "/players/{player_id}/season-batting-stats",
    response_model=List[PlayerBattingSeasonStats],
    summary="選手のシーズン打撃成績を取得",
    description="指定された選手IDに基づいて、シーズンの打撃成績を取得します。",
    tags=["players"]
)
async def get_season_batting_stats_endpoint(
    player_id: int = Path(..., description="取得したい選手のID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年)"),
    metrics: Optional[List[str]] = Query(None, description="取得するメトリックのリスト")
):
    """
    指定された選手のシーズン打撃成績を取得します。
    """

    # Convert the metrics list to a tuple (hashable object) for the service layer
    metrics_tuple = tuple(metrics) if metrics else ()

    # Get data from the service layer
    stats_data = get_season_batting_stats(player_id, season, metrics_tuple)

    # If no data is found, raise a 404 error
    if stats_data is None:
        raise HTTPException(status_code=404, detail="Batting stats data not found for the specified parameters.")

    # Return the list of stats items
    return stats_data



@router.get(
    "/players/{player_id}/monthly-batting-stats",
    response_model=List[PlayerMonthlyBattingStats],
    summary="選手の月別打撃成績を取得",
    description="指定された選手IDに基づいて、月別の打撃成績を取得します。",
    tags=["players"]
)
async def get_monthly_batting_stats_endpoint(
    player_id: int = Path(..., description="取得したい選手のID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象"),
    month: Optional[int] = Query(None, description="取得する月を指定。省略時は全月を対象"),
    metric: Optional[str] = Query(None, description="取得するメトリックを指定。省略時は全メトリックを対象")
):
    """
    指定された選手の月別打撃成績を取得します。
    シーズンを指定しない場合は、全シーズンの成績を返します。
    成績が見つからない場合は404エラーを返します。
    """
    # Get data from the service layer
    monthly_stats = get_monthly_batting_stats(player_id, season, month, metric)

    # If no data is found, raise a 404 error
    if monthly_stats is None:
        raise HTTPException(status_code=404, detail=f"Monthly batting stats not found for player {player_id}.")
    
    # Return the list of monthly stats
    return monthly_stats


# Router for monthly offensive stats
@router.get(
    "/players/{player_id}/monthly-offensive-stats",
    response_model=List[PlayerMonthlyOffensiveStats],
    summary="選手の月別打撃成績を取得",
    description="指定された選手IDに基づいて、月別の打撃成績を取得します。オプションでシーズンを指定できます。",
    tags=["players"]
)
async def get_monthly_offensive_stats_endpoint(
    player_id: int = Path(..., description="取得したい選手のID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象"),
    month: Optional[int] = Query(None, description="取得する月を指定。省略時は全月を対象"),
    metric: Optional[str] = Query(None, description="取得するメトリックを指定。省略時は全メトリックを対象")
):
    """
    指定された選手の月別打撃成績を取得します。
    シーズンを指定しない場合は、全シーズンの成績を返します。
    成績が見つからない場合は404エラーを返します。
    """
    # Get data from the service layer
    monthly_stats = get_batter_monthly_offensive_stats(player_id, season, month, metric)

    # If no data is found, raise a 404 error
    if monthly_stats is None:
        raise HTTPException(status_code=404, detail=f"Monthly offensive stats not found for player {player_id}.")
    
    # Return the list of monthly stats
    return monthly_stats


@router.get(
    "/players/{player_id}/season-pitching-stats",
    response_model=List[PlayerPitchingSeasonStats],
    summary="選手のシーズン投球成績を取得",
    description="指定された選手IDに基づいて、シーズンの投球成績を取得します。",
    tags=["players"]
)
async def get_season_pitching_stats_endpoint(
    player_id: int = Path(..., description="取得したい選手のID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年)"),
    metrics: Optional[List[str]] = Query(None, description="取得するメトリックのリスト")
):
    """
    指定された選手のシーズン投球成績を取得します。
    """

    # Convert the metrics list to a tuple (hashable object) for the service layer
    metrics_tuple = tuple(metrics) if metrics else ()

    # Get data from the service layer
    stats_data = get_season_pitching_stats(player_id, season, metrics_tuple)

    # If no data is found, raise a 404 error
    if stats_data is None:
        raise HTTPException(status_code=404, detail="Pitching stats data not found for the specified parameters.")

    # Return the list of stats items
    return stats_data



# @router.get(
#     "/players/{player_id}/performance-by-strike-count",
#     response_model=List[PlayerBatterPerformanceByStrikeCount],
#     summary="選手の打撃成績をストライクカウント別に取得",
#     description="指定された選手IDに基づいて、ストライクカウント別の打撃成績を取得します。",
#     tags=["players"]
# )
# async def get_batter_performance_by_strike_count_endpoint(
#     player_id: int = Path(..., description="取得したい選手のID"),
#     season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象"
# )):
#     """
#     指定された選手のストライクカウント別打撃成績を取得します。
#     シーズンを指定しない場合は、全シーズンの成績を返します。
#     成績が見つからない場合は404エラーを返します。
#     """
#     # Get data from the service layer
#     performance_data = get_batter_performance_by_strike_count(player_id, season)

#     # If no data is found, raise a 404 error
#     if performance_data is None:
#         raise HTTPException(status_code=404, detail=f"Performance by strike count not found for player with ID {player_id}.")

#     # Return the list of performance data
#     return performance_data


@router.get(
    "/players/{player_id}/performance-at-risp",
    response_model=List[PlayerBatterPerformanceAtRISPMonthly],
    summary="選手の得点圏打撃成績を取得",
    description="指定された選手IDに基づいて、得点圏での打撃成績を取得します。",
    tags=["players"]
)
async def get_batter_performance_at_risp_endpoint(
    player_id: int = Path(..., description="取得したい選手のID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象"),
    metric: Optional[str] = Query(None, description="取得するメトリックを指定。省略時は全メトリックを対象")
):
    """
    指定された選手の得点圏打撃成績を取得します。
    シーズンを指定しない場合は、全シーズンの成績を返します。
    成績が見つからない場合は404エラーを返します。
    """
    # Get data from the service layer
    performance_data = get_batter_performance_at_risp(player_id, season, metric)

    # If no data is found, raise a 404 error
    if performance_data is None:
        raise HTTPException(status_code=404, detail=f"Performance at RISP not found for player with ID {player_id}.")

    # Return the list of performance data
    return performance_data


# @router.get(
#     "/players/{player_id}/performance-by-inning",
#     response_model=List[PlayerPitcherPerformanceByInning],
#     summary="選手の投球成績をイニング別に取得",
#     description="指定された選手IDに基づいて、イニング別の投球成績を取得します。",
#     tags=["players"]
# )
# async def get_pitcher_performance_by_inning_endpoint(
#     player_id: int = Path(..., description="取得したい選手のID"),
#     season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象")
# ):
#     """
#     指定された選手のイニング別投球成績を取得します。
#     シーズンを指定しない場合は、全シーズンの成績を返します。
#     成績が見つからない場合は404エラーを返します。
#     """
#     # Get data from the service layer
#     performance_data = get_pitcher_performance_by_inning(player_id, season)

#     # If no data is found, raise a 404 error
#     if performance_data is None:
#         raise HTTPException(status_code=404, detail=f"Performance by inning not found for player with ID {player_id}.")

#     # Return the list of performance data
#     return performance_data


# @router.get(
#     "/players/{batter_id}/batting-stats-by-inning",
#     response_model=List[PlayerBattingStatsByInning],
#     summary="選手の打撃成績をイニング別に取得",
#     description="指定された選手IDに基づいて、イニング別の打撃成績を取得します。",
#     tags=["players"]
# )
# async def get_batting_stats_by_inning_endpoint(
#     batter_id: int = Path(..., description="取得したい選手のID"),
#     season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象")
# ):
#     """
#     指定された選手のイニング別打撃成績を取得します。
#     シーズンを指定しない場合は、全シーズンの成績を返します。
#     成績が見つからない場合は404エラーを返します。
#     """
#     # Get data from the service layer
#     performance_data = get_batting_stats_by_inning(batter_id, season)

#     # If no data is found, raise a 404 error
#     if performance_data is None:
#         raise HTTPException(status_code=404, detail=f"Performance by inning not found for batter with ID {batter_id}.")

#     # Return the list of performance data
#     return performance_data