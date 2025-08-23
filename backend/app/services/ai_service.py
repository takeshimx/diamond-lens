from typing import Optional, List, Dict, Any
# from google.cloud import bigquery
# from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import os
import json
import requests
from dotenv import load_dotenv
# from functools import lru_cache
from datetime import datetime
from .bigquery_service import client
import logging
from backend.app.config.query_maps import (
    QUERY_TYPE_CONFIG,
    METRIC_MAP,
    DECIMAL_FORMAT_COLUMNS,
    MAIN_PITCHING_STATS,
    MAIN_BATTING_STATS,
    MAIN_CAREER_BATTING_STATS,
    MAIN_RISP_BATTING_STATS, MAIN_BASES_LOADED_BATTING_STATS, MAIN_RUNNER_ON_1B_BATTING_STATS,
    MAIN_INNING_BATTING_STATS, MAIN_BATTING_BY_PITCHING_THROWS_STATS, MAIN_BATTING_BY_PITCH_TYPE_STATS
)

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Manage Google cloud alient with singleton pattern
SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _parse_query_with_llm(query: str, season: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    [ステップ1] LLMを使い、質問からパラメータを抽出します。この関数はLLMの役割を果たします。ユーザーの質問を解析し、「意図」を汲み取り、
    データベースで検索するためのパラメータをJSON形式で抽出します。
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return None

    prompt = f"""
    あなたはMLBのデータアナリストです。ユーザーからの"打撃成績のランキング"、"投手成績のランキング"、または"選手成績"に関する以下の質問を解析し、
    データベースで検索するためのパラメータをJSON形式で抽出してください。

    # 指示
    - 選手名は英語表記（フルネーム）に正規化してください。例：「大谷さん」 -> "Shohei Ohtani"
    - `season`は、ユーザーの質問から年を抽出してください。`season`が指定されていない場合、または「キャリア」や「通算」などの表現があれば、`season`はnullにしてください。
    - `query_type`は "season_batting"、"season_pitching"、 "batting_splits"、または "career_batting" のいずれかを選択してください。
    - `metrics`には、ユーザーが知りたい指標をリスト形式で格納してください。例えば、ホームラン数を知りたい場合は ["homerun"] とします。打率の場合は ["batting_average"] とし、単語と単語の間にアンダースコアを使用してください。
    - `split_type`は、「得点圏（RISP）」「満塁」「ランナー1類」「イニング別」「投手が左投げか右投げか」「球種別」などの特定の状況を示します。該当しない場合はnullにしてください。
    - `pitcher_throws`は、投手の投げ方（右投げまたは左投げ）を示します。右投げはRHP、左投げはLHPとし、該当しない場合はnullにしてください。
    - ユーザーが「主要スタッツ」や「主な成績」のような曖昧な表現を使った場合、metricsには ["main_stats"] というキーワードを一つだけ格納してください。
    - `order_by`には、ランキングの基準となる指標を一つだけ設定してください。
    - `output_format`では、デフォルトは "sentence" です。もしユーザーの質問に『表で』『一覧で』『まとめて』といったような言葉が含まれていたら、output_formatをtableに設定してください。そうでなければsentenceにしてください。

    # JSONスキーマ
    {{
        "query_type": "season_batting" | "season_pitching" | "batting_splits" | "career_batting",
        "metrics": ["string"],
        "split_type": "risp" | "bases_loaded" | "runner_on_1b" | "inning" | "pitcher_throws" | "pitch_type" | null,
        "inning": "integer | null",
        "pitcher_throws": "string | null",
        "pitch_type": ["string"] | null,
        "name": "string | null",
        "season": "integer | null",
        "order_by": "string",
        "limit": "integer | null",
        "output_format": "sentence" | "table"
    }}

    # 質問の例
    質問: 「2023年のホームラン王は誰？」
    JSON: {{ "query_type": "season_batting", "season": 2023, "metrics": ["homerun"],  "order_by": "homerun", "limit": 1 }}

    質問: 「大谷さんの2024年のRISP時の主要スタッツは？」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "risp", "order_by": null, "limit": 1 }}

    質問: 「大谷さんのの2024年の1イニング目のホームラン数とOPSを教えて」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["homerun", "on_base_plus_slugging"], "split_type": "inning", "inning": 1, "order_by": null, "limit": 1 }}

    質問: 「大谷さんの2024年の左投手に対する主要スタッツを一覧で教えて？」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "pitcher_throws", "pitcher_throws": "LHP", "order_by": null, "limit": 1, "output_format": "table" }}

    質問: 「大谷さんの2024年のスライダーに対する主要スタッツは？」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "pitch_type", "pitch_type": "Slider", "order_by": null }}

    質問: 「大谷さんのキャリア主要打撃成績を一覧で教えて」
    JSON: {{ "query_type": "career_batting", "name": "Shohei Ohtani", "metrics": ["main_stats"], "order_by": null, "limit": 1, "output_format": "table" }}

    # 本番
    質問: 「{query}」
    JSON:
    """

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

def _build_dynamic_sql(params: Dict[str, Any]) -> str:
    """
    [ステップ2] 抽出したパラメータを元に、BigQuery用のSQLクエリを構築します。
    """

    # Without query_type and metrics, a query can not be constructed
    query_type = params.get("query_type", [])
    metrics = params.get("metrics", []) # multiple metrics could be stored in the dictionary
    if not query_type or not metrics:
        return None
    
    split_type = params.get("split_type", [])
    
    # Replace keyword from "main_stats" with related column list
    if metrics == ["main_stats"]:
        if query_type == "season_pitching":
            metrics = MAIN_PITCHING_STATS
        elif query_type == "season_batting":
            metrics = MAIN_BATTING_STATS
        elif query_type == "career_batting":
            metrics = MAIN_CAREER_BATTING_STATS
        elif query_type == "batting_splits" and split_type == "risp":
            metrics = MAIN_RISP_BATTING_STATS
        elif query_type == "batting_splits" and split_type == "bases_loaded":
            metrics = MAIN_BASES_LOADED_BATTING_STATS
        elif query_type == "batting_splits" and split_type == "runner_on_1b":
            metrics = MAIN_RUNNER_ON_1B_BATTING_STATS
        elif query_type == "batting_splits" and split_type == "inning":
            metrics = MAIN_INNING_BATTING_STATS
        elif query_type == "batting_splits" and split_type == "pitcher_throws":
            metrics = MAIN_BATTING_BY_PITCHING_THROWS_STATS
        elif query_type == "batting_splits" and split_type == "pitch_type":
            metrics = MAIN_BATTING_BY_PITCH_TYPE_STATS
        # Add another metrics if needed from here

    # Initialize variables
    config = None
    metric_map_key_base = query_type  # Default key for METRIC_MAP

    # Get config info
    if query_type in ["season_batting", "season_pitching", "career_batting"]:
        config = QUERY_TYPE_CONFIG.get(query_type)
    elif query_type == "batting_splits" and params.get("split_type"):
        split_type = params.get("split_type")
        config = QUERY_TYPE_CONFIG.get(query_type, {}).get(split_type)
        metric_map_key_base = f"{query_type}_{split_type}"

    if not config:
        logger.error(f"Configuration not found for query_type: {query_type}")
        return None
    
    table_name = config["table_id"]
    year_column = config["year_col"]
    player_name_col = config["player_col"]
    # default_colsを動的に設定
    if query_type == "career_batting":
        default_cols = [f"{player_name_col} as name", "career_last_team"]
    else:
        default_cols = [f"{player_name_col} as name", f"{year_column} as season"]
    if "team" in config.get("available_metrics", []) or config.get("table_id") in [BATTING_STATS_TABLE_ID, PITCHING_STATS_TABLE_ID]:
        if "team" not in default_cols:
            default_cols.insert(1, "team")

    # METRIC_MAPから安全に値を取得し、Noneを除外
    if query_type == "career_batting":
        queried_metrics = []
        # Group by context first (career, risp, bases_loaded), then by metric type
        for key in ["career", "risp", "bases_loaded"]:
            for metric in metrics:
                metric_mapping = METRIC_MAP.get(metric, {}).get(metric_map_key_base, {}).get(key)
                if metric_mapping:
                    queried_metrics.append(metric_mapping)
    else:
        queried_metrics = [METRIC_MAP.get(metric, {}).get(metric_map_key_base) for metric in metrics]
    # Debugging
    logger.debug(f"Queried metrics for {query_type}: {queried_metrics}")
    # Noneがリストに含まれているとSQL文法エラーになるため、ここでフィルタリング
    valid_queried_metrics = [m for m in queried_metrics if m is not None]

    # SELECT clause
    if split_type == "pitch_type":
        select_cols = default_cols + ["pitch_name"] + [m for m in valid_queried_metrics if m not in ['name', 'team', 'season']]
    else:
        select_cols = default_cols + [m for m in valid_queried_metrics if m not in ['name', 'team', 'season']]
    # Deduplicate
    final_select_cols = list(dict.fromkeys(select_cols))
    select_clause = f"SELECT {', '.join(final_select_cols)}"

    # WHERE clause
    where_condition = []
    if params.get("name"):
        where_condition.append(f"{player_name_col} = '{params['name']}'")
    if params.get("season"):
        where_condition.append(f"{year_column} = {params['season']}")
    if params.get("inning") is not None and split_type == "inning": # condition by inning
        where_condition.append(f"inning = {params['inning']}")
    if params.get("pitcher_throws") and split_type == "pitcher_throws":  # condition by pitcher throws
        where_condition.append(f"p_throws = '{params['pitcher_throws']}'")
    if params.get("pitch_type") and split_type == "pitch_type":  # condition by pitch type
        # if multiple pitch types are provided
        if len(params['pitch_type']) > 1:
            where_condition.append(
                "pitch_name IN ({})".format(
                    ", ".join("'{}'".format(pt) for pt in params['pitch_type'])
                )
            )
        else:
            where_condition.append(f"pitch_name = '{params['pitch_type']}'")
    where_clause = f"WHERE {' AND '.join(where_condition)}" if where_condition else ""

    # GROUP BY clause
    group_by_clause = ""
    if params.get("pitch_type") and split_type == "pitch_type" and len(params['pitch_type']) > 1:
        group_by_clause = f"GROUP BY {', '.join([player_name_col, year_column, 'pitch_name'] + [m for m in valid_queried_metrics if m not in ['name', 'team', 'season']])}"

    # ORDER BY clause
    order_by_clause = ""
    if params.get("order_by"):
        order_by_col = METRIC_MAP.get(params["order_by"], {}).get(metric_map_key_base, params["order_by"])
        order_direction = "ASC" if order_by_col in ("era", "whip", "fip") else "DESC"
        order_by_clause = f"ORDER BY {order_by_col} {order_direction}"

    # LIMIT clause
    if params.get("limit") is not None:
        limit = params.get("limit", 10)
        limit_clause = f"LIMIT {limit}"
    else:
        limit_clause = ""

    return f"{select_clause} FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}` {where_clause} {group_by_clause} {order_by_clause} {limit_clause}"


def _generate_final_response_with_llm(original_query: str, data_df: pd.DataFrame) -> str:
    """
    [ステップ4] 取得したデータと元の質問に基づいて、LLMが自然言語の回答を生成します。
    * ステップ3はBigQueryからデータを取得することです。
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return "AIとの通信に失敗しました。"
    
    data_json_str = data_df.to_json(orient='records', indent=2, force_ascii=False)
    prompt = f"""
    あなたはMLBのデータアナリストです。以下のデータに基づいて、ユーザーの質問に簡潔に日本語で回答してください。
    データは表形式で提示するのではなく、自然な文章で説明してください。

    ---
    ユーザーの質問: {original_query}
    提供データ (JSON形式):
    {data_json_str}
    ---
    回答:
    """
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result.get("candidates"):
            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return generated_text.replace('\n', '<br>')
        return "AIによる回答を生成できませんでした。"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API for final response: {e}", exc_info=True)
        return "AIによる回答生成中にエラーが発生しました。"


def get_ai_response_for_qna_enhanced(query: str, season: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    【打撃リーダーボード特化版】
    ユーザーの"打撃リーダーボード"に関する質問を処理します。
    """
    # Step 1: LLMで質問を解析
    query_params = _parse_query_with_llm(query, season)
    if not query_params:
        logger.warning("Could not extract parameters from the query.")
        return {
            "answer": "質問を理解できませんでした。打撃成績のランキングについて質問してください。（例：2024年のホームラン王は誰？）",
            "isTable": False
        }
    logger.info(f"Parsed query parameters: {query_params}")

    # Step 2: Build SQL
    sql_query = _build_dynamic_sql(query_params)
    if not sql_query:
        logger.warning("Failed to build SQL query.")
        return {
            "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
            "isTable": False
        }
    logger.info(f"Generated SQL query:\n{sql_query}")

    # Step 3: Fetch data from BigQuery
    try:
        # client = get_bq_client()
        results_df = client.query(sql_query).to_dataframe()
        logger.info(f"Fetched {len(results_df)} rows from BigQuery.")
    except GoogleCloudError as e:
        logger.error(f"BigQuery query failed: {e}", exc_info=True)
        return {
            "answer": "データベースからのデータ取得中にエラーが発生しました。",
            "isTable": False
        }

    if results_df.empty:
        return {
            "answer": "関連するデータが見つかりませんでした。",
            "isTable": False
        }
    
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
        
        return {
            "answer": f"以下は{len(results_df)}件の結果です：",
            "isTable": True,
            "isTransposed": is_single_row,
            "tableData": table_data,
            "columns": columns,
            "decimalColumns": [col for col in results_df.columns if col in DECIMAL_FORMAT_COLUMNS],
            "grouping": grouping_info
        }

    # Step 4: Generate final response with LLM
    else:
        logger.info("Generating final response with LLM.")
        final_response = _generate_final_response_with_llm(query, results_df)
        return {
            "answer": final_response,
            "isTable": False
        }
