#!/usr/bin/env python3
"""
Schema Validation GATE for CI/CD Pipeline

このスクリプトはquery_maps.pyの設定とBigQueryの実際のテーブルスキーマを比較します。
不一致があればCI/CDパイプラインを停止します。

使用方法:
    python validate_schema_config.py

終了コード:
    0: 全て検証成功
    1: スキーマ不一致検出（CI/CDパイプライン停止）
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from google.cloud import bigquery
from google.api_core import exceptions

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.config.query_maps import QUERY_TYPE_CONFIG, METRIC_MAP

# 環境変数から設定を取得
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")

# カラー出力用
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """ヘッダーを出力"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(message: str):
    """成功メッセージを出力"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """エラーメッセージを出力"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """警告メッセージを出力"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def get_bigquery_schema(client: bigquery.Client, table_id: str) -> Set[str]:
    """
    BigQueryテーブルのスキーマ（カラム名一覧）を取得

    Args:
        client: BigQueryクライアント
        table_id: テーブルID

    Returns:
        カラム名のセット
    """
    try:
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
        table = client.get_table(table_ref)
        return {field.name for field in table.schema}
    except exceptions.NotFound:
        print_error(f"Table not found: {table_id}")
        return set()
    except Exception as e:
        print_error(f"Error fetching schema for {table_id}: {e}")
        return set()


def validate_table_columns(
    client: bigquery.Client,
    table_id: str,
    config: Dict[str, Any],
    query_type: str
) -> bool:
    """
    テーブルの必須カラムが存在するか検証

    Args:
        client: BigQueryクライアント
        table_id: テーブルID
        config: QUERY_TYPE_CONFIGのエントリ
        query_type: クエリタイプ名（エラーメッセージ用）

    Returns:
        True: 検証成功, False: 検証失敗
    """
    print(f"\n{Colors.BOLD}Validating: {query_type} -> {table_id}{Colors.RESET}")

    # BigQueryからスキーマ取得
    bq_schema = get_bigquery_schema(client, table_id)
    if not bq_schema:
        return False

    validation_passed = True

    # 必須カラムの検証
    required_columns = []

    # year_col (空文字列の場合はスキップ)
    if config.get("year_col"):
        required_columns.append(config["year_col"])

    # player_col
    if config.get("player_col"):
        required_columns.append(config["player_col"])

    # month_col (存在する場合)
    if config.get("month_col"):
        required_columns.append(config["month_col"])

    # available_metrics
    if config.get("available_metrics"):
        required_columns.extend(config["available_metrics"])

    # 重複削除
    required_columns = list(set(required_columns))

    # カラムの存在チェック
    missing_columns = []
    for col in required_columns:
        if col not in bq_schema:
            missing_columns.append(col)
            validation_passed = False

    if missing_columns:
        print_error(f"Missing columns in {table_id}:")
        for col in missing_columns:
            print(f"  - {col}")
    else:
        print_success(f"All required columns exist in {table_id}")
        print(f"  Validated columns: {', '.join(sorted(required_columns)[:5])}{'...' if len(required_columns) > 5 else ''}")

    return validation_passed


