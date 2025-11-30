"""
セキュリティテストを直接実行するスクリプト
pytestを使わず、シンプルに実行できます。
"""

import sys
from pathlib import Path

# backendディレクトリをパスに追加
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 環境変数を設定（BigQueryクライアント初期化のため）
import os
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("BIGQUERY_DATASET_ID", "test-dataset")
os.environ.setdefault("GEMINI_API_KEY_V2", "test-key")

# テスト対象の関数をインポート
from app.services.ai_service import _validate_query_params, _build_dynamic_sql, _build_dynamic_statcast_sql

# テスト結果を保存
test_results = []

def run_test(test_name, test_func):
    """テストを実行して結果を記録"""
    try:
        test_func()
        test_results.append(("PASS", test_name))
        print(f"[PASS] {test_name}")
        return True
    except AssertionError as e:
        test_results.append(("FAIL", test_name, str(e)))
        print(f"[FAIL] {test_name}")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        test_results.append(("ERROR", test_name, str(e)))
        print(f"[ERROR] {test_name}")
        print(f"   Exception: {e}")
        return False


print("=" * 80)
print("Phase 1: 入力検証テスト (_validate_query_params)")
print("=" * 80)

# ========================================
# 正常系テスト
# ========================================

def test_valid_simple_query():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Shohei Ohtani",
        "season": 2024
    }
    assert _validate_query_params(params) == True, "正常なクエリが拒否された"

def test_valid_name_with_apostrophe():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Mike O'Malley",
        "season": 2024
    }
    assert _validate_query_params(params) == True, "アポストロフィ付き名前が拒否された"

def test_valid_main_stats():
    params = {
        "query_type": "season_batting",
        "metrics": ["main_stats"],
        "season": 2024
    }
    assert _validate_query_params(params) == True, "main_statsが拒否された"

run_test("正常な簡単なクエリ", test_valid_simple_query)
run_test("アポストロフィを含む名前", test_valid_name_with_apostrophe)
run_test("main_statsキーワード", test_valid_main_stats)

print("\n" + "=" * 80)
print("SQLインジェクション攻撃テスト")
print("=" * 80)

# ========================================
# SQLインジェクション攻撃テスト
# ========================================

def test_reject_sql_injection_basic():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Ohtani' OR '1'='1",
        "season": 2024
    }
    assert _validate_query_params(params) == False, "基本的なSQLインジェクションが通過した"

def test_reject_sql_injection_union():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Ohtani' UNION SELECT password FROM users --",
        "season": 2024
    }
    assert _validate_query_params(params) == False, "UNION攻撃が通過した"

def test_reject_sql_injection_drop_table():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Ohtani'; DROP TABLE stats; --",
        "season": 2024
    }
    assert _validate_query_params(params) == False, "DROP TABLE攻撃が通過した"

def test_reject_invalid_characters():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Ohtani<script>alert('xss')</script>",
        "season": 2024
    }
    assert _validate_query_params(params) == False, "不正な文字が通過した"

def test_reject_name_too_long():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "A" * 101,
        "season": 2024
    }
    assert _validate_query_params(params) == False, "異常に長い名前が通過した"

run_test("基本的なSQLインジェクション", test_reject_sql_injection_basic)
run_test("UNION攻撃", test_reject_sql_injection_union)
run_test("DROP TABLE攻撃", test_reject_sql_injection_drop_table)
run_test("不正な文字を含む名前", test_reject_invalid_characters)
run_test("異常に長い名前", test_reject_name_too_long)

print("\n" + "=" * 80)
print("Phase 2: パラメータ化クエリテスト (_build_dynamic_sql)")
print("=" * 80)

# ========================================
# パラメータ化クエリテスト
# ========================================

def test_returns_tuple():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Shohei Ohtani",
        "season": 2024
    }
    result = _build_dynamic_sql(params)
    assert isinstance(result, tuple), f"タプルを返していない: {type(result)}"
    assert len(result) == 2, f"タプルの長さが2ではない: {len(result)}"

def test_uses_placeholders():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Shohei Ohtani",
        "season": 2024
    }
    sql_query, sql_parameters = _build_dynamic_sql(params)

    assert "@player_name" in sql_query, "プレースホルダー@player_nameがない"
    assert "@season" in sql_query, "プレースホルダー@seasonがない"
    assert "player_name" in sql_parameters, "パラメータplayer_nameがない"
    assert sql_parameters["player_name"] == "Shohei Ohtani", "パラメータの値が正しくない"

def test_no_direct_values_in_sql():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "name": "Shohei Ohtani",
        "season": 2024
    }
    sql_query, sql_parameters = _build_dynamic_sql(params)

    # 選手名が直接埋め込まれていないことを確認
    assert "'Shohei Ohtani'" not in sql_query, "選手名が直接SQL文に埋め込まれている"

def test_limit_parameterized():
    params = {
        "query_type": "season_batting",
        "metrics": ["homerun"],
        "season": 2024,
        "limit": 10
    }
    sql_query, sql_parameters = _build_dynamic_sql(params)

    assert "LIMIT @limit" in sql_query, "LIMITがパラメータ化されていない"
    assert "limit" in sql_parameters, "limitパラメータがない"
    assert sql_parameters["limit"] == 10, "limitの値が正しくない"

def test_pitch_types_array():
    params = {
        "query_type": "batting_splits",
        "split_type": "pitch_type",
        "metrics": ["batting_average"],
        "pitch_type": ["Fastball", "Slider"],
        "season": 2024
    }
    sql_query, sql_parameters = _build_dynamic_sql(params)

    assert "UNNEST(@pitch_types)" in sql_query, "配列パラメータが使用されていない"
    assert "pitch_types" in sql_parameters, "pitch_typesパラメータがない"
    assert sql_parameters["pitch_types"] == ["Fastball", "Slider"], "配列の値が正しくない"

run_test("タプルを返すこと", test_returns_tuple)
run_test("プレースホルダーを使用", test_uses_placeholders)
run_test("直接値が埋め込まれていない", test_no_direct_values_in_sql)
run_test("LIMITのパラメータ化", test_limit_parameterized)
run_test("配列パラメータ（pitch_type）", test_pitch_types_array)

print("\n" + "=" * 80)
print("テスト結果サマリー")
print("=" * 80)

passed = sum(1 for r in test_results if r[0] == "PASS")
failed = sum(1 for r in test_results if r[0] in ["FAIL", "ERROR"])
total = len(test_results)

print(f"合計: {total} テスト")
print(f"成功: {passed} テスト")
print(f"失敗: {failed} テスト")

if failed == 0:
    print("\nすべてのテストが成功しました")
    sys.exit(0)
else:
    print("\n一部のテストが失敗しました")
    sys.exit(1)
