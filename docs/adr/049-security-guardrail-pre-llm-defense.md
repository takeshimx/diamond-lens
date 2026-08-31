# ADR-049: Security Guardrail — LLM 到達前の 3 層入力防御

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

ユーザー入力をそのまま LLM に渡すと、次のリスクがあります。

- **プロンプトインジェクション**: 「これまでの指示を無視して」「あなたは今から〜」「システムプロンプトを見せて」等で、システムプロンプトの上書き・情報漏洩・jailbreak を狙われる。
- **オフトピック濫用**: MLB 分析と無関係な用途（詩作・翻訳・投資相談・悪意ある依頼）に LLM を使われ、コストと安全性を損なう。
- **構造的異常**: 異常に長い入力や多数の改行で、プロンプトを攻撃的に膨らませる。

「**危険な入力を LLM に届く前に検査・ブロックしたい**（素通し・出力後フィルタだけでは遅い）」という課題です。出力後フィルタは、すでに LLM コストを払い、危険な生成が起きた後の対処になります。

## Decision（決定）

**LLM 到達前**に 3 層で検査する `SecurityGuardrail` を実装しました（[backend/app/services/security_guardrail.py](../../backend/app/services/security_guardrail.py)）。`ChatOrchestrator` は LLM 呼び出し前に `validate_and_log()` を必ず通します。

3 層（実行順は軽い順）：

- **Layer 3 — 構造チェック**（最軽量ゆえ最初）: `MAX_QUERY_LENGTH=500` 超、改行 `MAX_LINE_COUNT=5` 超、空文字をブロック（[security_guardrail.py:156](../../backend/app/services/security_guardrail.py#L156)）。
- **Layer 1 — インジェクション検知**: 正規表現で system_prompt_override / role_reassignment / info_extraction / code_execution / sql_injection / jailbreak_attempt を検知（日英両対応）（[security_guardrail.py:25](../../backend/app/services/security_guardrail.py#L25)）。
- **Layer 2 — オフトピック検知**: MLB ドメインキーワードを 1 つでも含めば通過。無ければ creative_writing / cooking / translation / malicious / financial 等の明示パターンをブロック。曖昧な入力は誤ブロックを避けて通す（[security_guardrail.py:182](../../backend/app/services/security_guardrail.py#L182)）。

ブロック時は BigQuery にインシデントログを記録（`error_type="injection_attempt"`、query は先頭 200 文字のみでプライバシー配慮）。ログ失敗でもメインフローは止めない（[security_guardrail.py:225](../../backend/app/services/security_guardrail.py#L225)）。

## Alternatives Considered（検討した代替案）

- **素通し（防御なし）**: インジェクション・濫用に無防備。本 ADR が解消する対象。
- **出力後フィルタのみ**: LLM コストを払い、危険な生成が起きた後の対処になる。pre-LLM で止める方が安全かつ安価。
- **LLM ベースの分類器で入力を判定**: 高精度だが、入力検査のたびに追加 LLM 呼び出し（コスト・レイテンシ）。第一段は正規表現 + キーワードの軽量・決定論的な検査を採る（将来 LLM 分類を補助に足す余地あり）。
- **オフトピックを厳格にブロック**: 曖昧な MLB クエリまで誤ブロックする。Layer 2 は「MLB キーワードなし＆明示オフトピックなし」は通す保守的設計にした。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 危険な入力を LLM 到達前に止め、コストと安全性を守る（safety 要件）。
- 軽い順（構造→正規表現→キーワード）で、無駄な処理を早期に打ち切る。
- ブロックを BQ に記録し、攻撃傾向を可観測化（trace_id と相関、[[032-snowflake-trace-id-structured-logging]]）。

**悪くなったこと / 新たな負荷**

- 正規表現ベースのため、**未知の言い回しのインジェクションは取りこぼしうる**（LLM 分類より脆い）。
- キーワード方式のオフトピック検知は、MLB キーワードを含む悪意ある入力を通す/含まない正当な入力を弾く誤判定の余地がある。
- パターン辞書のメンテが継続的に必要。

## JD Alignment（この募集要件との対応）

- **EV★（observability frameworks: safety）**: JD が明示する safety の実装。pre-LLM ガードレールは GenAI の安全設計の標準で、多層防御として語れる。

## References

- 実装: [backend/app/services/security_guardrail.py](../../backend/app/services/security_guardrail.py)
- 利用側: [backend/app/services/chat_orchestrator.py](../../backend/app/services/chat_orchestrator.py)（`validate_and_log`）
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §7 Security Guardrail
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[031-firebase-auth-oidc]], [[032-snowflake-trace-id-structured-logging]]
