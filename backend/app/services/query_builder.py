"""
BigQuery用のSQLクエリを動的に構築するビルダークラス
パラメータ化クエリを使用してSQLインジェクション対策を実施
"""
import logging
from typing import Dict, Any, Tuple, Optional
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter

from backend.app.config.query_maps import (
    QUERY_TYPE_CONFIG,
    METRIC_MAP,
    MAIN_PITCHING_STATS,
    MAIN_BATTING_STATS,
    MAIN_CAREER_BATTING_STATS,
    MAIN_RISP_BATTING_STATS,
    MAIN_BASES_LOADED_BATTING_STATS,
    MAIN_RUNNER_ON_1B_BATTING_STATS,
    MAIN_INNING_BATTING_STATS,
    MAIN_BATTING_BY_PITCHING_THROWS_STATS,
    MAIN_BATTING_BY_PITCH_TYPE_STATS,
    MAIN_BATTING_BY_GAME_SCORE_SITUATIONS_STATS
)
from backend.app.config.statcast_query import KEY_METRICS_QUERY_SELECT

logger = logging.getLogger(__name__)


class QueryStrategy:
    """クエリ戦略の列挙（Strategy Pattern）"""
    AGGREGATED_TABLE = "aggregated_table"
    STATCAST_MASTER = "statcast_master_table"


