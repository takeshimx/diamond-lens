# ADR-015: Gemini Context Caching で固定プレフィックスの再計算課金を削減する

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

システムプロンプト（数千トークンの固定プレフィックス）を毎リクエスト LLM に送ると、その入力トークンが**毎回フル課金**されます。Diamond Lens のプロンプト（`oracle_semantic`、`strategy_synthesizer`、`chat_orchestrator_system` 等）は固定プレフィックスが大きく、function calling ループでは 1 リクエストあたり複数回 LLM を呼ぶため、再計算課金が積み上がります。

「同じプレフィックスを毎回フル課金で送る」のは無駄で、Gemini が提供する **Context Caching**（同一プレフィックスをサーバ側にキャッシュし、ヒット部分の課金を **約 1/10** に下げる機能）を使えば削減できます。しかし AI Engineering レビュー時点では、`client.caches.create()` を呼ぶコードが**リポジトリに 1 件もなく**、`cached_tokens` が常に 0 でした（[diamond-lens-review-05252026.md](../plan_docs/diamond-lens-review-05252026.md) #2）。

### 仕組み（1 プロンプト = 固定の大部分 + 動的な少量）

プロンプトは「毎回同じ固定の指示文（大部分）」と「毎回変わるユーザー質問（少量）」に分かれます。

```
┌──────────────────────────────┐
│ 固定部分（システムプロンプト）     │ ← 毎回まったく同じ・大きい
│ 「あなたはMLB分析の専門家です…」   │
├──────────────────────────────┤
│ 動的部分（ユーザー質問）          │ ← 毎回変わる・小さい
│ 「大谷の去年の打点は？」           │
└──────────────────────────────┘
```

```
■ caching なし：毎回フル課金
  req1: [固定を計算][動的を計算] → 💰💰💰💰💰
  req2: [固定を計算][動的を計算] → 💰💰💰💰💰  ← 固定部分の再計算がムダに高い
  req3: [固定を計算][動的を計算] → 💰💰💰💰💰

■ caching あり：固定部分の「計算済み状態」を再利用
  req1: [固定を計算して保存][動的を計算] → 💰💰💰💰💰（初回は普通）
  req2: [保存済み固定を再利用 ][動的を計算] → 💰🪙  ← 固定が約1/10課金
  req3: [保存済み固定を再利用 ][動的を計算] → 💰🪙
```

> **よくある誤解**: caching は「固定部分を LLM に渡さない」のではありません。**固定部分も毎回 LLM に渡され、回答に使われます**。キャッシュされるのは「固定部分を読み込んだ計算結果」で、削減されるのは**再計算の課金だけ**です。だからプロンプトの質（指示の厚み）を一切落とさずにコストだけ下げられます（短縮は本末転倒 → Alternatives 参照）。

## Decision（決定）

固定プレフィックスを **`client.caches.create()` で登録し、`generate_content` 時に `cached_content` として参照**する lifecycle 管理を `prompt_cache_service` に実装しました（[backend/app/services/prompt_cache_service.py](../../backend/app/services/prompt_cache_service.py)）。

- **キャッシュキー**: `prompt_name | version | model | mode | tools | sha256(prefix)[:16]` の合成キー。プレフィックス内容が変われば別キャッシュになる（[prompt_cache_service.py:68](../../backend/app/services/prompt_cache_service.py#L68)）。
- **TTL と自動再作成**: デフォルト TTL 3600 秒。残り 5 分（`MIN_REMAINING_SECONDS=300`）を切ったら再作成し、期限切れ参照を防ぐ（[prompt_cache_service.py:74](../../backend/app/services/prompt_cache_service.py#L74)）。
- **fail-open**: キャッシュ作成失敗時は `None` を返し、caller は**非キャッシュ経路にフォールバック**する。キャッシュ障害が本処理を止めない（[prompt_cache_service.py:105](../../backend/app/services/prompt_cache_service.py#L105)）。
- **API 制約への対応**: `cached_content` を使う `generate_content` には `system_instruction` / `tools` / `tool_config` を渡せないため、function calling ループをキャッシュする場合は `tools` をキャッシュ側に含める（[prompt_cache_service.py:61](../../backend/app/services/prompt_cache_service.py#L61)、ChatOrchestrator が利用）。

## Alternatives Considered（検討した代替案）

- **毎回フルでプロンプトを送る（現状維持）**: 固定プレフィックスを毎回フル課金。本 ADR が解消する対象。
- **プロンプトを短縮してトークンを減らす**: 品質に直結する指示を削ることになり本末転倒。caching ならプロンプトを保ったまま課金だけ下げられる。
- **キャッシュ必須（fail-closed）**: キャッシュ障害でチャットが止まる。可用性を優先し fail-open を採用。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 固定プレフィックスのヒット部分が約 1/10 課金に。function calling ループは 1 リクエストで複数回 LLM を呼ぶため、削減効果が iteration 数だけ倍加する。
- `cached_tokens` が記録され、コスト計算（[[013-centralized-llm-gateway]]）にキャッシュ割引が反映される。
- fail-open でキャッシュ障害時も可用性を維持。

**悪くなったこと / 新たな負荷**

- in-memory レジストリのため、Cloud Run コンテナ再起動でキャッシュ名を失い、再作成が走る（コストは限定的）。
- プレフィックスが 1,024 トークン未満だと Gemini のキャッシュ対象外で、無音でフォールバックする（効果ゼロのケース）。
- キャッシュキーに version/hash を含めるため、プロンプト改訂（[[014-prompt-as-config]]）のたびに新キャッシュが作られる。

## JD Alignment（この募集要件との対応）

- **LM★（LLM-native metrics / cost）**: cost-per-request を下げる具体的な最適化。Ch.7「Inference Optimization」の実装として語れる。

## References

- 実装: [backend/app/services/prompt_cache_service.py](../../backend/app/services/prompt_cache_service.py)
- 利用側: [backend/app/services/chat_orchestrator.py](../../backend/app/services/chat_orchestrator.py)（`get_or_create_cache`）
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §2.5 Context Caching
- レビュー: [diamond-lens-review-05252026.md](../plan_docs/diamond-lens-review-05252026.md) #2
- 関連 ADR: [[013-centralized-llm-gateway]], [[014-prompt-as-config]]
