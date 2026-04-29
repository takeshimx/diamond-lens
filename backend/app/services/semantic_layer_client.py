"""
MetricFlow Cloud Run サーバーへの認証付きHTTPクライアント。

backend (mlb-diamond-lens-api) から MetricFlow (mlb-metricflow-server) を
Cloud Run service-to-service authentication（OIDC IDトークン）で呼び出す。

ローカル開発時は METRICFLOW_SERVER_URL 未設定なら呼び出さない（Phase 4 のフラグで制御）。
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token

from backend.app.config.settings import get_settings
from backend.app.utils.structured_logger import get_logger

logger = get_logger("semantic-layer-client")
_settings = get_settings()

_HTTP_TIMEOUT_SEC = 30.0
_TOKEN_TTL_BUFFER_SEC = 300  # 期限の5分前に再取得
_token_cache: dict[str, tuple[str, float]] = {}  # audience -> (token, expires_at_epoch)
_token_lock = threading.Lock()


class SemanticLayerError(RuntimeError):
    """Semantic Layer 呼び出し失敗時の例外"""


def _get_id_token(audience: str) -> str:
    """
    Cloud Run サービス間認証用のIDトークンを取得する（同期）。

    1時間有効なので、_TOKEN_TTL_BUFFER_SEC を引いた時刻までキャッシュを再利用する。
    """
    now = time.time()
    with _token_lock:
        cached = _token_cache.get(audience)
        if cached and cached[1] - _TOKEN_TTL_BUFFER_SEC > now:
            return cached[0]
        token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
        _token_cache[audience] = (token, now + 3600)
        return token


def _ensure_url() -> str:
    url = _settings.metricflow_server_url
    if not url:
        raise SemanticLayerError(
            "METRICFLOW_SERVER_URL が未設定です。Cloud Run env vars または .env で指定してください。"
        )
    return url.rstrip("/")


def query_metric(
    metrics: list[str],
    group_by: Optional[list[str]] = None,
    where: Optional[list[str]] = None,
    order_by: Optional[list[str]] = None,
    limit: int = 100,
) -> dict:
    """
    MetricFlow Cloud Run サーバーにクエリを投げ、結果を返す（同期）。

    Returns:
        {"rows": [{...}, ...], "columns": [...]} 形式
    """
    url = _ensure_url()
    token = _get_id_token(audience=url)
    payload = {
        "metrics": metrics,
        "group_by": group_by or [],
        "where": where or [],
        "order_by": order_by or [],
        "limit": limit,
    }

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT_SEC) as client:
            resp = client.post(
                f"{url}/query",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "MetricFlow /query failed",
            status_code=e.response.status_code,
            body=e.response.text[:500],
            payload=payload,
        )
        raise SemanticLayerError(
            f"MetricFlow query failed (status={e.response.status_code}): {e.response.text[:200]}"
        ) from e
    except httpx.HTTPError as e:
        logger.warning("MetricFlow /query transport error", error=str(e))
        raise SemanticLayerError(f"MetricFlow transport error: {e}") from e


def list_available_metrics() -> list[str]:
    """MetricFlow に登録されたメトリクス名の一覧を取得する（同期）。"""
    url = _ensure_url()
    token = _get_id_token(audience=url)
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{url}/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json().get("metrics", [])


def list_available_dimensions() -> list[str]:
    """MetricFlow に登録された次元名の一覧を取得する（同期）。"""
    url = _ensure_url()
    token = _get_id_token(audience=url)
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{url}/dimensions",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json().get("dimensions", [])


# ============================================================
# メタデータキャッシュ（Phase 3: Oracle プロンプトに動的挿入するため）
# ============================================================

_metric_metadata_cache: Optional[dict] = None
_metadata_lock = threading.Lock()


def get_metric_metadata(force_refresh: bool = False) -> dict:
    """
    利用可能なメトリクス・次元のメタデータを取得する（同期）。

    Returns:
        {"metrics": [...], "dimensions": [...], "fetched_at": "ISO8601"} 形式
    """
    global _metric_metadata_cache

    if _metric_metadata_cache is not None and not force_refresh:
        return _metric_metadata_cache

    with _metadata_lock:
        if _metric_metadata_cache is not None and not force_refresh:
            return _metric_metadata_cache

        if not _settings.metricflow_server_url:
            logger.info("METRICFLOW_SERVER_URL not set, returning empty metadata")
            _metric_metadata_cache = {"metrics": [], "dimensions": [], "fetched_at": None}
            return _metric_metadata_cache

        try:
            metrics = list_available_metrics()
            dimensions = list_available_dimensions()
            _metric_metadata_cache = {
                "metrics": metrics,
                "dimensions": dimensions,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(
                "MetricFlow metadata cached",
                metric_count=len(metrics),
                dimension_count=len(dimensions),
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metric metadata, returning empty: {e}")
            _metric_metadata_cache = {"metrics": [], "dimensions": [], "fetched_at": None}

        return _metric_metadata_cache


def invalidate_metric_metadata() -> None:
    """
    メタデータキャッシュを破棄する。次回 get_metric_metadata() 呼出時に再取得される。
    """
    global _metric_metadata_cache
    _metric_metadata_cache = None
    logger.info("MetricFlow metadata cache invalidated")
