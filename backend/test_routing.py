"""
SupervisorAgent のルーティングテスト
BatterAgent と PitcherAgent への振り分けが正しく動作するかを検証
"""
import os
import sys
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from backend.app.services.agents.supervisor_agent import SupervisorAgent

def test_routing():
    """ルーティングのテストケース"""
    supervisor = SupervisorAgent()
    
    test_cases = [
        # Batter (打撃) のテストケース
        ("大谷翔平の2024年のホームラン数は？", "batter"),
        ("2025年の本塁打王は誰？", "batter"),
        ("Shohei Ohtaniの打率を教えて", "batter"),
        ("得点圏打率トップ10を表で見せて", "batter"),
        
        # Pitcher (投手) のテストケース
        ("山本由伸の防御率は？", "pitcher"),
        ("2025年の最多奪三振は誰？", "pitcher"),
        ("Paul Skenesの2024年のWHIPを教えて", "pitcher"),
        ("防御率トップ5を一覧で", "pitcher"),
        
        # Matchup (対戦) のテストケース
        ("大谷翔平 vs ダルビッシュ有の対戦成績", "matchup"),
        ("Shohei Ohtani vs Yu Darvishの相性は？", "matchup"),
    ]
    
    print("=" * 80)
    print("SupervisorAgent ルーティングテスト")
    print("=" * 80)
    print()
    
    results = []
    for query, expected in test_cases:
        actual = supervisor.route_query(query)
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        results.append((query, expected, actual, status))
        
        print(f"{status}")
        print(f"  質問: {query}")
        print(f"  期待: {expected}")
        print(f"  実際: {actual}")
        print()
    
    # サマリー
    print("=" * 80)
    passed = sum(1 for _, _, _, status in results if "PASS" in status)
    total = len(results)
    print(f"結果: {passed}/{total} 件成功 ({passed/total*100:.1f}%)")
    print("=" * 80)
    
    return passed == total

if __name__ == "__main__":
    success = test_routing()
    sys.exit(0 if success else 1)
