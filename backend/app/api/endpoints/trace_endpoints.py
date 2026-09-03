"""
Trace Viewer API Endpoints (P0-1)

エージェントの実行経路(trace)を閲覧し、失敗ラベルを付与するための API。

- GET  /traces                  trace 一覧
- GET  /traces/labels           ラベル軸の定義（フロントのハードコード回避）
- GET  /traces/compare          2 trace の比較
- GET  /traces/{trace_id}       1 trace の全ステップ
- POST /traces/{trace_id}/label ラベル付与
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.services.trace_label_service import VALID_LABELS, put_label
from backend.app.services.trace_query_service import (
    compare_traces,
    get_trace,
    list_traces,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traces", tags=["Trace Viewer"])

# usage_endpoints と同じ 60 秒 TTL キャッシュ。一覧の連打を BQ に流さない。
_CACHE_TTL_SEC = 60.0
_cache: Dict[Tuple, Tuple[float, Any]] = {}
_cache_lock = threading.Lock()


class LabelRequest(BaseModel):
    label: str = Field(..., description=f"ラベル軸。{VALID_LABELS} のいずれか")
    note: Optional[str] = Field(None, description="判断理由の自由記述", max_length=1000)
    labeled_by: Optional[str] = Field(None, description="付与者。省略時は unknown")


@router.get("/labels", summary="ラベル軸の定義を返す")
def get_label_definitions() -> Dict[str, Any]:
    """フロント側でラベル一覧をハードコードさせないための定義エンドポイント。"""
    return {"success": True, "labels": VALID_LABELS}


@router.get("", summary="trace 一覧")
def list_traces_endpoint(
    days: int = Query(30, ge=1, le=365, description="遡る日数"),
    limit: int = Query(100, ge=1, le=500, description="返す trace 数の上限"),
    only_unlabeled: bool = Query(False, description="ラベル未付与のみ"),
    only_failed: bool = Query(False, description="失敗ステップを含むもののみ"),
    force: bool = Query(False, description="True なら 60s キャッシュを無視"),
) -> Dict[str, Any]:
    cache_key = (days, limit, only_unlabeled, only_failed)
    if not force:
        with _cache_lock:
            hit = _cache.get(cache_key)
            if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
                return {"success": True, "traces": hit[1], "cached": True}
    try:
        traces = list_traces(
            days=days,
            limit=limit,
            only_unlabeled=only_unlabeled,
            only_failed=only_failed,
        )
    except Exception as e:
        logger.error(f"list_traces failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    with _cache_lock:
        _cache[cache_key] = (time.time(), traces)
    return {"success": True, "traces": traces, "cached": False}


@router.get("/compare", summary="2 trace の比較")
def compare_traces_endpoint(
    a: str = Query(..., description="比較元の trace_id"),
    b: str = Query(..., description="比較先の trace_id"),
) -> Dict[str, Any]:
    try:
        return {"success": True, "data": compare_traces(a, b)}
    except Exception as e:
        logger.error(f"compare_traces failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}", summary="1 trace の全ステップ")
def get_trace_endpoint(trace_id: str) -> Dict[str, Any]:
    try:
        data = get_trace(trace_id)
    except Exception as e:
        logger.error(f"get_trace failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    if not data["steps"] and not data.get("summary"):
        raise HTTPException(status_code=404, detail=f"trace not found: {trace_id}")
    return {"success": True, "data": data}


@router.post("/{trace_id}/label", summary="trace にラベルを付与")
def put_label_endpoint(trace_id: str, body: LabelRequest) -> Dict[str, Any]:
    try:
        row = put_label(
            trace_id=trace_id,
            label=body.label,
            note=body.note,
            labeled_by=body.labeled_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"put_label failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # ラベルが付くと一覧の見え方が変わるためキャッシュを捨てる
    with _cache_lock:
        _cache.clear()
    return {"success": True, "data": row}
