"""
Diamond Lens MCP Server
MLB統計データへのMCPアクセスを提供
"""
import asyncio
import sys
from pathlib import Path
from typing import List

# プロジェクトルートをPythonパスに追加（インポート前に実行）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# MCP関連のインポート
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server.models import InitializationOptions

# プロジェクト内のインポート（sys.path設定後）
from backend.app.services.ai_service import get_ai_response_with_simple_chart

# MCP server instance
server = Server("diamond-lens-mlb")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """利用可能なMCPツールのリスト"""
    return [
        Tool(
            name="query_player_stats",
            description="MLB選手の打撃・投球成績をBigQueryデータベースから取得。ランキング、月別推移、対戦成績、スプリットデータに対応。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "質問内容（例: '大谷翔平の2025年の打率は？'）"
                    },
                    "season": {
                        "type": "integer",
                        "description": "シーズン年（例: 2025）",
                        "default": 2025
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """MCPツールの実行"""
    if name == "query_player_stats":
        result = get_ai_response_with_simple_chart(
            query=arguments["query"],
            season=arguments.get("season", 2025),
            session_id=None  # MCPでは会話履歴なし
        )

        # レスポンスをテキスト形式で返却
        response_text = f"## {arguments['query']}\n\n"

        # チャートデータがある場合（月別推移など）→ テキストテーブルに変換
        if result.get("isChart") and result.get("chartData"):
            config = result.get("chartConfig", {})
            data_key = config.get("dataKey", "value")
            response_text += f"### {config.get('title', 'チャートデータ')}\n\n"
            
            # チャートデータをマークダウンテーブルに変換
            chart_data = result["chartData"]
            if chart_data:
                keys = list(chart_data[0].keys())
                response_text += "| " + " | ".join(keys) + " |\n"
                response_text += "|" + "|".join(["---"] * len(keys)) + "|\n"
                for row in chart_data:
                    response_text += "| " + " | ".join(str(row.get(k, "")) for k in keys) + " |\n"

        # テーブルデータがある場合
        elif result.get("isTable") and result.get("tableData"):
            response_text += result.get("answer", "") + "\n\n### データ\n"
            # columnsがlist[dict]の場合とlist[str]の場合に対応
            columns = result["columns"]
            if columns and isinstance(columns[0], dict):
                col_keys = [c["key"] for c in columns]
                col_labels = [c["label"] for c in columns]
            else:
                col_keys = columns
                col_labels = columns
            response_text += "| " + " | ".join(col_labels) + " |\n"
            response_text += "|" + "|".join(["---"] * len(col_keys)) + "|\n"
            for row in result["tableData"]:
                response_text += "| " + " | ".join(str(row.get(col, "")) for col in col_keys) + " |\n"

        # 通常のテキストレスポンス
        else:
            response_text += result.get("answer", "データを取得できませんでした。")
        
        return [TextContent(type="text", text=response_text)]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    """MCPサーバーのメインループ"""
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="diamond-lens-mlb",
            server_version="0.1.0",
            capabilities={}
        )
        await server.run(read_stream, write_stream, init_options)

if __name__ == "__main__":
    asyncio.run(main())