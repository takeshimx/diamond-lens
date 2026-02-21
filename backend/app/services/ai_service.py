from typing import Optional, List, Dict, Any
# from google.cloud import bigquery
# from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import os
import json
import requests
import re
from dotenv import load_dotenv
# from functools import lru_cache
from datetime import datetime
from .bigquery_service import client
import logging
from .conversation_service import get_conversation_service
from .analytics.base_engine import BaseEngine
from backend.app.config.prompt_registry import get_prompt, get_prompt_version

# インポート: テスト実行時と本番実行時の両方に対応
try:
    # テスト実行時の相対インポート
    from app.config.query_maps import (
        QUERY_TYPE_CONFIG,
        METRIC_MAP,
        DECIMAL_FORMAT_COLUMNS,
        MAIN_PITCHING_STATS,
        MAIN_BATTING_STATS,
        MAIN_CAREER_BATTING_STATS,
        MAIN_RISP_BATTING_STATS, MAIN_BASES_LOADED_BATTING_STATS, MAIN_RUNNER_ON_1B_BATTING_STATS,
        MAIN_INNING_BATTING_STATS, MAIN_BATTING_BY_PITCHING_THROWS_STATS, MAIN_BATTING_BY_PITCH_TYPE_STATS,
        MAIN_BATTING_BY_GAME_SCORE_SITUATIONS_STATS
    )
    from app.config.statcast_query import KEY_METRICS_QUERY_SELECT
except ImportError:
    # 本番実行時の絶対インポート
    from backend.app.config.query_maps import (
        QUERY_TYPE_CONFIG,
        METRIC_MAP,
        DECIMAL_FORMAT_COLUMNS,
        MAIN_PITCHING_STATS,
        MAIN_BATTING_STATS,
        MAIN_CAREER_BATTING_STATS,
        MAIN_RISP_BATTING_STATS, MAIN_BASES_LOADED_BATTING_STATS, MAIN_RUNNER_ON_1B_BATTING_STATS,
        MAIN_INNING_BATTING_STATS, MAIN_BATTING_BY_PITCHING_THROWS_STATS, MAIN_BATTING_BY_PITCH_TYPE_STATS,
        MAIN_BATTING_BY_GAME_SCORE_SITUATIONS_STATS
    )
    from backend.app.config.statcast_query import KEY_METRICS_QUERY_SELECT
# from .simple_chart_service import enhance_response_with_simple_chart, should_show_simple_chart # For Development, add backend. path

# ロガーの設定
logging.getLogger().handlers = []
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# 環境変数から設定を読み込む
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID")
BATTING_STATS_TABLE_ID = os.getenv("BIGQUERY_BATTING_STATS_TABLE_ID", "fact_batting_stats_with_risp")
PITCHING_STATS_TABLE_ID = os.getenv("BIGQUERY_PITCHING_STATS_TABLE_ID", "fact_pitching_stats")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_V2")

