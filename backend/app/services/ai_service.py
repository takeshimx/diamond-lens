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
from backend.app.config.query_maps import ( # For Development, add backend. path
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
from backend.app.config.statcast_query import KEY_METRICS_QUERY_SELECT # For Development, add backend. path
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
    - `split_type`は、「得点圏（RISP）」「満塁」「ランナー1類」「イニング別」「投手が左投げか右投げか」「球種別」「ゲームスコア状況別」などの特定の状況を示します。該当しない場合はnullにしてください。
    - `split_type`で、game_score_situation (ゲームスコア状況別) を選択した場合、`game_score`に具体的なスコア状況（例：1点リード、2点ビハインドなど）を示す必要があります。
        例えば、「1点差ゲーム、1点リード、1点ビハインド」は、'one_run_game'、'one_run_lead'、'one_run_trail'のように表現します。4点以上の差は'four_plus_run_lead'や'four_plus_run_trail'としてください。該当しない場合はnullにしてください。
    - `split_type`で、inning (イニング別) を選択した場合、`inning`に具体的なイニング数をリスト形式で示してください。レギュラーイニング数は1~9イニングまで。例：1イニング目なら [1]、7イニング目以降なら [7, 8, 9] とします。
    - `strikes`は、特定のストライク数を指定します。該当しない場合はnullにしてください。`balls`は、特定のボール数を指定します。該当しない場合はnullにしてください。
    - 例えば、「フルカウント」は、 `strikes`を2、`balls`を3としてください。「初球」は、`strikes`を0、`balls`を0とします。該当しない場合はnullにしてください。
    - `pitcher_throws`は、投手の投げ方（右投げまたは左投げ）を示します。右投げはRHP、左投げはLHPとし、該当しない場合はnullにしてください。
    - ユーザーが「主要スタッツ」や「主な成績」のような曖昧な表現を使った場合、metricsには ["main_stats"] というキーワードを一つだけ格納してください。
    - `order_by`には、ランキングの基準となる指標を一つだけ設定してください。
    - `output_format`では、デフォルトは "sentence" です。もしユーザーの質問に『表で』『一覧で』『まとめて』といったような言葉が含まれていたら、output_formatをtableに設定してください。そうでなければsentenceにしてください。

    # JSONスキーマ
    {{
        "query_type": "season_batting" | "season_pitching" | "batting_splits" | "career_batting" | null,
        "metrics": ["string"],
        "split_type": "risp" | "bases_loaded" | "runner_on_1b" | "inning" | "pitcher_throws" | "pitch_type" | "game_score_situation" | "monthly" | null,
        "inning": ["integer"] | null,
        "strikes": "integer | null",
        "balls": "integer | null",
        "game_score": "string | null",
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

    質問: 「大谷さんの2024年の、1点ビハインドでの主要スタッツは？」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "game_score_situation", "game_score": "one_run_trail", "order_by": null, "limit": 1 }}

    質問: 「大谷さんの2024年の打率を月毎の推移をチャートで教えて」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["batting_average"], "split_type": "monthly", "order_by": null }}

    # 複合質問の例
    質問: 「大谷さんの2024年の7イニング目以降、フルカウントでの、RISP時の主要スタッツは？」
    JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "risp", "inning": [7, 8, 9], "strikes": 2, "balls": 3, "order_by": null, "limit": 1 }}

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


