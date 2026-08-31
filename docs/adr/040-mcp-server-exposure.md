# ADR-040: MCP サーバーで外部 AI クライアント（Claude Desktop / Cursor）に統計取得を公開する

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

Diamond Lens の MLB 統計取得能力は、自前の Web UI / REST API からしか使えませんでした。一方、ユーザーが日常的に使う AI クライアント（Claude Desktop、Cursor 等）から「大谷翔平の 2025 年の打率は？」と直接聞いて、Diamond Lens のデータで答えられると価値が高い。

これを実現する標準的な手段が **MCP（Model Context Protocol）** です。MCP は「外部の AI クライアントが、ツール（関数）を持つサーバーに接続し、AI がそのツールを呼び出す」ためのオープンな規格でございます。これに対応すれば、Diamond Lens を**任意の MCP 対応クライアントから呼べるツール提供サーバー**として公開できます。

対象 JD（GenAI Forward Deployed Engineer, Google Cloud）は **MCP servers** を明示的に名指ししており、この対応は要件への直接的な裏付けにもなります。

## Decision（決定）

Diamond Lens を **MCP サーバーとして公開**しました（[backend/mcp_server.py](../../backend/mcp_server.py)）。

- `mcp` ライブラリの `Server` を `stdio_server`（標準入出力トランスポート）で起動し、Claude Desktop / Cursor 等のローカル MCP クライアントから接続可能にする。
- ツール `query_player_stats`（query / season を引数に取る）を 1 つ公開。`inputSchema` で引数スキーマを宣言し、AI クライアント側がこのスキーマを見て呼び出す。
- ツールの実体は、既存のチャット応答ロジック `get_ai_response_with_simple_chart` を**再利用**。MCP 専用に分析ロジックを再実装せず、既存資産の薄いラッパーに徹する。
- 戻り値は MCP の `TextContent` として返す。チャート/テーブル結果は Markdown テーブルに変換し、AI クライアント上で読める形に整形する。

## Alternatives Considered（検討した代替案）

- **自前 REST API のみで公開**: 外部 AI クライアントから使うには、各クライアントごとに独自連携を書く必要があり、汎用性がない。MCP という業界標準に乗ることで「1 実装で MCP 対応クライアント全部から使える」利点を取る。
- **MCP ツールを新規に作り込む**: 分析ロジックを MCP 用に再実装すると二重メンテになる。既存 `get_ai_response_with_simple_chart` のラッパーにして DRY を保つ方を採用。
- **HTTP/SSE トランスポートで公開**: ローカルの Claude Desktop / Cursor 連携が主目的のため、まずは `stdio` トランスポートで足りる。リモート公開が必要になった段階で HTTP 化を検討する（現状は stdio）。

## Consequences（結果・トレードオフ）

**良くなったこと**

- Claude Desktop / Cursor 等から、Diamond Lens の MLB データを会話で直接引ける。プロダクトのリーチが自前 UI の外へ広がる。
- 既存ロジックのラッパーなので実装・保守コストが小さい。
- JD が名指しする MCP server 対応の実物を提示できる。

**悪くなったこと / 新たな負荷**

- 公開ツールが `query_player_stats` 1 つに限られ、戦略レポート等の高度機能は MCP からは未公開。
- ツール実体が **旧経路 `get_ai_response_with_simple_chart`（`ai_service.py`）に依存**しており、`ChatOrchestrator`（[[010-chat-orchestrator-replaces-langgraph]]）への一本化からは外れている。チャット本体のリファクタに MCP 経路が追従していない点が技術的負債。
- `stdio` トランスポートのためローカル接続前提で、リモートからの利用には別途 HTTP 化が要る。

## JD Alignment（この募集要件との対応）

- **AG★（MCP servers / tool orchestration）**: JD が明示的に名指しする `MCP servers` の実装そのもの。外部 AI クライアントにツールを公開する agentic 統合を実物で示せる。

## References

- 実装: [backend/mcp_server.py](../../backend/mcp_server.py)
- 依存: `mcp` ライブラリ（[backend/requirements.txt](../../backend/requirements.txt)）
- 再利用元: `get_ai_response_with_simple_chart`（`backend/app/services/ai_service.py`）
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]]（MCP 経路の一本化は未追従）
