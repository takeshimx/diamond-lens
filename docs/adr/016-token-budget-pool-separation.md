# ADR-016: Token Budget をプール分離（chat / report / shared）する

- Status: Accepted
- Date: 2026-05-17（Phase 3-A）
- Deciders: プロジェクトオーナー

## Context（背景・課題）

日次の LLM トークン使用量に上限（コスト防御）を設けていますが、**単一プール**だと次の問題が起こります。

- 戦略レポート 1 本生成（`StrategyAgent` は並列 fan-out で数千トークン消費）で、**チャット用の枠まで一緒に枯渇**する。
- レポートとチャットは利用頻度・1 回あたりコストが大きく異なるのに、同じ財布から引くため、片方の重い処理がもう片方を巻き添えにする。

「重い report 処理が軽い chat を枯渇させない」よう、用途別に枠を分けたい、という課題です。

## Decision（決定）

Token Budget を **chat / report / shared の 2＋1 プール**に分離しました（[backend/app/services/token_budget_service.py](../../backend/app/services/token_budget_service.py)、Phase 3-A）。

- **chat**: `ChatOrchestrator` 経由の使用量（[token_budget_service.py:8](../../backend/app/services/token_budget_service.py#L8)）。
- **report**: `StrategyAgent` / strategy-report / tactics 経由の使用量。
- **shared**: 上記 2 つの**合算 hard cap**（派生値。直接記録は不可）。
- **判定ロジック**: `is_budget_exceeded(pool)` は「**プール別上限 OR 合算 hard cap のいずれか超過で True**」（[token_budget_service.py:77](../../backend/app/services/token_budget_service.py#L77)）。プール枠と全体上限の二段で守る。
- **計上**: 各経路が `record_usage(tokens, pool=...)` で自分のプールに加算（ChatOrchestrator は `pool="chat"`）。
- **実装**: in-memory + `threading.Lock`、UTC 日付で日次リセット。Redis 不要（[[030-in-memory-rate-limit]] と同思想）。

## Alternatives Considered（検討した代替案）

- **単一プール（現状維持）**: report がチャット枠を枯渇させる問題が残る。本 ADR が解消する対象。
- **完全独立な 2 プール（shared なし）**: 全体のコスト上限（hard cap）が効かず、両プール合算で青天井になりうる。shared を派生 hard cap として併設し二段で守る。
- **Redis 等の分散カウンタ**: 単一コンテナ運用では過剰。再起動でリセットされても「コスト防御」目的には十分機能する（分散整合は [[048-distributed-rate-limit]] で将来検討）。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 重い report 生成が chat 枠を巻き添えにしない（逆も成立）。
- プール別＋合算の二段で、用途別の公平性と全体のコスト上限を両立。
- 実装が軽量（in-memory + Lock）で依存が増えない。

**悪くなったこと / 新たな負荷**

- in-memory のため、Cloud Run コンテナ再起動・複数インスタンス間でカウントが共有されない（分散整合は未対応）。
- プール別上限値（`LLM_DAILY_TOKEN_BUDGET_CHAT` 等）はヒューリスティックで、最適配分の保証はない。
- 既存の合算アラート閾値とプール別閾値の二系統を運用する手間が増える。

## JD Alignment（この募集要件との対応）

- **LM★（LLM-native metrics / state management / cost）**: トークン予算という LLM 固有の state をプール単位で管理する。コスト制御の設計判断として語れる。

## References

- 実装: [backend/app/services/token_budget_service.py](../../backend/app/services/token_budget_service.py)
- 利用側: [backend/app/services/chat_orchestrator.py](../../backend/app/services/chat_orchestrator.py)（`record_usage(..., pool="chat")`）
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §9.5 Token Budget プール分離
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[011-retain-langgraph-for-strategy-agent]], [[013-centralized-llm-gateway]], [[030-in-memory-rate-limit]], [[048-distributed-rate-limit]]