class QueryBuilder:
    """BigQueryクエリの構築を担当するクラス"""

    def __init__(self, project_id: str, dataset_id: str):
        """
        Args:
            project_id: GCPプロジェクトID
            dataset_id: BigQueryデータセットID
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
    
    def determine_strategy(self, params: Dict[str, Any]) -> str:
        """
        クエリの複雑さに基づいて戦略を決定
        
        複合条件が2つ以上の場合は statcast master table を使用し、
        単一条件の場合は集約済みテーブルを使用する
        
        Args:
            params: クエリパラメータ
        
        Returns:
            クエリ戦略（"aggregated_table" or "statcast_master_table"）
        """
        complex_conditions = []
        
        # 各種条件をカウント
        if params.get("inning"):
            complex_conditions.append("inning")
        
        if params.get("strikes") is not None:
            complex_conditions.append("strikes")
        
        if params.get("balls") is not None:
            complex_conditions.append("balls")
        
        if params.get("pitcher_throws"):
            complex_conditions.append("pitcher_throws")
        
        if params.get("pitch_type"):
            complex_conditions.append("pitch_type")
        
        # 状況条件
        situational_splits = ["risp", "bases_loaded", "runner_on_1b"]
        if params.get("split_type") in situational_splits:
            complex_conditions.append("situational")
        
        if params.get("game_score"):
            complex_conditions.append("game_score")
        
        condition_count = len(complex_conditions)
        
        # 複数年 + 複合条件は重い可能性がある
        if not params.get("season") and condition_count >= 2:
            logger.warning(
                f"Multi-year query with {condition_count} complex conditions may be slow"
            )
        
        strategy = (
            QueryStrategy.STATCAST_MASTER if condition_count >= 2 
            else QueryStrategy.AGGREGATED_TABLE
        )
        
        logger.info(
            f"Query strategy: {strategy} (condition count: {condition_count})"
        )
        return strategy
    
    def build_query(
        self, 
        params: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        パラメータに基づいてクエリを構築
        
        Args:
            params: クエリパラメータ
        
        Returns:
            (SQL文字列, パラメータ辞書) のタプル
        """
        strategy = self.determine_strategy(params)
        
        if strategy == QueryStrategy.STATCAST_MASTER:
            return self._build_statcast_query(params)
        else:
            return self._build_aggregated_query(params)
    
    def _build_aggregated_query(
        self, 
        params: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        集約済みテーブルに対するクエリを構築
        
        Args:
            params: クエリパラメータ
        
        Returns:
            (SQL文字列, パラメータ辞書)
        """
        query_type = params.get("query_type")
        metrics = params.get("metrics", [])
        
        if not query_type or not metrics:
            logger.error("query_type or metrics is missing")
            return None, {}
        
        split_type = params.get("split_type")
        
        # "main_stats" キーワードを実際のメトリクスリストに展開
        metrics = self._expand_main_stats(metrics, query_type, split_type)
        
        # テーブル設定を取得
        config = self._get_table_config(query_type, split_type)
        if not config:
            logger.error(f"Configuration not found for query_type: {query_type}")
            return None, {}
        
        table_name = config["table_id"]
        year_column = config["year_col"]
        month_column = config.get("month_col")
        player_name_col = config["player_col"]
        
        # SELECT句の構築
        select_clause = self._build_select_clause(
            params, metrics, query_type, split_type, 
            player_name_col, year_column, month_column, config
        )
        
        # WHERE句の構築
        where_clause, query_parameters = self._build_where_clause(
            params, player_name_col, year_column, split_type, config
        )
        
        # GROUP BY句の構築
        group_by_clause = self._build_group_by_clause(
            params, split_type, player_name_col, year_column, metrics, query_type
        )
        
        # ORDER BY句の構築
        order_by_clause = self._build_order_by_clause(
            params, query_type, split_type, month_column
        )
        
        # LIMIT句の構築
        limit_clause = ""
        if params.get("limit") is not None:
            limit_clause = "LIMIT @limit"
            query_parameters["limit"] = params["limit"]
        
        # 最終的なクエリ文字列の組み立て
        query_string = (
            f"{select_clause} "
            f"FROM `{self.project_id}.{self.dataset_id}.{table_name}` "
            f"{where_clause} "
            f"{group_by_clause} "
            f"{order_by_clause} "
            f"{limit_clause}"
        )
        
        logger.info(
            f"✅ Built aggregated query with {len(query_parameters)} parameters"
        )
        return query_string, query_parameters
    
    def _build_statcast_query(
        self, 
        params: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Statcast master tableに対するクエリを構築
        
        Args:
            params: クエリパラメータ
        
        Returns:
            (SQL文字列, パラメータ辞書)
        """
        metrics = params.get("metrics", [])
        if not metrics:
            logger.error("metrics is missing")
            return None, {}
        
        # "main_stats"を展開
        if metrics == ["main_stats"]:
            metrics = MAIN_BATTING_STATS
        
        table_name = "tbl_statcast_2021_2025_master"
        year_column = "game_year"
        player_name_col = "batter_name"
        
        # SELECT句
        if not params.get("season"):
            select_clause = KEY_METRICS_QUERY_SELECT
        else:
            select_clause = KEY_METRICS_QUERY_SELECT + ", game_year"
        
        # WHERE句
        where_conditions = []
        query_parameters = {}
        
        if params.get("name"):
            where_conditions.append(f"{player_name_col} = @player_name")
            query_parameters["player_name"] = params["name"]
        
        if params.get("season"):
            where_conditions.append(f"{year_column} = @season")
            query_parameters["season"] = params["season"]
        
        if params.get("inning"):
            innings = params["inning"]
            if isinstance(innings, list):
                where_conditions.append("inning IN UNNEST(@innings)")
                query_parameters["innings"] = innings
            else:
                where_conditions.append("inning = @inning")
                query_parameters["inning"] = innings
        
        if params.get("pitcher_throws"):
            where_conditions.append("p_throws = @pitcher_throws")
            query_parameters["pitcher_throws"] = params["pitcher_throws"]
        
        if params.get("strikes") is not None:
            where_conditions.append("strikes = @strikes")
            query_parameters["strikes"] = params["strikes"]
        
        if params.get("balls") is not None:
            where_conditions.append("balls = @balls")
            query_parameters["balls"] = params["balls"]
        
        # 状況別の条件
        if params.get("split_type"):
            split_type = params["split_type"]
            if split_type == "risp":
                where_conditions.append("(on_2b != 0 OR on_3b != 0)")
            elif split_type == "bases_loaded":
                where_conditions.append("(on_1b != 0 AND on_2b != 0 AND on_3b != 0)")
            elif split_type == "runner_on_1b":
                where_conditions.append("(on_1b != 0 AND on_2b = 0 AND on_3b = 0)")
        
        # ベースとなるWHERE条件
        where_clause = "WHERE events IS NOT NULL AND game_type = 'R'"
        if where_conditions:
            where_clause += f" AND {' AND '.join(where_conditions)}"
        
        # GROUP BY句
        if params.get("season"):
            group_by_clause = f"GROUP BY {year_column}, {player_name_col}"
        else:
            group_by_clause = f"GROUP BY {player_name_col}"
        
        # ORDER BY句（将来実装予定）
        order_by_clause = ""
        
        # LIMIT句
        limit_clause = ""
        if params.get("limit") is not None:
            limit_clause = "LIMIT @limit"
            query_parameters["limit"] = params["limit"]
        
        query_string = (
            f"{select_clause} "
            f"FROM `{self.project_id}.{self.dataset_id}.{table_name}` "
            f"{where_clause} "
            f"{group_by_clause} "
            f"{order_by_clause} "
            f"{limit_clause}"
        )
        
        logger.info(
            f"✅ Built statcast query with {len(query_parameters)} parameters"
        )
        return query_string, query_parameters
    
    def _expand_main_stats(
        self, 
        metrics: list, 
        query_type: str, 
        split_type: Optional[str]
    ) -> list:
        """
        "main_stats" キーワードを実際のメトリクスリストに展開
        
        Args:
            metrics: メトリクスリスト
            query_type: クエリタイプ
            split_type: 分割タイプ
        
        Returns:
            展開されたメトリクスリスト
        """
        if metrics != ["main_stats"]:
            return metrics
        
        # クエリタイプとsplit_typeに応じて適切なメトリクスリストを選択
        if query_type == "season_pitching":
            return MAIN_PITCHING_STATS
        elif query_type == "season_batting":
            return MAIN_BATTING_STATS
        elif query_type == "career_batting":
            return MAIN_CAREER_BATTING_STATS
        elif query_type == "batting_splits":
            mapping = {
                "risp": MAIN_RISP_BATTING_STATS,
                "bases_loaded": MAIN_BASES_LOADED_BATTING_STATS,
                "runner_on_1b": MAIN_RUNNER_ON_1B_BATTING_STATS,
                "inning": MAIN_INNING_BATTING_STATS,
                "pitcher_throws": MAIN_BATTING_BY_PITCHING_THROWS_STATS,
                "pitch_type": MAIN_BATTING_BY_PITCH_TYPE_STATS,
                "game_score_situation": MAIN_BATTING_BY_GAME_SCORE_SITUATIONS_STATS,
            }
            return mapping.get(split_type, MAIN_BATTING_STATS)
        
        return metrics
    
    def _get_table_config(
        self, 
        query_type: str, 
        split_type: Optional[str]
    ) -> Optional[Dict]:
        """
        クエリタイプとsplit_typeに基づいてテーブル設定を取得
        
        Args:
            query_type: クエリタイプ
            split_type: 分割タイプ
        
        Returns:
            テーブル設定辞書（見つからない場合はNone）
        """
        if query_type in ["season_batting", "season_pitching", "career_batting"]:
            return QUERY_TYPE_CONFIG.get(query_type)
        elif query_type == "batting_splits" and split_type:
            return QUERY_TYPE_CONFIG.get(query_type, {}).get(split_type)
        
        return None
    
    def _build_select_clause(
        self,
        params: Dict[str, Any],
        metrics: list,
        query_type: str,
        split_type: Optional[str],
        player_name_col: str,
        year_column: str,
        month_column: Optional[str],
        config: Dict
    ) -> str:
        """SELECT句を構築"""
        # デフォルトカラムの設定
        if query_type == "career_batting":
            default_cols = [f"{player_name_col} as name", "career_last_team"]
        elif split_type == "monthly" and month_column:
            default_cols = [f"{player_name_col} as name", f"{month_column} as month"]
        else:
            default_cols = [f"{player_name_col} as name", f"{year_column} as season"]
        
        # teamカラムの追加
        available_metrics = config.get("available_metrics", [])
        table_id = config.get("table_id")
        
        from backend.app.services.base import BATTING_STATS_TABLE_ID, PITCHING_STATS_TABLE_ID
        
        if "team" in available_metrics or table_id in [BATTING_STATS_TABLE_ID, PITCHING_STATS_TABLE_ID]:
            if "team" not in default_cols:
                default_cols.insert(1, "team")
        
        # メトリクスのマッピング
        metric_map_key_base = f"{query_type}_{split_type}" if split_type else query_type
        
        if query_type == "career_batting":
            queried_metrics = []
            for key in ["career", "risp", "bases_loaded"]:
                for metric in metrics:
                    metric_mapping = METRIC_MAP.get(metric, {}).get(metric_map_key_base, {}).get(key)
                    if metric_mapping:
                        queried_metrics.append(metric_mapping)
        else:
            queried_metrics = [
                METRIC_MAP.get(metric, {}).get(metric_map_key_base) 
                for metric in metrics
            ]
        
        # Noneを除外
        valid_queried_metrics = [m for m in queried_metrics if m is not None]
        
        # SELECT カラムの構築
        if split_type == "pitch_type":
            select_cols = default_cols + ["pitch_name"] + [
                m for m in valid_queried_metrics if m not in ['name', 'team', 'season']
            ]
        else:
            select_cols = default_cols + [
                m for m in valid_queried_metrics if m not in ['name', 'team', 'season']
            ]
        
        # 重複除去
        final_select_cols = list(dict.fromkeys(select_cols))
        
        return f"SELECT {', '.join(final_select_cols)}"
    
    def _build_where_clause(
        self,
        params: Dict[str, Any],
        player_name_col: str,
        year_column: str,
        split_type: Optional[str],
        config: Dict
    ) -> Tuple[str, Dict[str, Any]]:
        """WHERE句を構築（パラメータ化）"""
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
            where_conditions.append("inning = @inning")
            query_parameters["inning"] = params["inning"]
        
        if params.get("pitcher_throws") and split_type == "pitcher_throws":
            where_conditions.append("p_throws = @pitcher_throws")
            query_parameters["pitcher_throws"] = params["pitcher_throws"]
        
        if params.get("pitch_type") and split_type == "pitch_type":
            where_conditions.append("pitch_name IN UNNEST(@pitch_types)")
            query_parameters["pitch_types"] = params["pitch_type"]
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        return where_clause, query_parameters
    
    def _build_group_by_clause(
        self,
        params: Dict[str, Any],
        split_type: Optional[str],
        player_name_col: str,
        year_column: str,
        metrics: list,
        query_type: str
    ) -> str:
        """GROUP BY句を構築"""
        if params.get("pitch_type") and split_type == "pitch_type" and len(params['pitch_type']) > 1:
            metric_map_key_base = f"{query_type}_{split_type}" if split_type else query_type
            queried_metrics = [
                METRIC_MAP.get(metric, {}).get(metric_map_key_base) 
                for metric in metrics
            ]
            valid_queried_metrics = [m for m in queried_metrics if m is not None]
            
            group_cols = [player_name_col, year_column, 'pitch_name'] + [
                m for m in valid_queried_metrics if m not in ['name', 'team', 'season']
            ]
            return f"GROUP BY {', '.join(group_cols)}"
        
        return ""
    
    def _build_order_by_clause(
        self,
        params: Dict[str, Any],
        query_type: str,
        split_type: Optional[str],
        month_column: Optional[str]
    ) -> str:
        """ORDER BY句を構築"""
        if params.get("order_by"):
            metric_map_key_base = f"{query_type}_{split_type}" if split_type else query_type
            order_by_col = METRIC_MAP.get(params["order_by"], {}).get(metric_map_key_base)
            
            if order_by_col:
                order_direction = "ASC" if order_by_col in ("era", "whip", "fip") else "DESC"
                return f"ORDER BY {order_by_col} {order_direction}"
        
        elif split_type == "monthly" and month_column:
            return f"ORDER BY {month_column} ASC"
        
        return ""
    
    def build_job_config(self, query_parameters: Dict[str, Any]) -> QueryJobConfig:
        """
        BigQuery用のJobConfigを構築
        
        Args:
            query_parameters: パラメータ辞書
        
        Returns:
            QueryJobConfig オブジェクト
        """
        query_parameters_list = []
        
        for key, value in query_parameters.items():
            if isinstance(value, list):
                # 配列の要素の型を判定
                if value and isinstance(value[0], int):
                    param = ArrayQueryParameter(key, "INT64", value)
                else:
                    param = ArrayQueryParameter(key, "STRING", value)
                query_parameters_list.append(param)
                logger.debug(f"Added array parameter: {key} = {value}")
            elif isinstance(value, int):
                param = ScalarQueryParameter(key, "INT64", value)
                query_parameters_list.append(param)
                logger.debug(f"Added scalar parameter: {key} = {value} (INT64)")
            else:
                param = ScalarQueryParameter(key, "STRING", str(value))
                query_parameters_list.append(param)
                logger.debug(f"Added scalar parameter: {key} = {value} (STRING)")
        
        logger.info(f"Total query parameters configured: {len(query_parameters_list)}")
        
        return QueryJobConfig(query_parameters=query_parameters_list)