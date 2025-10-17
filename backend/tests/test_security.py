"""
SQLインジェクション対策のセキュリティテスト

Phase 1: 入力検証（_validate_query_params）
Phase 2: パラメータ化クエリ（_build_dynamic_sql, _build_dynamic_statcast_sql）

このテストは、SQLインジェクション攻撃を防ぐためのセキュリティ対策を検証します。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.services.ai_service import (
    _validate_query_params,
    _build_dynamic_sql,
    _build_dynamic_statcast_sql
)


class TestValidateQueryParams:
    """Phase 1: _validate_query_params() のテスト"""

    # ========================================
    # 正常系テスト
    # ========================================

    def test_valid_simple_query(self):
        """正常な簡単なクエリを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_name_with_apostrophe(self):
        """アポストロフィを含む正当な選手名を許可"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Mike O'Malley",
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_name_with_hyphen(self):
        """ハイフンを含む正当な選手名を許可"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Jose Martinez-Lopez",
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_name_with_period(self):
        """ピリオドを含む正当な選手名を許可"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Jose Martinez Jr.",
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_multiple_metrics(self):
        """複数のメトリクスを許可"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun", "batting_average", "on_base_percentage"],
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_main_stats_keyword(self):
        """main_statsキーワードを許可"""
        params = {
            "query_type": "season_batting",
            "metrics": ["main_stats"],
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_pitcher_throws(self):
        """正当なpitcher_throwsを許可"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitcher_throws",
            "metrics": ["batting_average"],
            "pitcher_throws": "LHP",
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_inning_single(self):
        """単一イニングを許可"""
        params = {
            "query_type": "batting_splits",
            "split_type": "inning",
            "metrics": ["batting_average"],
            "inning": 7,
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_inning_list(self):
        """イニングのリストを許可"""
        params = {
            "query_type": "batting_splits",
            "split_type": "inning",
            "metrics": ["batting_average"],
            "inning": [7, 8, 9],
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_strikes_and_balls(self):
        """正当なstrikes/ballsを許可"""
        params = {
            "query_type": "batting_splits",
            "split_type": "risp",
            "metrics": ["batting_average"],
            "strikes": 2,
            "balls": 3,
            "season": 2024
        }
        assert _validate_query_params(params) == True

    def test_valid_pitch_types(self):
        """正当な球種リストを許可"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitch_type",
            "metrics": ["batting_average"],
            "pitch_type": ["Fastball", "Slider", "Curveball"],
            "season": 2024
        }
        assert _validate_query_params(params) == True

    # ========================================
    # SQLインジェクション攻撃テスト
    # ========================================

    def test_reject_sql_injection_basic(self):
        """基本的なSQLインジェクション攻撃を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani' OR '1'='1",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_sql_injection_union(self):
        """UNION攻撃を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani' UNION SELECT password FROM users --",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_sql_injection_drop_table(self):
        """DROP TABLE攻撃を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani'; DROP TABLE stats; --",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_sql_injection_comment(self):
        """SQLコメント記号を含む攻撃を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani' -- comment",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_sql_injection_multi_line_comment(self):
        """複数行コメントを含む攻撃を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani' /* comment */ OR '1'='1",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_characters_in_name(self):
        """不正な文字を含む名前を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani<script>alert('xss')</script>",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_semicolon_in_name(self):
        """セミコロンを含む名前を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani; SELECT * FROM users",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_name_too_long(self):
        """異常に長い名前を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "A" * 101,  # 101文字
            "season": 2024
        }
        assert _validate_query_params(params) == False

    # ========================================
    # 型・範囲チェックテスト
    # ========================================

    def test_reject_invalid_season_range(self):
        """無効な年の範囲を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "season": 3000  # 未来すぎる
        }
        assert _validate_query_params(params) == False

    def test_reject_season_too_old(self):
        """古すぎる年を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "season": 1800
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_query_type(self):
        """無効なquery_typeを拒否"""
        params = {
            "query_type": "malicious_type",
            "metrics": ["homerun"],
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_split_type(self):
        """無効なsplit_typeを拒否"""
        params = {
            "query_type": "batting_splits",
            "split_type": "invalid_split",
            "metrics": ["batting_average"],
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_pitcher_throws(self):
        """無効なpitcher_throwsを拒否"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitcher_throws",
            "metrics": ["batting_average"],
            "pitcher_throws": "INVALID",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_inning_range(self):
        """無効なイニング範囲を拒否"""
        params = {
            "query_type": "batting_splits",
            "split_type": "inning",
            "metrics": ["batting_average"],
            "inning": 15,  # 1-9のみ有効
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_strikes_range(self):
        """無効なストライク数を拒否"""
        params = {
            "query_type": "batting_splits",
            "split_type": "risp",
            "metrics": ["batting_average"],
            "strikes": 5,  # 0-3のみ有効
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_balls_range(self):
        """無効なボール数を拒否"""
        params = {
            "query_type": "batting_splits",
            "split_type": "risp",
            "metrics": ["batting_average"],
            "balls": 4,  # 0-3のみ有効
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_limit_range(self):
        """無効なlimit値を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "limit": 10000,  # 1-1000のみ有効
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_output_format(self):
        """無効なoutput_formatを拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "output_format": "invalid_format",
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_metrics_not_list(self):
        """metricsがリストでない場合を拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": "homerun",  # 文字列（リストでない）
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_metric_name(self):
        """METRIC_MAPにないメトリクスを拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["invalid_metric_xyz"],
            "season": 2024
        }
        assert _validate_query_params(params) == False

    def test_reject_invalid_order_by(self):
        """METRIC_MAPにないorder_byを拒否"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "order_by": "invalid_column; DROP TABLE stats; --",
            "season": 2024
        }
        assert _validate_query_params(params) == False


class TestParameterizedQueries:
    """Phase 2: パラメータ化クエリのテスト"""

    def test_build_dynamic_sql_returns_tuple(self):
        """_build_dynamic_sql()がタプルを返すことを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        result = _build_dynamic_sql(params)

        assert isinstance(result, tuple)
        assert len(result) == 2
        sql_query, sql_parameters = result
        assert isinstance(sql_query, str)
        assert isinstance(sql_parameters, dict)

    def test_parameterized_query_uses_placeholders(self):
        """プレースホルダー(@param_name)が使用されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # プレースホルダーがSQL文に含まれる
        assert "@player_name" in sql_query
        assert "@season" in sql_query

        # 実際の値はパラメータ辞書に含まれる
        assert "player_name" in sql_parameters
        assert sql_parameters["player_name"] == "Shohei Ohtani"
        assert "season" in sql_parameters
        assert sql_parameters["season"] == 2024

    def test_parameterized_query_no_direct_value_in_sql(self):
        """SQL文に直接値が埋め込まれていないことを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # 選手名が直接SQL文に含まれていない
        assert "'Shohei Ohtani'" not in sql_query
        # 代わりにプレースホルダー
        assert "@player_name" in sql_query

    def test_parameterized_query_with_limit(self):
        """LIMITもパラメータ化されることを検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "season": 2024,
            "limit": 10
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # LIMITがパラメータ化
        assert "LIMIT @limit" in sql_query
        assert "limit" in sql_parameters
        assert sql_parameters["limit"] == 10

    def test_parameterized_query_with_pitcher_throws(self):
        """pitcher_throwsもパラメータ化されることを検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitcher_throws",
            "metrics": ["batting_average"],
            "pitcher_throws": "LHP",
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        assert "@pitcher_throws" in sql_query
        assert "pitcher_throws" in sql_parameters
        assert sql_parameters["pitcher_throws"] == "LHP"

    def test_parameterized_query_with_pitch_types(self):
        """pitch_type配列がパラメータ化されることを検証"""
        params = {
            "query_type": "batting_splits",
            "split_type": "pitch_type",
            "metrics": ["batting_average"],
            "pitch_type": ["Fastball", "Slider"],
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # 配列パラメータ
        assert "UNNEST(@pitch_types)" in sql_query
        assert "pitch_types" in sql_parameters
        assert sql_parameters["pitch_types"] == ["Fastball", "Slider"]

    def test_order_by_not_parameterized(self):
        """ORDER BYはホワイトリスト方式（パラメータ化しない）を検証"""
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "order_by": "homerun",
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # ORDER BYはパラメータ化されない（ホワイトリスト方式）
        assert "ORDER BY" in sql_query
        assert "hr" in sql_query  # homerun → hr にマップ済み
        # order_byはパラメータ辞書に含まれない
        assert "order_by" not in sql_parameters

    def test_sql_injection_attack_safely_parameterized(self):
        """SQLインジェクション攻撃がパラメータ化で無害化されることを検証"""
        # 注: この攻撃は_validate_query_params()で既にブロックされるが、
        # 万が一通過しても、パラメータ化で無害化されることを確認
        params = {
            "query_type": "season_batting",
            "metrics": ["homerun"],
            "name": "Ohtani' OR '1'='1",
            "season": 2024
        }
        sql_query, sql_parameters = _build_dynamic_sql(params)

        # SQL文にはプレースホルダーのみ
        assert "@player_name" in sql_query
        # 攻撃文字列は値として別途格納
        assert sql_parameters["player_name"] == "Ohtani' OR '1'='1"
        # SQL文に直接埋め込まれていない
        assert "OR '1'='1'" not in sql_query


class TestStatcastParameterizedQueries:
    """statcast master table用のパラメータ化クエリテスト"""

    def test_build_statcast_sql_returns_tuple(self):
        """_build_dynamic_statcast_sql()がタプルを返すことを検証"""
        params = {
            "metrics": ["main_stats"],
            "name": "Shohei Ohtani",
            "season": 2024
        }
        result = _build_dynamic_statcast_sql(params)

        assert isinstance(result, tuple)
        assert len(result) == 2
        sql_query, sql_parameters = result
        assert isinstance(sql_query, str)
        assert isinstance(sql_parameters, dict)

    def test_statcast_parameterized_query_uses_placeholders(self):
        """statcastクエリでプレースホルダーが使用されることを検証"""
        params = {
            "metrics": ["main_stats"],
            "name": "Shohei Ohtani",
            "season": 2024,
            "inning": [7, 8, 9],
            "strikes": 2,
            "balls": 3
        }
        sql_query, sql_parameters = _build_dynamic_statcast_sql(params)

        # プレースホルダー
        assert "@player_name" in sql_query
        assert "@season" in sql_query
        assert "@innings" in sql_query
        assert "@strikes" in sql_query
        assert "@balls" in sql_query

        # パラメータ
        assert sql_parameters["player_name"] == "Shohei Ohtani"
        assert sql_parameters["season"] == 2024
        assert sql_parameters["innings"] == [7, 8, 9]
        assert sql_parameters["strikes"] == 2
        assert sql_parameters["balls"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
