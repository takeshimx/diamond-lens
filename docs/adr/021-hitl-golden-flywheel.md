# ADR-021: HITL フライホイール — 👎 を回帰テストに変換し、出口を PR に固定する

- Status: Accepted
- Date: 2026-09-11
- Deciders: Takeshi

## Context（背景・課題）

`golden_dataset.json` は CI の精度ゲート（`evaluate_llm_accuracy.py`、閾値 80%）が読む唯一のテストセットである。この中身をどう増やすかが、評価層全体の実効性を決める。

手で書き足す方法には上限がある。開発者が思いつく質問は、開発者が想定済みの質問であり、**実際に壊れている経路とは相関しない**。一方、本番の 👎 は「実際に壊れた」という事実そのものである。これを再現テストに変換できれば、テストセットは実トラフィックの分布に沿って育つ。

### 既存実装の限界

👎 を抽出する経路自体は存在していた。

```
👎 → BigQuery → extract_golden_dataset.py → pending_review.json
   → 人がエディタで TODO を手編集 → approve_to_golden.py → golden_dataset.json
```

問題は 3 点あった。

1. **すべて手でコマンドを叩く**。スケジューラも UI も無く、実運用では一度も回っていなかった
2. **期待値を入力する場所がテキストエディタ**だった。`pending_review.json` の `"TODO"` を手で埋める設計で、`query_type` の綴りを間違えても気づけない
3. **「レビュー待ち」が可視化されていない**。何件溜まっていて次に何を処理すべきかが分からない

### 前提の整理（設計前に固めた点）

この仕組みが何を**しない**かを先に決めた。ここが曖昧だと「LLM が自律学習する仕組み」と誤解され、期待値がずれる。

- モデルの重みもプロンプトも**自動では変わらない**。増えるのはテストケースだけである
- 👎 が直接「改善」を生むことはない。生むのは**「修正すべき既知の失敗」のリスト**である
- 回答が良くなるのは人が直した時であり、この仕組みが保証するのは**直した後に二度と壊れないこと**である

つまり「バグ報告 → 再現テストを書く → 修正 → テストが緑になる」という回帰テストの標準サイクルを、LLM の評価に持ち込むものである。違いは、期待値が「例外が出ないこと」ではなく「パース結果の `query_type` / `name` / `metrics` が一致すること」であり、LLM が非決定的であるため**期待値を人が承認する工程（HITL）を外せない**点にある。

## Decision（決定）

**👎 を Trace Viewer 上で「正解の期待値」に変換し、承認された分を golden に取り込む PR まで自動で作る。人の作業は Trace Viewer 内で完結させる。**

```
【人】 Trace Viewer
   ├─ 失敗ラベル (ADR-053 の 7 軸)
   └─ 期待値を入力 → 保存
        ↓
   [ 承認して PR 作成 ]
        ↓
【自動】
   trace_expectations を読む
     → GitHub から golden_dataset.json の最新を取得
     → 昇格判定（後述の 2 規則）
     → ブランチ作成 → コミット → PR 作成
```

### 1. 👎 は `request_id` で突き合わせる（`trace_id` では結べない）

フィードバックは既存ログ行の更新ではなく、`user_query='[FEEDBACK_UPDATE]'` の**別行として INSERT** される（Streaming Buffer が UPDATE を許さないため）。

実データを 1 行取得して確認したところ、その行は `node` も **`trace_id` も NULL** だった。`trace_id` は ContextVar から best-effort で取る実装だが、フィードバック送信は別リクエストであり、元のチャットの trace_id は入らない。

```
👎 の行:  trace_id = NULL, node = NULL, request_id = あり
```

したがって `trace_id` では結合できず、`request_id` を結合キーとする。1 trace = 1 request_id であることは実データで確認済み。

この事実は詳細画面にも影響していた。`get_trace` は `WHERE trace_id = @trace_id` で引くため、👎 の行を拾えず、**rating チップが永久に表示されない**状態だった。`request_id` で引き直して合流させる。

### 2. 「失敗ステップ」と「👎」は別の軸である

既存の `only_failed` フィルタは `failed_steps > 0`、すなわちツール実行の例外を見る。

実例として、`career_pitching` を要求した trace は全ステップが `success = true` / `ok: true` と記録されながら、最終回答は「不正な入力を検出しました」だった。Guardrail が拒否した事実が成否として計装されていないためである。

```
計装上: 全ステップ成功、FAIL チップ無し
実際  : 完全に失敗
```

**この種の失敗は `only_failed` では永久に見つからない。** ユーザー評価を独立した軸として持つ必要があり、`only_bad_rating` を追加した。

### 3. 期待値の語彙は tool schema の enum から導出する

選択肢をフロントに直書きすると enum の同期漏れを起こす（ADR-053 の `_split_types` が記録する事故と同種）。`GET /traces/expected-options` がサーバから配る。

導出元の選定でつまずいた経緯を残す。当初 `QUERY_TYPE_CONFIG` から展開したが、これは splits を 2 階層（`batting_splits` → `risp`）で持つため `batting_splits.risp` というドット結合を生んだ。**LLM が実際に出力するのは `query_type="batting_splits"` + `split_type="risp"` の 2 フィールド**であり、`golden_dataset.json` もその形で書かれている。既存 golden と評価スクリプトの双方と噛み合わなかった。

