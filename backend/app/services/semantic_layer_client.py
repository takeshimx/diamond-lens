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

    取得経路:
      1. 本番 (Cloud Run): metadata server から自動取得（高速・標準パス）
      2. ローカル開発: 1が失敗したら `gcloud auth print-identity-token` にフォールバック
    """
    import subprocess

    now = time.time()
    with _token_lock:
        cached = _token_cache.get(audience)
        if cached and cached[1] - _TOKEN_TTL_BUFFER_SEC > now:
            return cached[0]

        try:
            # 標準パス（Cloud Run の metadata server / GOOGLE_APPLICATION_CREDENTIALS）
            token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
        except Exception as primary_error:
            logger.info(
                "metadata-server token fetch failed; falling back to gcloud CLI "
                f"(reason: {primary_error})"
            )
            # ローカル開発フォールバック: gcloud CLI で ID トークン取得
            # Windows では gcloud は .cmd ファイルなので shell=True で PATHEXT 解決させる
            import platform
            is_windows = platform.system() == "Windows"
            cmd_args = ["gcloud", "auth", "print-identity-token", f"--audiences={audience}"]
            try:
                if is_windows:
                    # shell=True 用に文字列化（audience に空白等は入らない前提）
                    cmd_str = " ".join(cmd_args)
                    result = subprocess.run(
                        cmd_str, capture_output=True, text=True, check=True, shell=True
                    )
                else:
                    result = subprocess.run(
                        cmd_args, capture_output=True, text=True, check=True, shell=False
                    )
                token = result.stdout.strip()
                if not token:
                    raise SemanticLayerError("gcloud returned empty ID token")
            except FileNotFoundError as e:
                raise SemanticLayerError(
                    "gcloud CLI が見つかりません。本番では metadata server から取得されますが、"
                    "ローカル開発では gcloud auth login + Google Cloud SDK が必要です。"
                ) from e
            except subprocess.CalledProcessError as e:
                raise SemanticLayerError(
                    f"gcloud auth print-identity-token 失敗: {e.stderr.strip() or e.stdout.strip()}"
                ) from e

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


# メタデータ取得は MetricFlow Cloud Run のコールドスタート（dbt parse で20秒前後）を
# 吸収できるよう長めにする。アプリ起動時に1回叩いてキャッシュするため、
# レイテンシよりも確実性を優先。
_METADATA_TIMEOUT_SEC = 60.0


def list_available_metrics() -> list[str]:
    """MetricFlow に登録されたメトリクス名の一覧を取得する（同期）。"""
    url = _ensure_url()
    token = _get_id_token(audience=url)
    with httpx.Client(timeout=_METADATA_TIMEOUT_SEC) as client:
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
    with httpx.Client(timeout=_METADATA_TIMEOUT_SEC) as client:
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


def _fetch_metadata_with_retry(max_attempts: int = 3, backoff_sec: float = 5.0) -> dict:
    """
    メタデータ取得をリトライ付きで実行する。

    MetricFlow Cloud Run はコールドスタート時の dbt parse で20秒以上待たされるため、
    1回失敗しても数秒空けてリトライする。
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            metrics = list_available_metrics()
            dimensions = list_available_dimensions()
            logger.info(
                "MetricFlow metadata fetched",
                attempt=attempt,
                metric_count=len(metrics),
                dimension_count=len(dimensions),
            )
            return {
                "metrics": metrics,
                "dimensions": dimensions,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            last_error = e
            logger.warning(
                f"MetricFlow metadata fetch attempt {attempt}/{max_attempts} failed: {e}"
            )
            if attempt < max_attempts:
                time.sleep(backoff_sec)

    logger.warning(
        f"MetricFlow metadata fetch exhausted retries (last_error: {last_error}); "
        "caching empty metadata. Validation will fail-open until next refresh."
    )
    return {"metrics": [], "dimensions": [], "fetched_at": None}


def warmup_metric_metadata() -> dict:
    """
    アプリ起動時に呼び出す。リトライ付きでメタデータをキャッシュ確定する。

    既にキャッシュされていれば再取得しない（多重起動 race 用）。
    """
    global _metric_metadata_cache

    with _metadata_lock:
        if _metric_metadata_cache is not None:
            return _metric_metadata_cache

        if not _settings.metricflow_server_url:
            logger.info("METRICFLOW_SERVER_URL not set; skipping metadata warmup")
            _metric_metadata_cache = {"metrics": [], "dimensions": [], "fetched_at": None}
            return _metric_metadata_cache

        _metric_metadata_cache = _fetch_metadata_with_retry()
        return _metric_metadata_cache


def get_metric_metadata(force_refresh: bool = False) -> dict:
    """
    キャッシュ済みメタデータを返す（同期、ノンブロッキング想定）。

    通常はアプリ起動時の warmup_metric_metadata() でキャッシュが満たされている。
    リクエスト経路から呼ばれた場合にキャッシュが空なら、即座に再取得を試みる
    （ただし MetricFlow がコールドスタート中だと失敗してフォールバック空を返す）。
    """
    global _metric_metadata_cache

    if _metric_metadata_cache is not None and not force_refresh:
        return _metric_metadata_cache

    with _metadata_lock:
        if _metric_metadata_cache is not None and not force_refresh:
            return _metric_metadata_cache

        if not _settings.metricflow_server_url:
            _metric_metadata_cache = {"metrics": [], "dimensions": [], "fetched_at": None}
            return _metric_metadata_cache

        # warmup と違い、リクエスト経路ではリトライ少なめ・短時間で打ち切る
        _metric_metadata_cache = _fetch_metadata_with_retry(max_attempts=1, backoff_sec=0.0)
        return _metric_metadata_cache


def invalidate_metric_metadata() -> None:
    """
    メタデータキャッシュを破棄する。次回 get_metric_metadata() 呼出時に再取得される。
    """
    global _metric_metadata_cache
    _metric_metadata_cache = None
    logger.info("MetricFlow metadata cache invalidated")
