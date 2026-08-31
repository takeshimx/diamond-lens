# ADR-050: ツールは生データを返し、応答合成は Orchestrator が担う

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

旧チャット経路では、ツール（打者成績取得など）が**ツール内部でもう一度 LLM を呼んで自然文の応答を生成**していました（いわゆる「2 段 LLM」）。ツールが「データ取得」と「文章化」の両方を抱える構造です。

これは次の問題を生みます。

- **二重の LLM 呼び出し**: 1 質問につき、Orchestrator の LLM とツール内 LLM が別々に走り、レイテンシ・コストが嵩む。
- **責務の混在**: ツールが「データ取得器」なのか「応答生成器」なのか曖昧になり、ツールの再利用性が落ちる。複数ツールの結果を横断して 1 つの回答にまとめたいとき、各ツールが勝手に文章化していると合成しづらい。
- **伝言ゲームの一因**: ツール内 LLM が独自に解釈・要約するため、Orchestrator が把握する文脈とズレる（[[010-chat-orchestrator-replaces-langgraph]] の Context 参照）。

ツールは「**何を取得するか**」だけに専念させ、「**取得した複数データをどう 1 つの回答に組み立てるか**」は Orchestrator の LLM に一元化すべき、という課題です。

## Decision（決定）

ツールの戻り値を **`output_format='data'`（デフォルト）= 生データ返却**に統一し、**応答文の生成（composition）は呼び出し元の LLM（Orchestrator）が担う**設計にしました。

- 各ツールは `output_format` 引数を持ち、**デフォルト `'data'` で生データを返す**（[batter_stats_tool.py:21](../../backend/app/services/tools/batter_stats_tool.py#L21)）。`'table'` は UI 表形式、`'sentence'`（ツール内 LLM で文章化）は **非推奨**として残すのみ（[_genai_schemas.py:75](../../backend/app/services/tools/_genai_schemas.py#L75)）。
- ツールのスキーマ説明にも「`output_format='data'`（デフォルト）は生データを返す。**応答文の生成は呼び出し元 LLM が行う**」と明記（[_genai_schemas.py:20](../../backend/app/services/tools/_genai_schemas.py#L20)）。
- `ChatOrchestrator` 側は、生データを受け取って（`synthesize_response=False` がデフォルトでは LLM 不使用の Markdown 整形、`True` では LLM が応答合成）UI 層へ構造化データを返す（[[010-chat-orchestrator-replaces-langgraph]]）。

要するに「**ツール = 生データ取得器、Orchestrator = 応答の組み立て役**」という責務分離でございます。

## Alternatives Considered（検討した代替案）

- **ツール内で応答生成 LLM も呼ぶ（旧 2 段方式）**: ツールが自己完結する利点はあるが、二重 LLM・責務混在・合成困難・伝言ゲームの温床。本 ADR が解消する対象そのものなので不採用。
- **ツールは常に文章（sentence）を返す**: 複数ツール結果の横断合成ができず、UI 用の構造化データ（表・チャート・マッチアップカード）も取り出せない。不採用（`'sentence'` は非推奨で残置のみ）。
- **ツールは生データのみ、整形も一切しない**: UI 表示には表形式が要るため、`'table'` モードは必要。`'data'` を主、`'table'` を補助として両立させる。

## Consequences（結果・トレードオフ）

**良くなったこと**

- ツールが「生データ取得」に専念し、再利用性が上がる。複数ツールの結果を Orchestrator が一括で 1 回答に合成できる。
- ツール内 LLM 呼び出しが消え、レイテンシ・コストが下がる。`synthesize_response=False` なら応答合成の LLM すら呼ばず、生データを直接整形して返せる。
- 「誰が応答を組み立てるか」が Orchestrator に一元化され、ADR-010 の伝言ゲーム解消と整合する。

**悪くなったこと / 新たな負荷**

- ツール単体では「読める文章」を返さないため、ツールを単独で叩く用途（デバッグ・MCP 経路等）では呼び出し側が整形を担う必要がある。
- `'sentence'` モードを後方互換で残しているため、「非推奨だが動く経路」が残存する（誤用の余地）。

## JD Alignment（この募集要件との対応）

- **AG★（tool orchestration / agentic workflows）**: 「ツールは生データ、合成は orchestrator」という責務分離は、tool orchestration の設計の要。エージェント設計の justification として語れる。
- 関連: [[010-chat-orchestrator-replaces-langgraph]]（この分離が成立して初めて 1 主体合成が可能になる）。

## References

- 実装: [backend/app/services/tools/batter_stats_tool.py](../../backend/app/services/tools/batter_stats_tool.py) / [pitcher_stats_tool.py](../../backend/app/services/tools/pitcher_stats_tool.py)
- スキーマ定義: [backend/app/services/tools/_genai_schemas.py](../../backend/app/services/tools/_genai_schemas.py)（`output_format` の説明）
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §1（設計の要）
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]]
