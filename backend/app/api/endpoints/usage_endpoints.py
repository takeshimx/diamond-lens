"""
LLM Usage Cost Dashboard API Endpoints
GET /usage/dashboard で月次サマリ・モデル別・feature別・日次トレンド・直近N件を返す。
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.usage_stats_service import get_dashboard_all

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["LLM Usage Dashboard"])

# 60 秒の TTL キャッシュ（同一パラメータの連打を BQ に投げ直さない）
_CACHE_TTL_SEC = 60.0
_cache: Dict[Tuple, Tuple[float, Dict[str, Any]]] = {}
_cache_lock = threading.Lock()


@router.get("/dashboard")
def get_usage_dashboard(
    year: Optional[int] = Query(None, ge=2024, le=2100, description="対象年 (省略時は当月)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="対象月 (省略時は当月)"),
    trend_days: int = Query(30, ge=1, le=365, description="日次トレンドの対象日数"),
    recent_limit: int = Query(20, ge=1, le=100, description="直近呼び出しの件数"),
    force: bool = Query(False, description="True なら 60s キャッシュを無視して再取得"),
):
    """LLM コストダッシュボードに必要な集計データを **1 本の BQ クエリ** で取得する。

    高速化策:
    - BQ クエリ 6 本 → 1 本 (round-trip コスト削減、テーブル scan も 1 回)
    - 60 秒インメモリ TTL キャッシュ (Refresh 連打を BQ に流さない)
    - force=true で明示的にキャッシュバイパス可
    """
    try:
        now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
        target_year = year or now_jst.year
        target_month = month or now_jst.month
        if target_month == 1:
            prev_year, prev_month = target_year - 1, 12
        else:
            prev_year, prev_month = target_year, target_month - 1

        cache_key = (target_year, target_month, trend_days, recent_limit)

        if not force:
            with _cache_lock:
                hit = _cache.get(cache_key)
                if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
                    return {"success": True, "data": hit[1], "cached": True}

        data = get_dashboard_all(
            target_year=target_year,
            target_month=target_month,
            prev_year=prev_year,
            prev_month=prev_month,
            trend_days=trend_days,
            recent_limit=recent_limit,
        )

        with _cache_lock:
            _cache[cache_key] = (time.time(), data)

        return {"success": True, "data": data, "cached": False}

    except Exception as e:
        logger.error(f"Usage dashboard query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
