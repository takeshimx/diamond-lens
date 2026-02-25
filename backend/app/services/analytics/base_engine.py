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
import logging

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



class BaseEngine:
    """
    Namespace for common utility functions for analytics engines.
    """
    @staticmethod
    def validate_query_params(params: Dict[str, Any]) -> bool:
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

        # 1. 選手名の検証
        if params.get("name"):
            name = params["name"]

            # 英字、スペース、ピリオド、ハイフン、アポストロフィのみ許可
            # 例: "Shohei Ohtani", "Mike O'Malley", "Jose Martinez Jr."
            if not re.match(r"^[A-Za-z\s\.\-']+$", name):
                logger.warning(f"⚠️ Invalid name format detected: {name}")
                return False

            # 長さ制限（100文字以上は異常）
            if len(name) > 100:
                logger.warning(f"⚠️ Name too long: {len(name)} characters")
                return False

            # SQLキーワードの検出（基本的な攻撃パターン）
            sql_keywords = [
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
                'ALTER', 'UNION', 'WHERE', 'OR', 'AND', '--', '/*', '*/',
                'EXEC', 'EXECUTE', 'SCRIPT', 'JAVASCRIPT', 'EVAL'
            ]
            name_upper = name.upper()
            for keyword in sql_keywords:
                if keyword in name_upper:
                    logger.warning(f"⚠️ SQL keyword detected in name: {name}")
                    return False

        # 2. Seasonの検証
        if params.get("season") is not None:
            season = params["season"]

            # 整数型チェック
            if not isinstance(season, int):
                logger.warning(f"⚠️ Season must be integer: {season}")
                return False

            # 妥当な年の範囲
            if not (1900 <= season <= 2100):
                logger.warning(f"⚠️ Invalid season range: {season}")
                return False

        # 3. query_typeの検証（ホワイトリスト）
        if params.get("query_type"):
            valid_query_types = ["season_batting", "season_pitching", "batting_splits", "career_batting"]
            if params["query_type"] not in valid_query_types:
                logger.warning(f"⚠️ Invalid query_type: {params['query_type']}")
                return False

        # 4. split_typeの検証（ホワイトリスト）
        if params.get("split_type"):
            valid_split_types = [
                "risp", "bases_loaded", "runner_on_1b", "inning",
                "pitcher_throws", "pitch_type", "game_score_situation", "monthly"
            ]
            if params["split_type"] not in valid_split_types:
                logger.warning(f"⚠️ Invalid split_type: {params['split_type']}")
                return False

        # 5. metricsの検証
        if params.get("metrics"):
            metrics = params["metrics"]

            # リスト型チェック
            if not isinstance(metrics, list):
                logger.warning(f"⚠️ Metrics must be list: {metrics}")
                return False

            # "main_stats"は特殊キーワードなので許可
            if metrics != ["main_stats"]:
                # 各メトリックがMETRIC_MAPに存在するかチェック
                for metric in metrics:
                    if metric not in METRIC_MAP and metric != "main_stats":
                        logger.warning(f"⚠️ Invalid metric: {metric}")
                        return False

        # 6. order_byの検証
        if params.get("order_by"):
            order_by = params["order_by"]

            # METRIC_MAPに存在するかチェック
            if order_by not in METRIC_MAP:
                logger.warning(f"⚠️ Invalid order_by: {order_by}")
                return False

        # 7. pitcher_throwsの検証
        if params.get("pitcher_throws"):
            pitcher_throws = params["pitcher_throws"]

            # RHPまたはLHPのみ許可
            if pitcher_throws not in ["RHP", "LHP"]:
                logger.warning(f"⚠️ Invalid pitcher_throws: {pitcher_throws}")
                return False

        # 8. inningの検証
        if params.get("inning") is not None:
            inning = params["inning"]

            # リストまたは整数
            if isinstance(inning, list):
                for inn in inning:
                    if not isinstance(inn, int) or not (1 <= inn <= 9):
                        logger.warning(f"⚠️ Invalid inning in list: {inn}")
                        return False
            elif isinstance(inning, int):
                if not (1 <= inning <= 9):
                    logger.warning(f"⚠️ Invalid inning: {inning}")
                    return False
            else:
                logger.warning(f"⚠️ Inning must be int or list: {inning}")
                return False

        # 9. strikes/ballsの検証
        if params.get("strikes") is not None:
            strikes = params["strikes"]
            if not isinstance(strikes, int) or not (0 <= strikes <= 3):
                logger.warning(f"⚠️ Invalid strikes: {strikes}")
                return False

        if params.get("balls") is not None:
            balls = params["balls"]
            if not isinstance(balls, int) or not (0 <= balls <= 3):
                logger.warning(f"⚠️ Invalid balls: {balls}")
                return False

        # 10. pitch_typeの検証
        if params.get("pitch_type"):
            pitch_types = params["pitch_type"]

            # リスト型チェック
            if not isinstance(pitch_types, list):
                logger.warning(f"⚠️ pitch_type must be list: {pitch_types}")
                return False

            # 各球種が妥当な文字列かチェック（英字、スペース、ハイフンのみ）
            for pt in pitch_types:
                if not isinstance(pt, str) or not re.match(r"^[A-Za-z\s\-]+$", pt):
                    logger.warning(f"⚠️ Invalid pitch_type: {pt}")
                    return False

                # 長さ制限
                if len(pt) > 50:
                    logger.warning(f"⚠️ pitch_type too long: {pt}")
                    return False

        # 11. game_scoreの検証
        if params.get("game_score"):
            valid_game_scores = [
                'one_run_game', 'one_run_lead', 'one_run_trail',
                'two_run_game', 'two_run_lead', 'two_run_trail',
                'three_run_game', 'three_run_lead', 'three_run_trail',
                'four_plus_run_game', 'four_plus_run_lead', 'four_plus_run_trail',
                'tie_game'
            ]
            if params["game_score"] not in valid_game_scores:
                logger.warning(f"⚠️ Invalid game_score: {params['game_score']}")
                return False

        # 12. limitの検証
        if params.get("limit") is not None:
            limit = params["limit"]

            # 整数型チェック
            if not isinstance(limit, int):
                logger.warning(f"⚠️ limit must be integer: {limit}")
                return False

            # 妥当な範囲（1-1000）
            if not (1 <= limit <= 1000):
                logger.warning(f"⚠️ Invalid limit range: {limit}")
                return False

        # 13. output_formatの検証
        if params.get("output_format"):
            if params["output_format"] not in ["sentence", "table"]:
                logger.warning(f"⚠️ Invalid output_format: {params['output_format']}")
                return False

        logger.info("✅ Query parameters validation passed")
        return True
    

    # Helper function to determine query strategy (using a simple query or more complex one)
    @staticmethod
    def determine_query_strategy(params: Dict[str, Any]) -> str:
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
    @staticmethod
    def build_dynamic_statcast_sql(params: Dict[str, Any]) -> tuple[str, dict]:
        """
        statcast_master_tableに対するパラメータ化クエリを構築します。

        Args:
            params: LLMから抽出されたクエリパラメータ

        Returns:
            tuple[str, dict]: (SQL文字列, パラメータ辞書)
        """

        metrics = params.get("metrics", [])
        if not metrics:
            return None, {}
        
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

        # dynamic query part - パラメータ化クエリを使用
        # WHERE clause
        where_conditions = []
        query_parameters = {}

        if params.get("name"):
            where_conditions.append(f"{player_name_col} = @player_name")
            query_parameters["player_name"] = params["name"]

        if params.get("season"):
            where_conditions.append(f"{year_column} = @season")
            query_parameters["season"] = params["season"]

        if params.get("inning"):
            innings = params['inning']
            if isinstance(innings, list):
                where_conditions.append(f"inning IN UNNEST(@innings)")
                query_parameters["innings"] = innings
            else:
                where_conditions.append(f"inning = @inning")
                query_parameters["inning"] = innings

        if params.get('pitcher_throws'):
            where_conditions.append(f"p_throws = @pitcher_throws")
            query_parameters["pitcher_throws"] = params['pitcher_throws']

        if params.get("strikes") is not None:
            where_conditions.append(f"strikes = @strikes")
            query_parameters["strikes"] = params["strikes"]

        if params.get("balls") is not None:
            where_conditions.append(f"balls = @balls")
            query_parameters["balls"] = params["balls"]

        if params.get('split_type'):
            if params['split_type'] == 'risp':
                where_conditions.append("(on_2b != 0 OR on_3b != 0)")
            elif params['split_type'] == 'bases_loaded':
                where_conditions.append("(on_1b != 0 AND on_2b != 0 AND on_3b != 0)")
            elif params['split_type'] == 'runner_on_1b':
                where_conditions.append("(on_1b != 0 AND on_2b = 0 AND on_3b = 0)")

        where_clause = f"WHERE events IS NOT NULL AND game_type = 'R'"
        if where_conditions:
            where_clause += f" AND {' AND '.join(where_conditions)}"

        # GROUP BY clause # all seasons can be selected, to be updated
        if params.get("season"):
            group_by_clause = f"GROUP BY {year_column}, {player_name_col}"
        else:
            group_by_clause = f"GROUP BY {player_name_col}"

        # ORDER BY clause # To be implemented later
        order_by_clause = ""

        # LIMIT clause - パラメータ化
        limit_clause = ""
        if params.get("limit") is not None:
            limit_clause = f"LIMIT @limit"
            query_parameters["limit"] = params["limit"]

        query_string = f"{select_clause} FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}` {where_clause} {group_by_clause} {order_by_clause} {limit_clause}"

        logger.info(f"✅ Built parameterized statcast query with {len(query_parameters)} parameters")
        return query_string, query_parameters
            
    

    # Helper function to build dynamic SQL queries with aggregated table
    @staticmethod
    def build_dynamic_sql(params: Dict[str, Any]) -> tuple[str, dict]:
        """
        [ステップ2] 抽出したパラメータを元に、BigQuery用のパラメータ化クエリを構築します。

        Args:
            params: LLMから抽出されたクエリパラメータ

        Returns:
            tuple[str, dict]: (SQL文字列, パラメータ辞書)
            - SQL文字列: プレースホルダー（@param_name）を含むクエリ
            - パラメータ辞書: プレースホルダーに対応する実際の値
        """

        # Without query_type and metrics, a query can not be constructed
        query_type = params.get("query_type", [])
        metrics = params.get("metrics", []) # multiple metrics could be stored in the dictionary
        if not query_type or not metrics:
            return None, {}
        
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
            return None, {}
        
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

        # WHERE clause - パラメータ化クエリを使用
        where_conditions = []
        query_parameters = {}

        if params.get("name"):
            where_conditions.append(f"{player_name_col} = @player_name")
            query_parameters["player_name"] = params["name"]

        if params.get("season"):
            where_conditions.append(f"{year_column} = @season")
            query_parameters["season"] = params["season"]
        
        if config.get("filter_col") and config.get("filter_val"):
            where_conditions.append(f"{config['filter_col']} = @filter_val")
            query_parameters["filter_val"] = config["filter_val"]

        if params.get("inning") is not None and split_type == "inning":
            where_conditions.append(f"inning = @inning")
            query_parameters["inning"] = params["inning"]

        if params.get("pitcher_throws") and split_type == "pitcher_throws":
            where_conditions.append(f"p_throws = @pitcher_throws")
            query_parameters["pitcher_throws"] = params["pitcher_throws"]

        if params.get("pitch_type") and split_type == "pitch_type":
            # BigQueryの配列パラメータを使用してIN句を安全に構築
            where_conditions.append(f"pitch_name IN UNNEST(@pitch_types)")
            query_parameters["pitch_types"] = params["pitch_type"]

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # GROUP BY clause
        group_by_clause = ""
        if params.get("pitch_type") and split_type == "pitch_type" and len(params['pitch_type']) > 1:
            group_by_clause = f"GROUP BY {', '.join([player_name_col, year_column, 'pitch_name'] + [m for m in valid_queried_metrics if m not in ['name', 'team', 'season']])}"

        # ORDER BY clause - ホワイトリスト方式（パラメータ化不可）
        order_by_clause = ""
        if params.get("order_by"):
            # METRIC_MAPに存在する場合のみ使用（_validate_query_paramsで検証済み）
            order_by_col = METRIC_MAP.get(params["order_by"], {}).get(metric_map_key_base)
            if order_by_col:
                order_direction = "ASC" if order_by_col in ("era", "whip", "fip") else "DESC"
                order_by_clause = f"ORDER BY {order_by_col} {order_direction}"
        elif split_type == "monthly" and month_column:
            order_by_clause = f"ORDER BY {month_column} ASC"

        # LIMIT clause - パラメータ化
        limit_clause = ""
        if params.get("limit") is not None:
            limit_clause = f"LIMIT @limit"
            query_parameters["limit"] = params["limit"]

        query_string = f"{select_clause} FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}` {where_clause} {group_by_clause} {order_by_clause} {limit_clause}"

        logger.info(f"✅ Built parameterized query with {len(query_parameters)} parameters")
        return query_string, query_parameters
    

    @staticmethod
    def generate_final_response_with_llm(original_query: str, data_df: pd.DataFrame) -> str:
        """
        [ステップ4] 取得したデータと元の質問に基づいて、LLMが自然言語の回答を生成します。
        * ステップ3はBigQueryからデータを取得することです。
        """
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY_V2 is not set.")
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