"""
BigQueryクライアントを提供する役割。
このファイル自体には個別のデータ取得ロジックは含めず、他のサービス層から import して利用する。

client は遅延初期化プロキシ。`from .bigquery_service import client` は認証を発生させず、
初めて client.query(...) 等を呼んだ時点で実クライアントを生成する。
これにより GCP 認証のない環境（CI・ユニットテスト）でも import が成功する。
"""
import os
from typing import Any, Optional

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
PROJECT_ID = os.getenv('GCP_PROJECT_ID')

_real_client: Optional[bigquery.Client] = None


def get_bq_client() -> bigquery.Client:
    """実 BigQuery クライアントを返す（初回のみ生成するシングルトン）。"""
    global _real_client
    if _real_client is None:
        _real_client = bigquery.Client(project=PROJECT_ID)
    return _real_client


def reset_bq_client() -> None:
    """テスト用。生成済みクライアントを破棄し、次回アクセスで作り直させる。"""
    global _real_client
    _real_client = None


class _LazyBigQueryClient:
    """属性アクセスされて初めて実クライアントを生成する透過プロキシ。

    `client.query(sql)` の `.query` を取りに来たタイミングで get_bq_client() が走る。
    import 時点では何も起きないため、GCP 認証なしでモジュールを読み込める。
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_bq_client(), name)

    def __repr__(self) -> str:
        state = "initialized" if _real_client is not None else "not initialized"
        return f"<LazyBigQueryClient project={PROJECT_ID} ({state})>"


client = _LazyBigQueryClient()
