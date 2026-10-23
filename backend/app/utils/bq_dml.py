"""BigQuery への行書き込み（DML INSERT 専用）

このプロジェクトでは insert_rows_json / insert_rows（ストリーミング挿入）を使わない。
Streaming Buffer に入った行は最大 90 分程度 UPDATE / DELETE できず、
誤ったラベルの修正やテスト行の削除がその間できなくなるため。

列の型はテーブルのスキーマから実行時に取得する（呼び出し側で型を直書きしない）。
"""
import threading
from typing import Any, Dict, List, Sequence

from google.cloud import bigquery

# クエリパラメータとしてそのまま渡せる型
_SCALAR_TYPES = {
    "STRING": "STRING",
    "INTEGER": "INT64",
    "INT64": "INT64",
    "FLOAT": "FLOAT64",
    "FLOAT64": "FLOAT64",
    "NUMERIC": "NUMERIC",
    "BIGNUMERIC": "BIGNUMERIC",
    "BOOLEAN": "BOOL",
    "BOOL": "BOOL",
    "BYTES": "BYTES",
}

# 文字列で渡し、SQL 側で変換する型。insert_rows_json に渡していた
# ISO 8601 文字列や JSON 文字列を、呼び出し側を変えずに受け付けるため。
_CAST_EXPRS = {
    "TIMESTAMP": "CAST({} AS TIMESTAMP)",
    "DATETIME": "CAST({} AS DATETIME)",
    "DATE": "CAST({} AS DATE)",
    "TIME": "CAST({} AS TIME)",
    "JSON": "PARSE_JSON({})",
}

_schema_cache: Dict[str, Dict[str, bigquery.SchemaField]] = {}
_schema_lock = threading.Lock()


def _get_schema(client: bigquery.Client, table_id: str) -> Dict[str, bigquery.SchemaField]:
    with _schema_lock:
        if table_id not in _schema_cache:
            table = client.get_table(table_id)
            _schema_cache[table_id] = {f.name: f for f in table.schema}
        return _schema_cache[table_id]


def _build_param(name: str, field: bigquery.SchemaField, value: Any):
    """(SQL 上の式, クエリパラメータ) を返す。"""
    field_type = field.field_type.upper()
    placeholder = f"@{name}"

    if field_type in ("RECORD", "STRUCT"):
        raise ValueError(f"RECORD column is not supported: {field.name}")

    if field.mode == "REPEATED":
        if field_type in _CAST_EXPRS:
            raise ValueError(f"REPEATED {field_type} column is not supported: {field.name}")
        param_type = _SCALAR_TYPES.get(field_type, "STRING")
        return placeholder, bigquery.ArrayQueryParameter(name, param_type, list(value or []))

    if field_type in _CAST_EXPRS:
        text = None if value is None else str(value)
        return _CAST_EXPRS[field_type].format(placeholder), bigquery.ScalarQueryParameter(name, "STRING", text)

    param_type = _SCALAR_TYPES.get(field_type, "STRING")
    return placeholder, bigquery.ScalarQueryParameter(name, param_type, value)


def insert_rows_dml(client: bigquery.Client, table_id: str, rows: Sequence[Dict[str, Any]]) -> None:
    """rows を 1 本の DML INSERT で書き込む。

    Raises:
        ValueError: テーブルに存在しない列、または未対応の型の列が含まれる場合
        google.api_core.exceptions.GoogleAPIError: クエリ実行に失敗した場合
    """
    if not rows:
        return

    schema = _get_schema(client, table_id)

    # 行ごとにキーが欠けていても NULL で埋められるよう、全行のキーの和集合を列にする
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)

    unknown = [c for c in columns if c not in schema]
    if unknown:
        raise ValueError(f"columns not in {table_id}: {unknown}")

    params = []
    values_sql = []
    for i, row in enumerate(rows):
        exprs = []
        for j, col in enumerate(columns):
            expr, param = _build_param(f"r{i}_c{j}", schema[col], row.get(col))
            exprs.append(expr)
            params.append(param)
        values_sql.append(f"({', '.join(exprs)})")

    query = (
        f"INSERT INTO `{table_id}` ({', '.join(f'`{c}`' for c in columns)})\n"
        f"VALUES {', '.join(values_sql)}"
    )
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    client.query(query, job_config=job_config).result()
