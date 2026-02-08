import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cache_service import StatsCache


def test_cache():
    cache = StatsCache()
    
    # テストデータ
    test_data = {"avg": 0.310, "hr": 54, "rbi": 130}
    
    # 保存
    cache.set_player_stats("Shohei Ohtani", 2024, "season_batting", test_data)
    print("✅ データを保存しました")
    
    # 取得
    result = cache.get_player_stats("Shohei Ohtani", 2024, "season_batting")
    print(f"✅ 取得結果: {result}")
    
    # 検証
    if result == test_data:
        print("🎉 テスト成功！")
    else:
        print("❌ テスト失敗")

if __name__ == "__main__":
    test_cache()