def validate_metric_mappings(client: bigquery.Client) -> bool:
    """
    METRIC_MAPで参照されているカラムが実際のテーブルに存在するか検証

    Args:
        client: BigQueryクライアント

    Returns:
        True: 検証成功, False: 検証失敗
    """
    print_header("Validating METRIC_MAP Column Mappings")

    # テーブルごとにスキーマをキャッシュ
    schema_cache = {}
    validation_passed = True
    errors_found = []

    # METRIC_MAPを走査
    for metric_name, mappings in METRIC_MAP.items():
        for query_type_key, column_or_dict in mappings.items():
            # career_battingの特殊なネスト構造を処理
            if isinstance(column_or_dict, dict):
                for sub_key, column_name in column_or_dict.items():
                    # テーブルIDを取得（簡略化のため主要タイプのみチェック）
                    if "career_batting" in query_type_key:
                        table_id = "tbl_batter_career_stats_master"
                    else:
                        continue  # 他の複雑なケースはスキップ

                    # スキーマ取得（キャッシュ利用）
                    if table_id not in schema_cache:
                        schema_cache[table_id] = get_bigquery_schema(client, table_id)

                    # カラム存在チェック
                    if column_name not in schema_cache[table_id]:
                        errors_found.append(f"{metric_name}.{query_type_key}.{sub_key} -> {column_name} (not in {table_id})")
                        validation_passed = False
            else:
                # 通常のマッピング
                column_name = column_or_dict

                # クエリタイプからテーブルIDを推定
                if "season_batting" in query_type_key:
                    table_id = "fact_batting_stats_with_risp"
                elif "season_pitching" in query_type_key:
                    table_id = "fact_pitching_stats"
                elif "batting_splits" in query_type_key:
                    # batting_splitsの場合、QUERY_TYPE_CONFIGから取得
                    split_type = query_type_key.replace("batting_splits_", "")
                    if split_type in QUERY_TYPE_CONFIG.get("batting_splits", {}):
                        table_id = QUERY_TYPE_CONFIG["batting_splits"][split_type]["table_id"]
                    else:
                        continue  # 不明なスプリットタイプはスキップ
                else:
                    continue  # 不明なクエリタイプはスキップ

                # スキーマ取得（キャッシュ利用）
                if table_id not in schema_cache:
                    schema_cache[table_id] = get_bigquery_schema(client, table_id)

                # カラム存在チェック
                if schema_cache[table_id] and column_name not in schema_cache[table_id]:
                    errors_found.append(f"{metric_name}.{query_type_key} -> {column_name} (not in {table_id})")
                    validation_passed = False

    if errors_found:
        print_error(f"Found {len(errors_found)} metric mapping errors:")
        for error in errors_found[:10]:  # 最初の10件のみ表示
            print(f"  - {error}")
        if len(errors_found) > 10:
            print(f"  ... and {len(errors_found) - 10} more errors")
    else:
        print_success(f"All metric mappings are valid")

    return validation_passed


def main():
    """メイン処理"""
    print_header("Schema Validation GATE - Starting...")

    # BigQueryクライアント初期化
    try:
        client = bigquery.Client(project=PROJECT_ID)
        print_success(f"Connected to BigQuery project: {PROJECT_ID}")
        print_success(f"Dataset: {DATASET_ID}")
    except Exception as e:
        print_error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)

    overall_validation_passed = True

    # QUERY_TYPE_CONFIGの検証
    print_header("Validating QUERY_TYPE_CONFIG Tables")

    for query_type, config in QUERY_TYPE_CONFIG.items():
        if query_type == "batting_splits":
            # batting_splitsのネスト構造を処理
            for split_name, split_config in config.items():
                table_id = split_config["table_id"]
                result = validate_table_columns(
                    client,
                    table_id,
                    split_config,
                    f"{query_type}.{split_name}"
                )
                if not result:
                    overall_validation_passed = False
        else:
            table_id = config["table_id"]
            result = validate_table_columns(client, table_id, config, query_type)
            if not result:
                overall_validation_passed = False

    # METRIC_MAPの検証
    metric_validation = validate_metric_mappings(client)
    if not metric_validation:
        overall_validation_passed = False

    # 結果サマリー
    print_header("Validation Summary")

    if overall_validation_passed:
        print_success("✓ ALL VALIDATIONS PASSED")
        print_success("Schema configuration is in sync with BigQuery")
        print("\nCI/CD Pipeline can proceed safely.\n")
        sys.exit(0)
    else:
        print_error("✗ VALIDATION FAILED")
        print_error("Schema configuration does NOT match BigQuery")
        print("\n⚠️  CI/CD Pipeline STOPPED to prevent deployment issues.\n")
        print("Action required:")
        print("  1. Update query_maps.py to match BigQuery schema")
        print("  2. OR update BigQuery tables to match query_maps.py")
        print("  3. Re-run validation\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
