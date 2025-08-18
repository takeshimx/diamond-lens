from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import os
import json
import numpy as np
import requests
from dotenv import load_dotenv
# from functools import lru_cache
from datetime import datetime
from .bigquery_service import client
# from backend.app.api.schemas import *
import logging
# from backend.app.services.player_service import get_player_details
# from backend.app.services.statcast_service import get_batter_statcast_data

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Manage Google cloud alient with singleton pattern
SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _parse_batting_leaderboard_query_with_llm(query: str, season: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    [ステップ1] LLMを使い、"打撃リーダーボード"に関する質問からパラメータを抽出します。
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return None

    prompt = f"""
    あなたはMLBのデータアナリストです。ユーザーからの"打撃成績のランキング"に関する以下の質問を解析し、
    データベースで検索するためのパラメータをJSON形式で抽出してください。

    # 指示
    - `query_type`は必ず "leaderboard" になります。
    - `season`が指定されていない場合、ユーザーの質問から年を抽出してください。
    - `metrics`には、ユーザーが知りたい打撃指標（例: "hr", "avg", "ops"）を抽出してください。
    - `order_by`には、ランキングの基準となる指標を一つだけ設定してください。
    - `limit`には、ランキングの上位何件を取得したいかを抽出してください。指定がなければ10にしてください。

    # JSONスキーマ
    {{
        "season": "integer | null",
        "metrics": ["string"],
        "query_type": "leaderboard",
        "order_by": "string",
        "limit": "integer"
    }}

    # 質問の例
    質問: 「2023年のホームラン王は誰？」
    JSON: {{ "season": 2023, "metrics": ["hr"], "query_type": "leaderboard", "order_by": "hr", "limit": 1 }}

    質問: 「去年のOPSトップ5の選手を教えて」
    JSON: {{ "season": {datetime.now().year - 1}, "metrics": ["ops"], "query_type": "leaderboard", "order_by": "ops", "limit": 5 }}
    
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

def _build_batting_leaderboard_sql(params: Dict[str, Any]) -> str:
    """
    [ステップ2] 抽出したパラメータを元に、BigQuery用のSQLクエリを構築します。
    """
    
    metrics = params.get("metrics", [])
    if not metrics:
        return None

    table_name = f"`{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`"
    default_cols = ["name", "team", "season"]

    # SELECT clause
    select_cols = default_cols + [m for m in metrics if m not in default_cols]
    select_clause = f"SELECT {', '.join(select_cols)}"

    # WHERE clause
    where_clause = f"WHERE season = {params['season']}" if params.get("season") else ""

    # ORDER BY & LIMIT clause
    order_by_clause = ""
    if params.get("order_by"):
        order_by_clause = f"ORDER BY {params['order_by']} DESC"
    
    limit = params.get("limit", 10)
    limit_clause = f"LIMIT {limit}"

    return f"{select_clause} FROM {table_name} {where_clause} {order_by_clause} {limit_clause}"


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


def get_ai_response_for_qna_enhanced(query: str, season: Optional[int] = None) -> Optional[str]:
    """
    【打撃リーダーボード特化版】
    ユーザーの"打撃リーダーボード"に関する質問を処理します。
    """
    # Step 1: LLMで質問を解析
    query_params = _parse_batting_leaderboard_query_with_llm(query, season)
    if not query_params:
        logger.warning("Could not extract parameters from the query.")
        return "質問を理解できませんでした。打撃成績のランキングについて質問してください。（例：2024年のホームラン王は誰？）"
    logger.info(f"Parsed query parameters: {query_params}")

    # Step 2: Build SQL
    sql_query = _build_batting_leaderboard_sql(query_params)
    if not sql_query:
        logger.warning("Failed to build SQL query.")
        return "この質問に対応するデータの検索クエリを構築できませんでした。"
    logger.info(f"Generated SQL query:\n{sql_query}")

    # Step 3: Fetch data from BigQuery
    try:
        # client = get_bq_client()
        results_df = client.query(sql_query).to_dataframe()
        logger.info(f"Fetched {len(results_df)} rows from BigQuery.")
    except GoogleCloudError as e:
        logger.error(f"BigQuery query failed: {e}", exc_info=True)
        return "データベースからのデータ取得中にエラーが発生しました。"

    if results_df.empty:
        return "関連するデータが見つかりませんでした。"

    # Step 4: Generate final response with LLM
    final_response = _generate_final_response_with_llm(query, results_df)
    return final_response
