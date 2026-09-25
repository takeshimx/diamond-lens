# ADR-040: Expose stat retrieval to external AI clients (Claude Desktop / Cursor) via an MCP server

> **TL;DR（日本語）**: MLB 統計の取得能力が自前の Web UI / REST API からしか使えなかったため、**MCP（Model Context Protocol）サーバーとして公開**し、Claude Desktop / Cursor 等から会話で直接引けるようにした。業界標準に乗ることで「1 実装で MCP 対応クライアント全部から使える」。ツールは MCP 用に作り込まず、**既存ロジックの薄いラッパー**に徹して二重メンテを避けている。制約は 3 つ: 公開ツールは `query_player_stats` **1 つのみ**、トランスポートが `stdio` でローカル接続前提、そして実体が**旧経路 `ai_service.py` に依存**しており `ChatOrchestrator` への一本化に追従できていない（技術的負債）。
>
> **TL;DR (English)**: MLB stat retrieval was reachable only through the project's own web UI and REST API, so it is now **exposed as an MCP (Model Context Protocol) server**, letting Claude Desktop, Cursor and similar clients query it conversationally. Riding an industry standard means **one implementation serves every MCP-capable client**. The tool is deliberately a **thin wrapper over existing logic** rather than a reimplementation, avoiding duplicate maintenance. Three limits: only **one tool** (`query_player_stats`) is exposed, the `stdio` transport assumes local connections, and the implementation still **depends on the legacy `ai_service.py` path** rather than `ChatOrchestrator` — outstanding technical debt.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

Diamond Lens's MLB stat retrieval was reachable only through its own web UI and REST API. Yet there is real value in asking an AI client people already use every day — Claude Desktop, Cursor — "What was Shohei Ohtani's batting average in 2025?" and having it answered from Diamond Lens data.

The standard way to make that possible is **MCP (Model Context Protocol)**, an open specification for an external AI client to connect to a server that owns tools (functions) and have the AI invoke them. Supporting it turns Diamond Lens into **a tool-providing server callable from any MCP-capable client**.

## Decision

Diamond Lens is **exposed as an MCP server** ([backend/mcp_server.py](../backend/mcp_server.py)).

- The `mcp` library's `Server` is started over `stdio_server` (the standard-I/O transport), so local MCP clients such as Claude Desktop and Cursor can connect.
- One tool, `query_player_stats` (taking `query` and `season`), is exposed. Its argument schema is declared through `inputSchema`, which the AI client reads before calling.
- The tool's body **reuses** the existing chat response logic, `get_ai_response_with_simple_chart`. Rather than reimplementing analysis for MCP, it stays a thin wrapper over existing assets.
- Results are returned as MCP `TextContent`. Chart and table results are converted to Markdown tables so they read well in the AI client.

## Alternatives Considered

- **Expose only the existing REST API**: using it from an external AI client would require writing bespoke integration per client, with no generality. Riding the MCP standard means one implementation serves every MCP-capable client.
- **Build MCP-specific tools from scratch**: reimplementing the analysis logic for MCP would mean maintaining it twice. Wrapping the existing `get_ai_response_with_simple_chart` keeps it DRY.
- **Expose over an HTTP/SSE transport**: the primary goal is local Claude Desktop / Cursor integration, for which `stdio` is sufficient. Moving to HTTP can be considered when remote exposure is actually needed.

## Consequences

**What got better**

- Diamond Lens MLB data can be queried conversationally from Claude Desktop, Cursor and similar clients, extending the product's reach beyond its own UI.
- Being a wrapper over existing logic, implementation and maintenance cost are small.
- Riding the MCP standard means the set of usable clients grows over time with no additional implementation.

**What got worse / new burdens**

- Only one tool, `query_player_stats`, is exposed; advanced features such as strategy reports are not available over MCP.
- The tool's body **depends on the legacy `get_ai_response_with_simple_chart` (`ai_service.py`)** rather than `ChatOrchestrator` ([[010-chat-orchestrator-replaces-langgraph]]). The MCP path never followed the chat refactor — outstanding technical debt.
- The `stdio` transport assumes local connections; remote use would require an HTTP transport.

## Why This Matters

- **MCP server / tool orchestration**: this is the implementation of an agentic integration that exposes tools to external AI clients, and the key is reusing existing analysis rather than reimplementing it.

## References

- Implementation: [backend/mcp_server.py](../backend/mcp_server.py)
- Dependency: the `mcp` library ([backend/requirements.txt](../backend/requirements.txt))
- Reused from: `get_ai_response_with_simple_chart` (`backend/app/services/ai_service.py`)
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]] (the MCP path has not yet followed the consolidation)