正しい導出元は **tool schema の `FunctionDeclaration` が持つ enum** である。実装側（`query_maps`）ではなく、LLM が選べる値の宣言が語彙の正になる。

### 4. 期待値は追記のみ。保存後は UI でロックする

`trace_labels` と同じ設計で、`trace_expectations` テーブルに追記のみ。付け直しは新しい行の INSERT で表現し、読み出し側が `created_at` の最新を採用する。

ただし UI 上は**保存済みを既定で編集不可**とし、明示的に「修正する」を押した時だけ解除する。golden の元データであり、開いたついでに書き換わる事故を防ぐ。

### 5. 昇格の出口は PR。BigQuery を正にしない

| 案 | 内容 | 難点 |
|---|---|---|
| A. BQ を正 | 承認で `golden_dataset` テーブルに INSERT、CI が実行時に読む | git の履歴とレビューが効かず、**ゲートの基準が知らぬ間に書き換わる** |
| **B. git を正（採用）** | 承認で GitHub API を叩き PR を自動作成。マージして初めてゲートに反映 | 実装がやや重い |

テストの期待値は「壊れても気づけない」種類のデータである。基準そのものにレビューを効かせる必要があり、B を採る。

ファイルは**必ず GitHub から読む**。Cloud Run のコンテナに焼かれた `golden_dataset.json` はビルド時点のもので、他の PR がマージされていれば古い。古い内容で書き戻すと、その間の変更を巻き戻してしまう。

### 6. 構造規則を満たさないものは昇格させず保留する

`tests/test_llm_evaluation.py` が golden に課している規則がある。これを破ると、精度ゲート以前に CI が**構造エラー**で落ちる。

| 規則 | 保留の理由 |
|---|---|
| `query_type` が `QUERY_TYPE_CONFIG` に存在すること | 未実装の機能に対するテストは、プロンプトを幾ら直しても緑にならない |
| 同カテゴリ最低 3 件 | 新カテゴリを 1 件だけ入れると `test_category_coverage` が落ちる |

保留したものは **BigQuery 側に残す**。人の判断（正解はこれだ）は正しく、足りないのは受け入れ側の実装であり、記録を消す理由がない。実装が入った後に同じコマンドを実行すれば自動で昇格する。

判定ロジックは `golden_promotion_service` に集約し、UI 経由（`golden_pr_service`）とローカル CLI（`scripts/approve_to_golden.py`）の双方が同じ関数を使う。二重実装すると経路によって golden の中身が食い違う。

## Consequences（結果・トレードオフ）

### 得られたもの

- 👎 が「忘れられる BQ の 1 行」から「消えない赤いテスト」に変わる
- 同じバグの 2 回目以降を、ユーザーに届く前に CI が検知する（最初の 1 回だけが reactive）
- レビュー待ち行列が UI 上で可視化され、処理すると消える

### 引き受けた制約

- **人の作業は消えない。** 「フライホイール」と呼ぶが、回すのは人である。自動化されているのは記録・抽出・検証・PR 作成までで、期待値の判断と PR のマージは人が行う
- **採点範囲はパース層に限られる。** `evaluate_llm_accuracy.py` はツール引数のみを比較し、ツールを実行しない。したがって「LLM のパースは正しいが下流が壊れている」種類のバグ（上記 Guardrail の例）は golden では捕捉できない。この層は `evaluate_with_llm_judge.py` または対象コードの単体テストが担う
- **未実装機能はテストにできない。** 「赤い PR が修正待ちチケットになる」は、プロンプトやロジックで直せる場合に限り成立する。機能そのものが無いものを入れると CI が永久に赤くなるため、保留する
- GitHub の fine-grained PAT（Contents / Pull requests の RW）が運用上の前提になる。未設定でもアプリは起動し、PR 作成を呼んだ時にだけ明示的に失敗する

### 派生して見つかった負債（本 ADR では対処しない）

`career_pitching` が **tool schema には宣言されているが `query_maps` にも Guardrail のホワイトリストにも存在しない**。`query_type` の許可リストが 3 箇所（tool schema 6 種 / `query_maps` 5 種 / `validate_query_params` 4 種）に分裂しており、Guardrail が最も狭い。投手の通算成績と splits の一部が「不正な入力」として弾かれる。投手通算テーブルが未整備のため、本件は着手しない。

## References

- [ADR-053: Agent Trace Viewer と失敗ラベリング](053-agent-trace-viewer-failure-labeling.md) — 失敗ラベルの 7 軸と trace の計装
- [ADR-049: Security Guardrail](049-security-guardrail-pre-llm-defense.md) — 上記の `validate_query_params`
- [ADR-032: trace_id と構造化ログ](032-snowflake-trace-id-structured-logging.md)
- `backend/app/services/golden_promotion_service.py` — 昇格判定（I/O なし）
- `backend/app/services/golden_pr_service.py` — GitHub API 経由の PR 作成
- `backend/app/services/trace_expectation_service.py` — 期待値の記録と語彙の導出
- `backend/sql/create_trace_expectations.sql`
