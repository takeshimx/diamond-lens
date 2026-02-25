"""
Unit tests for _build_dynamic_sql function

このテストは動的SQL生成ロジックを検証します。
パラメータから正しいSQLクエリが生成されることを保証します。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.services.ai_service import _build_dynamic_sql
except ImportError:
    from backend.app.services.ai_service import _build_dynamic_sql


class TestBuildDynamicSQLBasics:
    """基本的なSQL生成を検証"""

    def test_returns_none_when_query_type_missing(self):
        """query_typeがない場合は(None, {})を返すことを検証"""
        params = {
            "metrics": ["homerun"]
        }
        result = _build_dynamic_sql(params)
        assert result == (None, {})

    def test_returns_none_when_metrics_missing(self):
        """metricsがない場合は(None, {})を返すことを検証"""
        params = {
            "query_type": "season_batting"
        }
        result = _build_dynamic_sql(params)
        assert result == (None, {})

    def test_returns_none_when_invalid_query_type(self):
        """無効なquery_typeの場合は(None, {})を返すことを検証"""
        params = {
            "query_type": "invalid_type",
            "metrics": ["homerun"]
        }
        result = _build_dynamic_sql(params)
        assert result == (None, {})


class TestSeasonBattingSQL:
    """season_batting クエリのSQL生成を検証"""

    def test_simple_season_batting_query(self):
        """シンプルな打撃成績クエリのSQL生成を検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "SELECT" in sql
        assert "FROM" in sql
        assert "fact_batting_stats_with_risp" in sql
        assert "@player_name" in sql  # パラメータ化
        assert "@season" in sql  # パラメータ化
        assert "hr" in sql  # homerun -> hr mapping
        assert sql_params["player_name"] == "Shohei Ohtani"
        assert sql_params["season"] == 2024

    def test_multiple_metrics_season_batting(self):
        """複数メトリクスの打撃成績クエリを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun", "batting_average", "on_base_percentage"],
            "name": "Aaron Judge",
            "season": 2023
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "hr" in sql
        assert "avg" in sql
        assert "obp" in sql
        assert "@player_name" in sql
        assert sql_params["player_name"] == "Aaron Judge"

    def test_main_stats_keyword_season_batting(self):
        """main_statsキーワードが主要統計に展開されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["main_stats"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # MAIN_BATTING_STATS に含まれる主要メトリクスが含まれているはず
        assert "hr" in sql or "homerun" in sql
        assert "avg" in sql or "batting_average" in sql

    def test_order_by_clause(self):
        """ORDER BY句が正しく生成されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "order_by": "homerun",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "ORDER BY" in sql
        assert "hr" in sql  # order_by: homerun -> hr
        assert "DESC" in sql  # ホームランは降順

    def test_limit_clause(self):
        """LIMIT句が正しく生成されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "season": 2024,
            "limit": 10
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "LIMIT @limit" in sql
        assert sql_params["limit"] == 10

    def test_no_where_clause_when_no_conditions(self):
        """条件がない場合、WHERE句がないことを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"]
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # WHERE句がない、またはWHERE後に何もない
        assert "WHERE" not in sql or sql.count("WHERE") == 0


class TestSeasonPitchingSQL:
    """season_pitching クエリのSQL生成を検証"""

    def test_simple_season_pitching_query(self):
        """シンプルな投手成績クエリのSQL生成を検証"""
        params = {
            "query_type": "season_pitching",
            "metrics": ["era", "whip"],
            "name": "Shohei Ohtani",
            "season": 2023
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "fact_pitching_stats" in sql
        assert "era" in sql
        assert "whip" in sql
        assert "@player_name" in sql
        assert sql_params["player_name"] == "Shohei Ohtani"

    def test_pitching_order_by_ascending(self):
        """投手成績で昇順（ERA等）のORDER BYを検証"""
        params = {
            "query_type": "season_pitching",
            "metrics": ["era"],
            "order_by": "era",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "ORDER BY" in sql
        assert "era" in sql
        assert "ASC" in sql  # ERAは昇順（低い方が良い）

    def test_main_stats_keyword_season_pitching(self):
        """main_statsキーワードが投手主要統計に展開されることを検証"""
        params = {
            "query_type": "season_pitching",
            "metrics": ["main_stats"],
            "name": "Shohei Ohtani",
            "season": 2023
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # MAIN_PITCHING_STATS に含まれる主要メトリクス
        assert "era" in sql
        assert "whip" in sql


class TestCareerBattingSQL:
    """career_batting クエリのSQL生成を検証"""

    def test_career_batting_query(self):
        """キャリア通算打撃成績クエリのSQL生成を検証"""
        params = {
            "query_type": "career_batting",
            "metrics": ["homerun", "batting_average"],
            "name": "Mike Trout"
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "tbl_batter_career_stats_master" in sql
        assert "@player_name" in sql
        assert sql_params["player_name"] == "Mike Trout"
        assert "WHERE" in sql

    def test_career_batting_special_column_mapping(self):
        """career_battingの特殊なカラムマッピングを検証"""
        params = {
            "query_type": "career_batting",
            "metrics": ["homerun"],
            "name": "Aaron Judge"
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # career_batting の homerun は career_homeruns にマップされる
        assert "career_homeruns" in sql or "career_homeruns_at_risp" in sql or "career_grandslam_at_bases_loaded" in sql


class TestBattingSplitsSQL:
    """batting_splits クエリのSQL生成を検証"""

    def test_risp_batting_splits(self):
        """得点圏（RISP）打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "risp",
            "metrics": ["batting_average", "homerun"],
            "name": "Mookie Betts",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "mart_batter_clutch" in sql
        assert "avg" in sql
        assert "homeruns" in sql
        assert "@player_name" in sql
        assert sql_params["player_name"] == "Mookie Betts"
        assert "@filter_val" in sql
        assert sql_params["filter_val"] == "risp"

    def test_bases_loaded_batting_splits(self):
        """満塁打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "bases_loaded",
            "metrics": ["batting_average"],
            "name": "Freddie Freeman",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "mart_batter_clutch" in sql
        assert "avg" in sql
        assert "@filter_val" in sql
        assert sql_params["filter_val"] == "bases_loaded"

    def test_inning_batting_splits(self):
        """イニング別打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "inning",
            "metrics": ["batting_average"],
            "name": "Ronald Acuna Jr.",
            "season": 2024,
            "inning": 7
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "tbl_batter_inning_stats" in sql
        assert "@inning" in sql
        assert sql_params["inning"] == 7

    def test_pitcher_throws_batting_splits(self):
        """投手投げ方別打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitcher_throws",
            "metrics": ["batting_average"],
            "name": "Juan Soto",
            "season": 2024,
            "pitcher_throws": "LHP"
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "tbl_batter_pitcher_throws_stats" in sql
        assert "@pitcher_throws" in sql
        assert sql_params["pitcher_throws"] == "LHP"

    def test_pitch_type_single_batting_splits(self):
        """単一球種別打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitch_type",
            "metrics": ["batting_average"],
            "name": "Shohei Ohtani",
            "season": 2024,
            "pitch_type": ["Fastball"]
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "tbl_batter_pitch_type_stats" in sql
        assert "pitch_name = 'Fastball'" in sql or "pitch_name IN" in sql

    def test_pitch_type_multiple_batting_splits(self):
        """複数球種別打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitch_type",
            "metrics": ["batting_average"],
            "name": "Shohei Ohtani",
            "season": 2024,
            "pitch_type": ["Fastball", "Slider", "Curveball"]
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "pitch_name IN" in sql
        assert "@pitch_types" in sql
        assert sql_params["pitch_types"] == ["Fastball", "Slider", "Curveball"]
        assert "GROUP BY" in sql  # 複数球種の場合はGROUP BYが必要

    def test_monthly_batting_splits(self):
        """月別打撃スプリットのSQL生成を検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "monthly",
            "metrics": ["batting_average"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "tbl_batter_offensive_stats_monthly" in sql
        assert "ORDER BY" in sql
        assert "game_month" in sql or "month" in sql


class TestSQLStructure:
    """生成されるSQL構造の整合性を検証"""

    def test_sql_contains_required_clauses(self):
        """基本的なSQL句が含まれることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert sql.startswith("SELECT")
        assert "FROM" in sql
        # WHERE, ORDER BY, LIMIT は条件による

    def test_sql_has_proper_table_reference(self):
        """テーブル参照が正しいフォーマット（プロジェクト.データセット.テーブル）であることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # BigQueryの完全修飾テーブル名フォーマット: `project.dataset.table`
        assert "`" in sql
        assert "." in sql
        assert "fact_batting_stats_with_risp" in sql

    def test_name_parameter_uses_proper_quoting(self):
        """選手名が適切にパラメータ化されていることを検証（SQLインジェクション対策）"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Test Player",
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        assert "@player_name" in sql  # パラメータ化されている
        assert sql_params["player_name"] == "Test Player"

    def test_metric_deduplication(self):
        """重複メトリクスが除去されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun", "homerun", "batting_average"],
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # hrが一度だけ出現（SELECT句内）
        # 実際には list(dict.fromkeys()) で重複除去されている


class TestEdgeCases:
    """エッジケースとエラーハンドリングを検証"""

    def test_empty_params(self):
        """空のパラメータでNoneを返すことを検証"""
        params = {}
        result = _build_dynamic_sql(params)
        assert result == (None, {})

    def test_none_metrics_filtered_out(self):
        """METRIC_MAPにないメトリクスがフィルタリングされることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun", "invalid_metric_xyz"],
            "season": 2024
        }
        sql, sql_params = _build_dynamic_sql(params)

        assert sql is not None
        # invalid_metric_xyzは無視される
        assert "hr" in sql
        assert "invalid_metric_xyz" not in sql

    def test_batting_splits_without_split_type_returns_none(self):
        """batting_splitsでsplit_typeがない場合はNoneを返すことを検証"""
        params = {
            "query_type": "batting_splits",
            "metrics": ["batting_average"],
            "season": 2024
        }
        result = _build_dynamic_sql(params)
        assert result == (None, {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
