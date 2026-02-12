# backend/verify_refactor.py

# ai_service.py から既存の「関数」をインポート
from app.services.ai_service import (
    _validate_query_params,
    _determine_query_strategy,
    _build_dynamic_sql
)
# base_engine.py から新設した「クラスのスタティックメソッド」をインポート
from app.services.analytics.base_engine import BaseEngine

# テスト用パラメータ
test_params = {
    "name": "Shohei Ohtani",
    "season": 2024,
    "query_type": "season_batting",
    "metrics": ["homerun", "batting_average"]
}

print("--- 1. Validation Test ---")
old_val = _validate_query_params(test_params)
new_val = BaseEngine.validate_query_params(test_params)
print(f"Old: {old_val}, New: {new_val}")
assert old_val == new_val
print("✅ Validation OK")

print("\n--- 2. Strategy Test ---")
old_strat = _determine_query_strategy(test_params)
new_strat = BaseEngine.determine_query_strategy(test_params)
print(f"Old: {old_strat}, New: {new_strat}")
assert old_strat == new_strat
print("✅ Strategy OK")

print("\n--- 3. SQL Construction Test ---")
old_sql, old_params = _build_dynamic_sql(test_params)
new_sql, new_params = BaseEngine.build_dynamic_sql(test_params)

# SQL文字列の比較（念のため空白をトリム）
assert old_sql.strip() == new_sql.strip()
assert old_params == new_params
print("✅ SQL Construction OK")
print(f"Generated SQL: {new_sql[:100]}...")

print("\n🎉 All refactored functions are verified successfully!")