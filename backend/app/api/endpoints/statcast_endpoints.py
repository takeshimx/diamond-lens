from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
import logging

# サービス層とスキーマをインポート
from backend.app.services.statcast_service import get_batter_splits_stats_advanced
from backend.app.api.schemas import (
    PlayerStatcastData
)

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
router = APIRouter(tags=["statcast"])

# # Router for player Statcast data for pitcher
# @router.get(
#     "/players/{pitcher_id:int}/statcast/pitcher",
#     response_model=List[PlayerStatcastData],
#     summary="PitcherのStatcastデータを取得",
#     description="指定された選手IDに基づいて、PitcherのStatcastデータを取得します。",
#     tags=["players"]
# )
# async def get_pitcher_statcast_data_endpoint(
#     pitcher_id: int = Path(..., description="取得したい選手のMLB ID"),
#     season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象")
# ):
#     """
#     指定された選手のStatcastデータを取得します。
#     シーズンを指定しない場合は、全シーズンのデータを返します。
#     データが見つからない場合は404エラーを返します。
#     """
#     # Get data from the service layer
#     statcast_data = get_pitcher_statcast_data(pitcher_id, season)

#     # If no data is found, raise a 404 error
#     if statcast_data is None:
#         raise HTTPException(status_code=404, detail=f"Statcast data not found for pitcher with ID {pitcher_id}.")

#     # Return the list of Statcast data
#     return statcast_data

# Router for player Statcast data for batter
@router.get(
    "/players/{batter_id:int}/statcast/batter/advanced-stats",
    response_model=List[PlayerStatcastData],
    summary="BatterのStatcastデータを取得",
    description="指定された選手IDに基づいて、BatterのStatcastデータを取得します。",
    tags=["players"]
)
async def get_batter_statcast_data_endpoint(
    batter_id: int = Path(..., description="取得したい選手のMLB ID"),
    season: Optional[int] = Query(None, description="取得するシーズン (年) を指定。省略時は全シーズンを対象"),
    innings: Optional[List[int]] = Query(None, description="取得するイニングを指定。省略時は全イニングを対象"),
    strikes: Optional[int] = Query(None, description="取得するストライク数を指定。省略時は全ストライク数を対象"),
    balls: Optional[int] = Query(None, description="取得するボール数を指定。省略時は全ボール数を対象"),
    p_throws: Optional[str] = Query(None, description="取得する投手の投球スタイルを指定。省略時は全投球スタイルを対象"),
    runners: Optional[List[str]] = Query(None, description="取得するランナーの情報を指定。省略時は全ランナーを対象"),
    pitch_types: Optional[List[str]] = Query(None, description="取得する投球の種類を指定。省略時は全投球の種類を対象")
):
    """
    指定された選手のStatcastデータを取得します。
    シーズンを指定しない場合は、全シーズンのデータを返します。
    データが見つからない場合は404エラーを返します。
    """

    # # ★★★ 強制デバッグエラーの追加（関数の冒頭） ★★★
    # # This line is for temporary debugging. Remove it after the issue is resolved.
    # raise Exception(f"DEBUG: Reached get_batter_statcast_data_endpoint. Params: batter_id={batter_id}, season={season}")
    # # ★★★ ここまで ★★★

    # # ★★★ デバッグログの追加 ★★★
    # logger.debug(f"Reached get_batter_statcast_data_endpoint. Params: batter_id={batter_id}, season={season}")
    # # ★★★ ここまで ★★★

    # Get data from the service layer
    statcast_data = get_batter_splits_stats_advanced(batter_id, season, innings, strikes, balls, p_throws, runners, pitch_types)

    # If no data is found, raise a 404 error
    if statcast_data is None:
        logger.debug(f"Statcast data is None from player_service for batter ID {batter_id}.")
        raise HTTPException(status_code=404, detail=f"Statcast data not found for batter with ID {batter_id}.")

    # Return the list of Statcast data
    return statcast_data