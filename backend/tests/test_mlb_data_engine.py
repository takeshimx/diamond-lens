import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをsys.pathに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from backend.app.services.mlb_data_engine import get_mlb_stats_data

# .envを読み込む
load_dotenv(dotenv_path=project_root / ".env")

def test_engine():
    """
    MLBDataEngineの動作確認テスト
    """
    test_queries = [
        "大谷翔平の2024年のホームラン数は？",
        "2023年の打点王は誰？",
        "アーロン・ジャッジの通算成績を教えて"
    ]

    print("🚀 Starting MLB Data Engine Test...\n")

    for query in test_queries:
        print(f"🔍 Testing Query: '{query}'")
        try:
            result = get_mlb_stats_data(query)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Success!")
                print(f"   - Parsed Params: {result['parameters']}")
                print(f"   - Data Count: {result['data_count']}")
                if result['data']:
                    print(f"   - Sample Data (1st row): {result['data'][0]}")
                else:
                    print("   - No data found.")
            
        except Exception as e:
            print(f"💥 Exception occurred: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_engine()
