# backend/tests/test_ai_agent.py

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from backend.app.services.ai_agent_service import run_mlb_agent

# .env を読み込む（APIキーなどの取得用）
load_dotenv(dotenv_path=project_root / ".env")

def test_agent_run():
    """
    LangGraphエージェントの基本動作テスト
    """
    print("🤖 Starting MLB Agent Test...")
    
    # テストクエリ（比較質問：複数ステップが必要）
    query = "2024年の大谷翔平とアーロン・ジャッジのホームラン数を比較して"
    
    print(f"❓ User Query: {query}")
    print("-" * 30)
    
    try:
        # エージェントを実行
        # 内部で Planner -> Executor -> Synthesizer が回ります
        answer = run_mlb_agent(query)
        
        print("\n✨ Agent's Final Answer:")
        print(answer)
        
    except Exception as e:
        print(f"❌ Error during agent execution: {e}")

if __name__ == "__main__":
    test_agent_run()