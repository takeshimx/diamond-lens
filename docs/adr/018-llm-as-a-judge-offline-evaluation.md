# ADR-018: LLM-as-a-Judge による多次元オフライン評価

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

LLM の出力品質（パースの正しさ、応答の質）を、ルールベースの完全一致だけで測るのは限界があります。「`rbi` と `runs_batted_in` は同義」「意図は合っているが表現が違う」といった**意味的な正しさ**は、文字列一致では PASS/FAIL を正しく付けられません。

人手レビューは正確ですが、回帰のたびに全件を人が見るのはスケールしません。「**意味的な品質を、人手に頼らず自動で多次元採点したい**」という課題です。

## Decision（決定）

LLM を「審判（Judge）」として使い、出力を**多次元で意味的に採点**する仕組みを導入しました（[backend/app/services/llm_judge_service.py](../../backend/app/services/llm_judge_service.py)）。ルールベース評価（`evaluate_llm_accuracy.py`）を**補完**する位置づけです。

- **パース評価 Judge** `LLMJudgeService`: expected vs actual を **4 次元**（`query_type_accuracy` / `metrics_accuracy` / `entity_resolution` / `intent_understanding`）で 1〜5 採点し、`overall_score >= 3.5`（`PASS_THRESHOLD`）で PASS、不合格は `failure_category`（synonym_mismatch 等）を付与（[llm_judge_service.py:19](../../backend/app/services/llm_judge_service.py#L19) / [:45](../../backend/app/services/llm_judge_service.py#L45)）。
- 観点別に複数の Judge サービスを用意（パース／応答合成／ルーティング／リフレクション／ドリフトアラート）：`llm_judge` / `synthesizer_judge` / `routing_judge` / `reflection_judge` / `drift_alert_judge`。README #10 の「5-panel」はこの観点群を指す。
- Judge も LLM 呼び出しのため、Gateway 経由でコスト記録される（[[013-centralized-llm-gateway]]）。

## Alternatives Considered（検討した代替案）

- **ルールベース（完全一致）のみ**: 同義語・表現揺れを誤って FAIL にする。意味評価ができない。Judge で補完する。
- **人手レビューのみ**: 正確だがスケールしない。回帰の自動化に向かない。Judge を一次フィルタにし、人手は HITL の golden 昇格（[[021-hitl-golden-flywheel]]）に集中させる。
- **単一スコアの Judge**: どの観点で落ちたか分からず改善に繋がらない。次元別スコア + `failure_category` で原因を分解する。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 意味的な品質を自動で多次元採点でき、回帰検知がスケールする。
- 次元別スコア + `failure_category` で「どこが悪いか」が分かり、改善の手がかりになる。
- shadow eval（[[019-shadow-evaluation]]）や CI gate（[[020-ci-evaluation-gate]]）の採点エンジンとして再利用できる。

**悪くなったこと / 新たな負荷**

- Judge 自体が LLM のため、**判定にコストと非決定性**がある（同じ入力で揺れうる）。
- Judge モデル（`gemini-2.0-flash`）の偏り・誤判定リスク。閾値 3.5 はヒューリスティック。
- プロンプト依存で、Judge プロンプトの改訂が評価結果に影響する。

## JD Alignment（この募集要件との対応）

- **EV★（evaluation pipelines: accuracy）**: JD が明示する evaluation pipeline の中核。LLM-as-a-Judge は GenAI の品質評価の標準手法で、設計判断として語れる。

## References

- 実装: [backend/app/services/llm_judge_service.py](../../backend/app/services/llm_judge_service.py) ほか `*_judge_service.py`
- 評価スクリプト: [backend/scripts/evaluate_with_llm_judge.py](../../backend/scripts/evaluate_with_llm_judge.py)
- テスト: `backend/tests/test_llm_judge.py` ほか
- 関連 ADR: [[019-shadow-evaluation]], [[020-ci-evaluation-gate]], [[021-hitl-golden-flywheel]], [[013-centralized-llm-gateway]]