# Helper function to determine query strategy (using a simple query or more complex one)
def _determine_query_strategy(params: Dict[str, Any]) -> str:
    """
    クエリの複雑さに基づいて戦略を決定する
    - 複合条件が2つ以上: statcast master table
    - 単一条件: aggregated table
    - パフォーマンス重視が必要な場合の特別処理も含む
    """

    complex_conditions = []

    # イニング条件
    if params.get("inning"):
        complex_conditions.append("inning")
    
    # カウント条件
    if params.get("strikes") is not None:
        complex_conditions.append("strikes")
    if params.get("balls") is not None:
        complex_conditions.append("balls")
    
    # 投手タイプ条件
    if params.get("pitcher_throws"):
        complex_conditions.append("pitcher_throws")
    
    # 球種条件
    if params.get("pitch_type"):
        complex_conditions.append("pitch_type")
    
    # 状況条件
    situational_splits = ["risp", "bases_loaded", "runner_on_1b"]
    if params.get("split_type") in situational_splits:
        complex_conditions.append("situational")
    
    # ゲームスコア状況条件
    if params.get("game_score"):
        complex_conditions.append("game_score")
    
    # 複合条件の判定
    condition_count = len(complex_conditions)

    # 特別なケース：複数年データ + 複合条件は重すぎる可能性
    if not params.get("season") and condition_count >= 2:
        logger.warning(f"Multi-year query with {condition_count} complex conditions may be slow")

    strategy = "statcast_master_table" if condition_count >= 2 else "aggregated_table"

    logger.info(f"Query strategy: {strategy} based on condition count: {condition_count}")
    return strategy


# Helper function to build dynamic SQL queries with statcast_master_table
def _build_dynamic_statcast_sql(params: Dict[str, Any]) -> str:
    """
    Build a SQL query for the statcast_master_table based on the provided parameters.
    """

    metrics = params.get("metrics", [])
    if not metrics:
        return None
    
    # Replace keyword from "main_stats" with related column list
    if metrics == ["main_stats"]:
        metrics = MAIN_BATTING_STATS # tentative
    
    table_name = "tbl_statcast_2021_2025_master"
    year_column = "game_year"
    player_name_col = "batter_name"

    
    # static query part
    # SELECT clause
    # if all seasons
    if not params.get("season"):
        select_clause = KEY_METRICS_QUERY_SELECT
    else:
        select_clause = KEY_METRICS_QUERY_SELECT + ", game_year"

    # dynamic query part
    # WHERE clause
    where_condition = []
    if params.get("name"):
        where_condition.append(f"{player_name_col} = '{params['name']}'")
    if params.get("season"):
        where_condition.append(f"{year_column} = {params['season']}")
    if params.get("inning"):
        # Ensure inning is a list of integers, then join as comma-separated string
        innings = params['inning']
        if isinstance(innings, list):
            inning_list = ", ".join(str(int(i)) for i in innings)
            where_condition.append(f"inning IN ({inning_list})")
        else:
            where_condition.append(f"inning = {int(innings)}")
    if params.get('pitch_throws'):
        where_condition.append(f"p_throws = {params['pitch_throws']}")
    if params.get("strikes"):
        where_condition.append(f"strikes = {params['strikes']}")
    if params.get("balls"):
        where_condition.append(f"balls = {params['balls']}")
    if params.get('split_type'):
        if params['split_type'] == 'risp':
            where_condition.append("(on_2b != 0 OR on_3b != 0)")
        if params['split_type'] == 'bases_loaded':
            where_condition.append("(on_1b != 0 AND on_2b != 0 AND on_3b != 0)")
        if params['split_type'] == 'runner_on_1b':
            where_condition.append("(on_1b != 0 AND on_2b = 0 AND on_3b = 0)")
    # if params.get('game_score'): # At this point, data source is not accurate due to incorrect logic. To be fixed.
    #     pass

    where_clause = f"WHERE events IS NOT NULL AND game_type = 'R' AND {' AND '.join(where_condition)}" if where_condition else ""

    # GROUP BY clause # all seasons can be selected, to be updated
    if params.get("season"):
        group_by_clause = f"GROUP BY {year_column}, {player_name_col}"
    else:
        group_by_clause = f"GROUP BY {player_name_col}"

    # ORDER BY clause # To be implmented later
    order_by_clause = ""
    # if params.get("order_by"):
    #     order_by_clause = f"ORDER BY {params['order_by']}"
    #     order_direction = "ASC" if order_by_col in ("era", "whip", "fip") else "DESC"
    #     order_by_clause = f"ORDER BY {order_by_col} {order_direction}"

    # LIMIT clause
    if params.get("limit") is not None:
        limit = params.get("limit", 10)
        limit_clause = f"LIMIT {limit}"
    else:
        limit_clause = ""
    
    return f"{select_clause} FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}` {where_clause} {group_by_clause} {order_by_clause} {limit_clause}"
        
 