# Manage Google cloud alient with singleton pattern
SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _parse_query_with_llm(query: str, season: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    [ステップ1] LLMを使い、質問からパラメータを抽出します。この関数はLLMの役割を果たします。ユーザーの質問を解析し、「意図」を汲み取り、
    データベースで検索するためのパラメータをJSON形式で抽出します。
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY_V2 is not set.")
        return None

    # Get the prompt version-managed by prompt_registry.py
    prompt = get_prompt(
        "parse_query",
        query=query,
        season=season if season else "None"
    )
    prompt_version = get_prompt_version("parse_query")
    logger.info(f"Using parse_query prompt version: {prompt_version}")

    GEMINI_API_URL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result.get("candidates"):
            json_string = result["candidates"][0]["content"]["parts"][0]["text"]
            params = json.loads(json_string)

            logger.info(f"Parsed parameters: {params}")

            if season and 'season' not in params:
                params['season'] = season
            return params
        return None
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Error during LLM query parsing: {e}", exc_info=True)
        return None


def _validate_query_params(params: Dict[str, Any]) -> bool:
    """
    LLM出力パラメータのセキュリティ検証を行います。
    SQLインジェクション攻撃やその他の不正な入力を検出します。

    Args:
        params: LLMから抽出されたクエリパラメータ

    Returns:
        bool: 検証に合格した場合True、不正な入力を検出した場合False

    検証項目:
        1. 選手名: 英字、スペース、ピリオド、ハイフン、アポストロフィのみ許可
        2. Season: 妥当な年の範囲（1900-2100）
        3. query_type: ホワイトリストに含まれる値のみ
        4. split_type: ホワイトリストに含まれる値のみ
        5. metrics: METRIC_MAPに含まれる値のみ（main_statsを除く）
        6. order_by: METRIC_MAPに含まれる値のみ
        7. pitcher_throws: RHPまたはLHPのみ
        8. inning: 1-9の整数のみ
        9. strikes/balls: 0-3の整数のみ
        10. 長さ制限: 異常に長い文字列を拒否
    """

    return BaseEngine.validate_query_params(params)


# Helper function to determine query strategy (using a simple query or more complex one)
def _determine_query_strategy(params: Dict[str, Any]) -> str:
    """
    クエリの複雑さに基づいて戦略を決定する
    - 複合条件が2つ以上: statcast master table
    - 単一条件: aggregated table
    - パフォーマンス重視が必要な場合の特別処理も含む
    """

    return BaseEngine.determine_query_strategy(params)


# Helper function to build dynamic SQL queries with statcast_master_table
def _build_dynamic_statcast_sql(params: Dict[str, Any]) -> tuple[str, dict]:
    """
    statcast_master_tableに対するパラメータ化クエリを構築します。

    Args:
        params: LLMから抽出されたクエリパラメータ

    Returns:
        tuple[str, dict]: (SQL文字列, パラメータ辞書)
    """

    return BaseEngine.build_dynamic_statcast_sql(params)
        
 

# Helper function to build dynamic SQL queries with aggregated table
def _build_dynamic_sql(params: Dict[str, Any]) -> tuple[str, dict]:
    """
    [ステップ2] 抽出したパラメータを元に、BigQuery用のパラメータ化クエリを構築します。

    Args:
        params: LLMから抽出されたクエリパラメータ

    Returns:
        tuple[str, dict]: (SQL文字列, パラメータ辞書)
        - SQL文字列: プレースホルダー（@param_name）を含むクエリ
        - パラメータ辞書: プレースホルダーに対応する実際の値
    """

    return BaseEngine.build_dynamic_sql(params)


def _generate_final_response_with_llm(original_query: str, data_df: pd.DataFrame) -> str:
    """
    [ステップ4] 取得したデータと元の質問に基づいて、LLMが自然言語の回答を生成します。
    * ステップ3はBigQueryからデータを取得することです。
    """
   
    return BaseEngine.generate_final_response_with_llm(original_query, data_df)


def get_ai_response_for_qna_enhanced(
        query: str, 
        season: Optional[int] = None,
        session_id: Optional[str] = None # Id from frontend to track user session
    ) -> Optional[Dict[str, Any]]:
    """
    【打撃リーダーボード特化版】
    ユーザーの"打撃リーダーボード"に関する質問を処理します。
    """

    # Step 0: Resolve conversation context (会話コンテキストの解決 == 直前の履歴から情報を補完)
    conv_service = get_conversation_service()
    resolved_query = query
    context_used = False

    if session_id:
        logger.info(f"Resolving conversation context for session_id: {session_id}")
        context_result = conv_service.resolve_context(query, session_id)
        resolved_query = context_result["resolved_query"]
        context_used = context_result["context_used"]

        # コンテキストから season を補完
        if not season and context_result.get("season"):
            season = int(context_result["season"])
            logger.info(f"Season {season} inferred from conversation context")
        
        if context_used:
            logger.info(f"Query resolved: '{query}' → '{resolved_query}'")
        
        # ユーザーメッセージを会話履歴に保存。次の質問で「さっきの質問をもう一度」などの文脈が使えるようにする。
        conv_service.add_message(session_id, "user", query)

    # Step 1: LLMで質問を解析（解決後のクエリを使用）
    query_params = _parse_query_with_llm(resolved_query, season)
    if not query_params:
        logger.warning("Could not extract parameters from the query.")
        error_response = {
            "answer": "質問を理解できませんでした。打撃成績のランキングについて質問してください。（例：2024年のホームラン王は誰？）",
            "isTable": False
        }

        # エラーレスポンスも会話履歴に保存
        if session_id:
            conv_service.add_message(session_id, "assistant", error_response["answer"])
        
        return error_response
    
    logger.info(f"Parsed query parameters: {query_params}")

    # Step 1.5: セキュリティ検証（SQLインジェクション対策）
    if not _validate_query_params(query_params):
        logger.error(f"Security validation failed for parameters: {query_params}")
        return {
            "answer": "不正な入力を検出しました。正しい形式で質問してください。",
            "isTable": False
        }

    # Step 2: Build SQL with parameterization
    query_strategy = _determine_query_strategy(query_params)
    logger.info(f"Using query strategy: {query_strategy}")

    if query_strategy == "aggregated_table":
        # Using aggregated table
        sql_query, sql_parameters = _build_dynamic_sql(query_params)
        if not sql_query:
            logger.warning("Failed to build SQL query.")
            return {
                "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
                "isTable": False
            }
        logger.info(f"Generated parameterized SQL query:\n{sql_query}")
        logger.info(f"Query parameters: {sql_parameters}")

    else: # Using statcast master table
        sql_query, sql_parameters = _build_dynamic_statcast_sql(query_params)
        if not sql_query:
            logger.warning("Failed to build SQL query with statcast master table.")
            return {
                "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
                "isTable": False
            }
        logger.info(f"Generated parameterized SQL query (strategy: {query_strategy}):\n{sql_query}")
        logger.info(f"Query parameters: {sql_parameters}")

    # Step 3: Fetch data from BigQuery with parameterized query
    try:
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter

        # BigQuery用のパラメータ設定を作成
        query_parameters_list = []

        for key, value in sql_parameters.items():
            if isinstance(value, list):
                # 配列パラメータ（例: pitch_types, innings）
                # 配列の要素の型を判定
                if value and isinstance(value[0], int):
                    param = ArrayQueryParameter(key, "INT64", value)
                    query_parameters_list.append(param)
                    logger.debug(f"Added array parameter: {key} = {value} (INT64)")
                else:
                    param = ArrayQueryParameter(key, "STRING", value)
                    query_parameters_list.append(param)
                    logger.debug(f"Added array parameter: {key} = {value} (STRING)")
            elif isinstance(value, int):
                # 整数パラメータ（例: season, inning, limit）
                param = ScalarQueryParameter(key, "INT64", value)
                query_parameters_list.append(param)
                logger.debug(f"Added scalar parameter: {key} = {value} (INT64)")
            else:
                # 文字列パラメータ（例: player_name, pitcher_throws）
                param = ScalarQueryParameter(key, "STRING", str(value))
                query_parameters_list.append(param)
                logger.debug(f"Added scalar parameter: {key} = {value} (STRING)")

        job_config = QueryJobConfig(query_parameters=query_parameters_list)

        logger.info(f"Total query parameters configured: {len(query_parameters_list)}")
        logger.debug(f"Query parameters list: {[p.name for p in query_parameters_list]}")

        query_start = datetime.now()
        results_df = client.query(sql_query, job_config=job_config).to_dataframe()
        query_duration = (datetime.now() - query_start).total_seconds()

        logger.info(f"Query completed in {query_duration:.2f}s, fetched {len(results_df)} rows")

        # Performance warning for slow queries
        if query_duration > 10:  # 10秒以上
            logger.warning(f"Slow query detected: {query_duration:.2f}s")
    except GoogleCloudError as e:
        logger.error(f"BigQuery query failed: {e}", exc_info=True)

        # より詳細なエラーメッセージ
        error_message = "データベースからのデータ取得中にエラーが発生しました。"
        if "timeout" in str(e).lower():
            error_message += "クエリがタイムアウトしました。条件を絞って再試行してください。"
        elif "quota" in str(e).lower():
            error_message += "利用制限に達しました。しばらくしてから再試行してください。"
        
        return {
            "answer": error_message,
            "isTable": False
        }
    
    if results_df.empty:
        return {
            "answer": "指定された条件に一致するデータが見つかりませんでした。条件を変更して再試行してください。",
            "isTable": False
        }
    
    # Step 4: Format response
    total_duration = (datetime.now() - query_start).total_seconds()
    logger.info(f"Total request processing time: {total_duration:.2f}s")
    
    # if output format is table
    if query_params.get("output_format") == "table":
        # Debug logging
        logger.info(f"DataFrame columns: {results_df.columns.tolist()}")
        logger.info(f"DataFrame dtypes: {results_df.dtypes.to_dict()}")
        logger.info(f"First row sample: {results_df.iloc[0].to_dict() if len(results_df) > 0 else 'No data'}")
        
        # Use centralized decimal columns configuration
        decimal_columns = DECIMAL_FORMAT_COLUMNS
        
        # Force decimal columns to have proper numeric types BEFORE converting to dict
        for col in decimal_columns:
            if col in results_df.columns:
                # Convert to numeric, coercing errors to NaN, then fill NaN with None
                results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
                results_df[col] = results_df[col].where(pd.notnull(results_df[col]), None)
        
        # Convert to dictionary
        table_data = results_df.to_dict('records')
        
        # Post-process to ensure decimal formatting
        for row in table_data:
            for col in decimal_columns:
                if col in row and row[col] is not None:
                    try:
                        # Ensure it's a proper decimal number
                        value = float(row[col])
                        if not pd.isna(value):
                            row[col] = round(value, 3)
                        else:
                            row[col] = None
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert {col} value {row[col]} to float: {e}")
                        # Keep original value
                        pass
        
        # Debug the final table data
        logger.info(f"Final table_data sample: {table_data[0] if table_data else 'No data'}")
        
        columns = [{"key": col, "label": col.replace('_', ' ').title()} for col in results_df.columns]
        
        # Check if single row result for transposition
        is_single_row = len(results_df) == 1
        
        # Add grouping metadata for career batting
        grouping_info = None
        if query_params.get("query_type") == "career_batting":
            # Get base info columns (name, team, etc.)
            base_columns = [col for col in results_df.columns if col in ['name', 'batter_name', 'career_last_team']]
            career_base_columns = [col for col in results_df.columns if col.startswith('career_') and '_at_' not in col and '_by_' not in col]
            risp_columns = [col for col in results_df.columns if '_at_risp' in col]
            bases_loaded_columns = [col for col in results_df.columns if '_at_bases_loaded' in col]
            
            grouping_info = {
                "type": "career_batting_chunks",
                "groups": [
                    {
                        "name": "Career Stats",
                        "columns": base_columns + career_base_columns
                    },
                    {
                        "name": "Career RISP Stats", 
                        "columns": risp_columns
                    },
                    {
                        "name": "Career Bases Loaded Stats",
                        "columns": bases_loaded_columns
                    }
                ]
            }
        
        table_response = {
            "answer": f"以下は{len(results_df)}件の結果です：",
            "isTable": True,
            "isTransposed": is_single_row,
            "tableData": table_data,
            "columns": columns,
            "decimalColumns": [col for col in results_df.columns if col in DECIMAL_FORMAT_COLUMNS],
            "grouping": grouping_info
        }

        # テーブル表示も履歴に保存
        if session_id:
            # テーブル全体ではなく要約を保存（トークン節約）
            summary = f"{len(results_df)}件の{query_params.get('query_type', '結果')}データを表示"
            conv_service.add_message(
                session_id,
                "assistant",
                summary,
                metadata={ # 後で分析に使える（例: どの選手がよく検索されているか）
                    "query_type": query_params.get("query_type"),
                    "player_name": query_params.get("name"),
                    "is_table": True,
                    "context_used": context_used
                }
            )
        
        return table_response

    # Step 4: Generate final response with LLM
    else:
        logger.info("Generating final response with LLM.")
        final_response = _generate_final_response_with_llm(query, results_df)

        # 回答を履歴に保存
        if session_id:
            conv_service.add_message(
                session_id,
                "assistant",
                final_response,
                metadata={ # 後で分析に使える（例: どの選手がよく検索されているか）
                    "query_type": query_params.get("query_type"),
                    "player_name": query_params.get("name"),
                    "context_used": context_used
                }
            )
        
        # Try to enhance with chart data
        from .simple_chart_service import enhance_response_with_simple_chart
        try:
            chart_data = enhance_response_with_simple_chart(
                query, query_params, results_df, season
            )
            
            if chart_data:
                # Return response with chart data only (minimal text)
                response = {
                    "answer": "📈",  # Just chart emoji to avoid empty content message
                    "isTable": False
                }
                response.update(chart_data)
                return response
        except Exception as e:
            logger.warning(f"Chart enhancement failed: {e}")
        
        # Return regular response if no chart enhancement
        return {
            "answer": final_response,
            "isTable": False
        }


def get_ai_response_with_simple_chart(
    query: str,
    season: Optional[int] = None,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """既存関数を拡張してシンプルチャート対応（会話履歴対応）"""

    # Just call the existing function for now - we'll integrate chart logic directly into it
    return get_ai_response_for_qna_enhanced(query, season, session_id)