"""
Trace Viewer API Endpoints (P0-1)

エージェントの実行経路(trace)を閲覧し、失敗ラベルを付与するための API。

- GET  /traces                     trace 一覧
- GET  /traces/labels              ラベル軸の定義（フロントのハードコード回避）
- GET  /traces/expected-options    期待値入力欄の選択肢（同上）
- GET  /traces/compare             2 trace の比較
- GET  /traces/{trace_id}          1 trace の全ステップ
- POST /traces/{trace_id}/label    ラベル付与
- POST /traces/{trace_id}/expected 期待値付与（golden_dataset への昇格元）

注意: パス定義の順序。FastAPI は上から順にマッチするため、固定パス
(/labels, /expected-options, /compare) は必ず /{trace_id} より前に置く。
後ろに置くと trace_id="labels" として解釈される。
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.services.golden_pr_service import (
    GoldenPRError,
    create_golden_pr,
    is_configured,
)
from backend.app.services.trace_expectation_service import (
    put_expectation,
    valid_metrics,
    valid_query_types,
    valid_split_types,
)
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


class ExpectationRequest(BaseModel):
    """「本来こう解釈されるべきだった」の入力。golden_dataset の expected になる。"""

    user_query: str = Field(..., description="対象の質問文", max_length=2000)
    query_type: str = Field(..., description="tool schema の query_type enum")
    metrics: List[str] = Field(default_factory=list, description="METRIC_MAP のキー")
    split_type: Optional[str] = Field(None, description="splits 系のみ")
    player_name: Optional[str] = Field(None, description='例: "Seiya Suzuki"')
    season: Optional[int] = Field(None, ge=1871, le=2100)
    order_by: Optional[str] = Field(None, description="ランキング系のみ")
    expected_no_tool: bool = Field(
        False, description="ツールを呼ばず断るのが正解のケース"
    )
    request_id: Optional[str] = None
    note: Optional[str] = Field(None, max_length=1000)
    created_by: Optional[str] = Field(None, description="付与者。省略時は unknown")


@router.get("/labels", summary="ラベル軸の定義を返す")
def get_label_definitions() -> Dict[str, Any]:
    """フロント側でラベル一覧をハードコードさせないための定義エンドポイント。"""
    return {"success": True, "labels": VALID_LABELS}


@router.get("/expected-options", summary="期待値入力欄の選択肢を返す")
def get_expected_options() -> Dict[str, Any]:
    """フロントに query_type / metric 名をハードコードさせないための定義。

    選択肢の唯一のソースは QUERY_TYPE_CONFIG / METRIC_MAP である。
    フロント側で別の定数を持つと enum の同期漏れを起こす。
    """
    return {
        "success": True,
        "query_types": valid_query_types(),
        "split_types": valid_split_types(),
        "metrics": valid_metrics(),
        # GitHub 連携が未設定なら UI は PR ボタンを出さない
        "pr_enabled": is_configured(),
    }


@router.get("", summary="trace 一覧")
def list_traces_endpoint(
    days: int = Query(30, ge=1, le=365, description="遡る日数"),
    limit: int = Query(100, ge=1, le=500, description="返す trace 数の上限"),
    only_unlabeled: bool = Query(False, description="ラベル未付与のみ"),
    only_failed: bool = Query(False, description="失敗ステップを含むもののみ"),
    only_bad_rating: bool = Query(False, description="ユーザーが 👎 を付けたもののみ"),
    only_unexpected: bool = Query(False, description="期待値が未付与のもののみ"),
    force: bool = Query(False, description="True なら 60s キャッシュを無視"),
) -> Dict[str, Any]:
    # フィルタを増やしたら cache_key にも必ず足すこと。忘れると切り替えても
    # 60 秒間は前の結果が返り、「実装したのに動かない」状態になる。
    cache_key = (
        days, limit, only_unlabeled, only_failed, only_bad_rating, only_unexpected
    )
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
            only_bad_rating=only_bad_rating,
            only_unexpected=only_unexpected,
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


@router.post("/promote", summary="承認済みの期待値を golden に昇格する PR を作る")
def promote_endpoint(
    days: int = Query(90, ge=1, le=365, description="遡る日数"),
) -> Dict[str, Any]:
    """Trace Viewer で人の作業が終わった分を golden に取り込み、PR を作る。

    golden は CI の合格ラインそのものなので、出口は必ず PR にする。
    ここで直接 main に書き込むと、テストの基準が誰にも気づかれずに変わる。
    """
    try:
        result = create_golden_pr(days=days)
    except GoldenPRError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"create_golden_pr failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, **result}


@router.post("/{trace_id}/expected", summary="trace に期待値を付与")
def put_expectation_endpoint(trace_id: str, body: ExpectationRequest) -> Dict[str, Any]:
    try:
        row = put_expectation(
            trace_id=trace_id,
            user_query=body.user_query,
            query_type=body.query_type,
            metrics=body.metrics,
            split_type=body.split_type,
            player_name=body.player_name,
            season=body.season,
            order_by=body.order_by,
            expected_no_tool=body.expected_no_tool,
            request_id=body.request_id,
            note=body.note,
            created_by=body.created_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"put_expectation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    with _cache_lock:
        _cache.clear()
    return {"success": True, "data": row}