# Helper function to build dynamic SQL queries with aggregated table
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
        elif query_type == "batting_splits" and split_type == "game_score_situation":
            metrics = MAIN_BATTING_BY_GAME_SCORE_SITUATIONS_STATS
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
    month_column = config.get("month_col", None)
    player_name_col = config["player_col"]
    # default_colsを動的に設定
    if query_type == "career_batting":
        default_cols = [f"{player_name_col} as name", "career_last_team"]
    elif split_type == "monthly" and month_column:
        default_cols = [f"{player_name_col} as name", f"{month_column} as month"]
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
            # リストの最初の要素を取得
            where_condition.append(f"pitch_name = '{params['pitch_type'][0]}'")
    
    # At this point, data source is not accurate due to incorrect logic. To be fixed.
    # if params.get("game_score") and split_type == "game_score_situation":  # condition by game score situation
    #     mapping = {
    #         'one_run_game':      "game_score_situation IN ('1-run lead', '1-run trail')",
    #         'one_run_lead':      "game_score_situation = '1-run lead'",
    #         'one_run_trail':     "game_score_situation = '1-run trail'",
    #         'two_run_game':      "game_score_situation IN ('2-run lead', '2-run trail')",
    #         'two_run_lead':      "game_score_situation = '2-run lead'",
    #         'two_run_trail':     "game_score_situation = '2-run trail'",
    #         'three_run_game':    "game_score_situation IN ('3-run lead', '3-run trail')",
    #         'three_run_lead':    "game_score_situation = '3-run lead'",
    #         'three_run_trail':   "game_score_situation = '3-run trail'",
    #         'four_plus_run_game':"game_score_situation IN ('4+ run lead', '4+ run trail')",
    #         'four_plus_run_lead':"game_score_situation = '4+ run lead'",
    #         'four_plus_run_trail':"game_score_situation = '4+ run trail'",
    #         'tie_game':          "game_score_situation = 'Tie game'",
    #     }
    #     condition = mapping.get(params['game_score'])
    #     if condition:
    #         where_condition.append(condition)
    #     else:
    #         logger.warning(f"Unknown game_score parameter: {params['game_score']}")


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
    elif split_type == "monthly" and month_column:
        order_by_clause = f"ORDER BY {month_column} ASC"

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
    query_strategy = _determine_query_strategy(query_params)
    logger.info(f"Using query strategy: {query_strategy}")

    if query_strategy == "aggregated_table":
        # Using aggregated table
        sql_query = _build_dynamic_sql(query_params)
        if not sql_query:
            logger.warning("Failed to build SQL query.")
            return {
                "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
                "isTable": False
            }
        logger.info(f"Generated SQL query:\n{sql_query}")
    
    else: # Using statcast master table
        sql_query = _build_dynamic_statcast_sql(query_params)
        if not sql_query:
            logger.warning("Failed to build SQL query with statcast master table.")
            return {
                "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
                "isTable": False
            }
        logger.info(f"Generated SQL query (strategy: {query_strategy}):\n{sql_query}")

    # Step 3: Fetch data from BigQuery
    try:
        query_start = datetime.now()
        results_df = client.query(sql_query).to_dataframe()
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


def get_ai_response_with_simple_chart(query: str, season: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """既存関数を拡張してシンプルチャート対応"""
    
    # Just call the existing function for now - we'll integrate chart logic directly into it
    return get_ai_response_for_qna_enhanced(query, season)