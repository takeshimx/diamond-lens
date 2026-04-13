from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from backend.app.services.hot_slump_service import get_hot_slump_batters, get_available_dates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["hot-slump"])


@router.get(
    "/hot-slump/batters",
    summary="ホット/スランプ打者ランキングを取得",
    description="指定された指標・期間・日付に基づき、直近スタッツがシーズン平均比±20%を超えた打者Top Nを返す。",
    tags=["hot-slump"],
)
async def get_hot_slump_batters_endpoint(
    metric: str = Query("ops", description="指標 (ba / ops / barrels / hard_hit)"),
    period: int = Query(7, description="集計期間 (7 または 15)"),
    game_date: Optional[str] = Query(None, description="基準日 YYYY-MM-DD。省略時は最新日"),
    top_n: int = Query(10, ge=1, le=30, description="取得件数"),
):
    data = get_hot_slump_batters(metric=metric, period=period, game_date=game_date, top_n=top_n)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch hot/slump data.")
    return data


@router.get(
    "/hot-slump/available-dates",
    summary="利用可能な日付リストを取得",
    tags=["hot-slump"],
)
async def get_available_dates_endpoint(
    period: int = Query(7, description="集計期間 (7 または 15)"),
):
    dates = get_available_dates(period=period)
    if dates is None:
        raise HTTPException(status_code=500, detail="Failed to fetch available dates.")
    return {"dates": dates}
