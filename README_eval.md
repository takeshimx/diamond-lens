# README_eval — 評価システム概要

> **この文書の役割**: 本プロジェクトの評価システムについて、構成・**設計判断とその理由**・実測値を 1 枚にまとめた参照文書。
> 手順書ではないため、実行コマンドは末尾に最小限だけ置く。決定の詳細は各 ADR、実施ログは `docs/plan_docs/` を参照。
>
> **最終更新**: 2026-08-24

---

## 1. 30 秒サマリ

非決定的な LLM システムに対し、**4 層 + オンライン**の評価を敷いている。

- **L1 ユニット**: LLM を呼ばない決定的テスト。fail-open の保証が主目的
- **L2 トラジェクトリ**: LLM は実際に呼び、BigQuery だけ固定。「LLM の揺れ」を分離して測る。3 回実行の `pass^3` で判定
- **L3 パース精度**: ゴールデンデータセットに対するルールベース評価 + LLM-as-a-Judge の二本立て
- **検索評価**: RAG の hit@k / recall@k / MRR / 誤発火率
- **オンライン**: 本番応答の非同期サンプリング Judge（5%）と Shadow Evaluation（champion/challenger 並走）

一貫した設計思想は 3 つ。**(a) 評価が本番を壊さない**（非同期・例外握り潰し・fail-open）、**(b) 非決定性は複数回実行で測る**、**(c) 閾値や設定値は憶測で決めず実測で決める**。

---

## 2. 評価レイヤーの全体像

```
                        ┌──────────────── オフライン ────────────────┐
 コード変更 ──▶ L1 ユニット ──▶ L2 トラジェクトリ ──▶ L3 パース精度 ──▶ 検索評価
                (LLM 呼ばない)   (LLM 呼ぶ/BQ 固定)    (Judge 併用)    (RAG)
                        └────────────────────────────────────────────┘
                                          │
                                     デプロイ
                                          │
                        ┌──────────────── オンライン ────────────────┐
                        │  Online Judge（5% サンプリング・非同期）      │
                        │  Shadow Eval（champion/challenger 並走）     │
                        │  Data Drift（KS / PSI / mean-shift）        │
                        └────────────────────────────────────────────┘
```

| 層 | 何を守るか | LLM 呼ぶ | 判定 | 実装 |
|---|---|:--:|---|---|
| L1 ユニット | 障害時の fail-open、境界条件 | ✕ | 決定的 assert | `backend/tests/test_glossary_rag_service.py` ほか |
| L2 トラジェクトリ | ツール選択と引数の正しさ、ループ暴走 | ○ | 決定的 assert（Judge は使わない） | `backend/tests/eval/harness.py` |
| L3 パース精度 | 自然言語 → 構造化クエリの精度 | ○ | ルールベース + LLM Judge | `backend/scripts/evaluate_llm_accuracy.py` / `evaluate_with_llm_judge.py` |
| 検索評価 | RAG が正解チャンクを引けるか | △ | 決定的（順位計算） | `backend/scripts/run_retrieval_eval.py` |
| 誤発火評価 | 引くべきでない質問でツールを呼ばないか | ○ | 決定的 | `backend/scripts/run_misfire_eval.py` |
| Online Judge | 本番応答の品質 | ○ | LLM Judge | `backend/app/services/online_judge_service.py` |
| Shadow Eval | 新旧比較（ユーザー影響ゼロ） | ○ | ペア比較ログ + Judge | `backend/app/services/shadow_logger_service.py` |
| Data Drift | ML モデルの入力分布ずれ | ✕ | 統計検定 | `backend/app/services/data_drift_service.py` |

---

## 3. 設計判断と、その理由

### 3-1. 評価アーキテクチャの判断

| 論点 | 採用 | 却下したもの | 理由 |
|---|---|---|---|
| 意味的な正しさの判定 | LLM-as-a-Judge で**多次元採点**（1〜5 点、`overall_score >= 3.5` で PASS） | ルールベース完全一致のみ | `rbi` と `runs_batted_in` のような同義語・表現揺れを誤って FAIL にする |
| 同上 | 同上 | 人手レビューのみ | 正確だがスケールしない。Judge を一次フィルタにし、人手は golden 昇格に集中 |
| Judge のスコア設計 | 観点別スコア + `failure_category` | 単一スコア | 単一値では「どこが悪いか」が分からず改善に繋がらない |
| L2 の判定方法 | **決定的 assert**（Judge を使わない） | L2 も Judge で採点 | 測りたいのはツール選択の正誤で、これは文字列比較で足りる。Judge を挟むと Judge の非決定性が混入し、何を測っているか分からなくなる |
| L2 の実行回数 | **3 回実行し `pass^3`**（3 回とも通った率） | 1 回実行の pass/fail | 非決定的システムで単発の合否は無意味。たまたま通った 1 回で緑にしてはいけない |
| L2 の BigQuery | `_execute_tool` を差し替えて**固定データ**を返す | 実 BQ を叩く | データ変動が混ざると「LLM の揺れ」を分離できない。LLM だけは実際に呼ぶ |
| 本番評価の方式 | **Shadow**（champion を返しつつ challenger を裏で走らせる） | A/B テスト（challenger を一部ユーザーに返す） | ユーザーが challenger の劣化を被る。Shadow なら**ユーザー影響ゼロ**で本番分布を測れる |
| 同上 | 同上 | オフライン golden のみ | 実トラフィックの分布とエッジケースが見えない |
| Shadow の実行 | **非同期 fire-and-forget**（別スレッド + `daemon=True`）、例外は内部で握り潰す | 同期実行 | 本番レイテンシに challenger の実行時間が乗る。かつ shadow の失敗でユーザー応答を落としてはならない |
| Online Judge | **サンプリング 5%**・応答返却後に非同期実行 | 全件評価 | 全件は課金が読めない。レイテンシにも乗せない |
| ドリフト検知の指標 | **KS 検定 + PSI + 平均シフト率**の併用 | KS のみ | KS は分布差に敏感だが業務的な「どれだけずれたか」が分かりにくい。PSI（実務標準）と併用して多面判定 |
| 同上 | 同上 | 精度メトリクスのみで監視 | 正解ラベルが遅れて入るため検知が遅れる。入力分布のドリフトなら正解を待たず早期に気づける |
| CI ゲートの閾値 | parse accuracy **≥ 80%** から開始 | ≥ 95% | golden が 14 ケースと小規模な段階では 1 ケースの揺れで頻繁にブロックし運用が回らない |
| Judge の呼び出し | すべて `call_gemini`（LLM Gateway）経由 | 各 Judge が直接 SDK を叩く | 直叩きはコスト計上が漏れる（ADR-013） |

### 3-2. RAG 検索の判断（ADR-047）

| 論点 | 採用 | 却下したもの | 理由 |
|---|---|---|---|
| 精度改善の手段 | **LLM リランク**（候補 10 件を Gemini が並べ直す） | 距離閾値のチューニング | 最近傍の**不正解 0.1684 < 正解 0.1816**。分布が重なっており、どこに線を引いても分離不能。これを実測で示したのがリランク採用の直接の根拠 |
| ベクトルストア | **BigQuery**（`ML.DISTANCE` ブルートフォース） | ChromaDB を復活させる | Cloud Run のイメージ肥大化が RAG 無効化の直接原因だった。BQ なら新規ライブラリゼロ |
| 同上 | 同上 | `VECTOR_SEARCH` + インデックス | 第 1 引数がテーブル固定でサブクエリを取れず、`category` の**事前フィルタができない**。43 件規模ならブルートフォースで十分 |
| 埋め込み | `text-multilingual-embedding-002`、`task_type` を**非対称指定**（文書 `RETRIEVAL_DOCUMENT` / 質問 `RETRIEVAL_QUERY`） | 単一 task_type | 質問は日本語・文書は英語混じりのクロスリンガル検索を 1 モデルで吸収する |
| 語彙ギャップ | リランクで後段解決 | 各エントリに「想定質問」を手書き追加 | 43 件だから成立するだけで、**文書数に比例して人手が増えスケールしない** |
| チャンク | `## 見出し` 1 つ = 1 チャンク。**メタデータはベクトル化対象から除外**し別カラムへ | チャンク全文を埋め込む | 全チャンク共通の定型文が識別力を下げる |
| 呼び出し方式 | **Agentic RAG**（LLM が必要と判断したときだけ引く） | 常時検索する naive RAG | 数値集計は SQL ツールの担当。全質問で検索すると無駄な課金とノイズが増える |
| 出典 | 合成後に**機械的に付加**（`_append_sources`） | system prompt で「出典を明記せよ」と指示 | 「だいたい守られる」に留まる。実際に要約の過程で落ちた事例あり |
| 応答合成の要否 | **ツール名**で判定（`SYNTHESIS_REQUIRED_TOOLS`） | 戻り値のキー（`sources` 等）で推測 | 将来別ツールが同じキーを返した瞬間、黙って挙動が変わる |
| 評価コスト | 質問側の埋め込みを **BQ にキャッシュ** | 毎回生成 | 閾値・フィルタ・リランクの構成比較を何度回しても追加課金が出ない |

---

## 4. Judge サービス 6 種

すべて `call_gemini`（Gateway）経由。判定モデルは `gemini-3.6-flash`。

**Judge を生成側（`gemini-2.5-flash`）より上位のモデルに置いているのは意図的**。採点側が被採点側より弱いと、微妙な事実誤認や論理の飛躍を検出できず採点が甘い方向に偏る。とくに `factual_accuracy` / `analytical_depth` のような内容理解を要する次元で影響が出る。Judge は低頻度・入力 4000 字切り詰め・JSON 出力のため、上位モデルでも絶対額は小さい。

| サービス | 対象 | 評価次元 | 出力の特徴 |
|---|---|---|---|
| `llm_judge_service` | パース精度（自然言語 → 構造化クエリ） | 4 次元: query_type_accuracy / metrics_accuracy / entity_resolution / intent_understanding | `overall_score >= 3.5` で PASS、不合格に `failure_category`（synonym_mismatch 等） |
| `synthesizer_judge_service` | 応答・レポートの品質 | 5 次元: factual_accuracy / analytical_depth / language_quality / structure / completeness。**RAG 経路のみ 6 次元目 `context_relevance`** | 本番チャット経路にサンプリング接続済み |
| `routing_judge_service` | Supervisor のルーティング判断 | 4 次元 | 正解ルート（batter / pitcher / stats / matchup）との突合 |
| `reflection_judge_service` | 自己修正ループの判断品質 | 4 次元: trigger_appropriateness / root_cause_identification / correction_quality / over_correction_risk | **過修正リスク**を明示的に測る（5 = リスクなし） |
| `drift_alert_judge_service` | 統計的ドリフト検知結果の解釈 | 4 次元: statistical_validity / practical_significance / actionability / domain_relevance | `recommended_action`（retrain / monitor / ignore）を返すセカンドオピニオン層 |
| `online_judge_service` | 本番応答（`synthesizer_judge` を呼ぶ薄いラッパ） | — | サンプリング判定・非同期実行・入力 4000 字切り詰め・例外握り潰し。結果は BQ `online_judge_verdicts` へ |

**設計上のポイント**: Judge を観点ごとに分けているのは、単一の万能 Judge にすると「何が悪いか」が潰れるため。ドリフト判定に Judge を重ねているのは、統計的有意と業務的重要性が一致しないため（PSI が動いても実害がないケースを `ignore` に落とす）。

### RAG Triad との対応

RAG 品質評価の定番である **RAG Triad**（context relevance / groundedness / answer relevance の 3 点検査）について、**専用フレームワーク（TruLens 等）は導入しない**。3 辺とも既存資産で測っており、導入すると依存が増えるうえ同一項目を二重計上するため。

| RAG Triad の辺 | 日本語 | 本プロジェクトでの実装 | 測定範囲 |
|---|---|---|---|
| Context Relevance | 引いた文書は質問に関係あるか | `synthesizer_judge` の `context_relevance` | **本番トラフィック**（5% サンプリング） |
| 同上 | 同上 | `run_retrieval_eval.py` の hit@k / recall@k / MRR | オフライン golden 13 問 |
| Groundedness | 回答は引いた文書に根拠を持つか | `synthesizer_judge` の `factual_accuracy`。判定プロンプトに実際のツール戻り値を「元データ」として渡している | 本番トラフィック |
| Answer Relevance | 回答は質問に答えているか | `synthesizer_judge` の `completeness` | 本番トラフィック |

`context_relevance` を追加した動機は、**3 辺のうちここだけがオフライン 13 問でしか測られていなかった**こと。本番でどんな質問が来て、どれだけ的外れなチャンクを引いているかが不可視だった。

### `context_relevance` の設計判断

| 論点 | 採用 | 却下したもの | 理由 |
|---|---|---|---|
| 評価フレームワーク | 既存 Judge に採点項目を 1 つ追加 | TruLens 等の導入 | 依存が増え、既存 Judge と同一項目を二重計上する。観点別 Judge という本プロジェクトの設計とも噛み合わない |
| RAG 非発火時の扱い | **採点基準ごとプロンプトから外し `0`（評価対象外）を記録** | 常に採点させる | 文書を引かない成績照会に「文脈の関連度」を尋ねると、Judge が架空のスコアを返す |
| `overall_score` への算入 | **含めない**（プロンプトで明示的に除外を指示） | 6 項目の平均に変更 | 合格ライン 3.5 の意味が変わり、既に蓄積した判定結果と比較できなくなる |
| 「対象外」と「判定失敗」の区別 | `retrieval_used`（BOOL）を別列で保持 | `context_relevance=0` のみ | どちらも 0 になるため、列がないと集計時に切り分けられない |
| RAG 発火の判定方法 | **ツール名**（`RETRIEVAL_TOOLS = {"glossary_search_tool"}`） | 戻り値のキーで推測 | 別ツールが同じキーを返した瞬間に黙って挙動が変わる。`SYNTHESIS_REQUIRED_TOOLS` と同じ思想 |
| 追加コスト | 既存 1 コールに採点項目を 1 つ足すのみ | 専用 Judge を新設 | Judge 呼び出し回数を増やさない。増分はプロンプト約 200 字と出力 1 項目 |

**前提**: BQ `online_judge_verdicts` に `context_relevance INT64` / `retrieval_used BOOL` の 2 列が必要。`_write_to_bq` は例外を握り潰すため、**列がないと無言で記録が欠落する**。

---

## 5. ゴールデンデータセット

| ファイル | 件数 | 用途 | 育て方 |
|---|---:|---|---|
| `backend/tests/golden_dataset.json` | 14 | L3 パース精度・CI ゲート | HITL フライホイール（👎 → `extract_golden_dataset.py` で BQ から抽出 → 人手レビュー → `approve_to_golden.py` で昇格） |
| `backend/tests/golden/trajectories.jsonl` | 17 | L2 トラジェクトリ | 手動。`p0` タグ 7 件 / `p1` 10 件 |
| `backend/tests/golden/fixtures.json` | 4 ツール分 | L2 の BQ 固定データ | 手動 |
| `backend/tests/golden/retrieval_fixtures.json` | 15 | 検索評価 + 誤発火評価 | 手動。型別に direct 3 / paraphrase 5 / confusable 2 / rule 3 / should_not_fire 2 |

**型を分けている理由**: 平均値だけ見ると改善の効いた場所が分からない。用語名を含む `direct` は元から 1.000 で伸びしろがなく、実際に効いたのは `paraphrase`（言い換え）と `confusable`（紛らわしい対）だった。型別に切ることで初めてそれが見える。

---

## 6. 指標の定義

| 指標 | 定義 | 補足 |
|---|---|---|
| **hit@k**（命中率） | 上位 k 件に正解が 1 件でも入った質問の割合 | RAG 文献で "Recall@k" と呼ばれるもの |
| **recall@k**（網羅率） | 正解集合のうち上位 k 件に入った割合 | ML の定義通り。**正解が 1 件の質問では hit@k と一致し、複数正解のときだけ差が出る** |
| **MRR** | 正解の最上位順位の逆数の平均 | 1 位と 3 位を区別する。hit@k では見えない「順位の改善」を検出する |
| **誤発火率** | 検索不要な質問でツールが呼ばれた割合 | 検索精度ではなく**ツール選択**の問題なので評価スクリプトを分けている |
| **pass^3** | 3 回実行して 3 回とも通った割合 | 非決定性を織り込んだ合否 |
| **PSI** | Population Stability Index | 0.1 超で warning、0.2 超で critical |
| **context_relevance** | 引いた文書の質問との関連度（1-5） | `0` は「評価対象外」であり最低評価ではない。RAG 非発火時と Judge 失敗時に入る。両者は `retrieval_used` で区別する |

> hit@k と recall@k を分けているのは、RAG 文献と ML 文献で "Recall" の語が別物を指すため。用語を混ぜたまま数値を出すと議論が噛み合わなくなる。

---

## 7. 実測値

### 検索精度（ゴールデンセット 13 問。`should_not_fire` 2 問は対象外）

| 構成 | hit@3 | hit@5 | MRR |
|---|---:|---:|---:|
| ベクトル検索のみ | 0.615 | 0.769 | 0.585 |
| **+ LLM リランク** | **0.769** | **0.923** | **0.762** |

用語集のみ（`rule` 型 3 問を除く 10 問）に絞ると **hit@3 0.700 → 0.900 / MRR 0.658 → 0.925**。全体値を押し下げているのは公式ルール PDF 由来の `rule` 型で、hit@3 は 0.333 に留まる。

型別の効き方:

| 型 | リランク前 hit@3 | リランク後 hit@3 | MRR |
|---|---:|---:|---|
| direct（用語名を含む） | 1.000 | 1.000 | 1.000 → 1.000 |
| paraphrase（言い換え） | 0.600 | 0.800 | 0.567 → 0.850 |
| confusable（紛らわしい対） | 0.500 | **1.000** | 0.375 → 1.000 |

**誤発火率 0.000**（2/2 で正しく成績取得ツールを選択）。副次効果として閾値通過後のノイズも 3.00 → 2.60 件/問に減少。

### 閾値の確定（0.275）

| 閾値 | 正解保持率 | ノイズ件数/問 | 空回答率 |
|---:|---:|---:|---:|
| 0.250 | 0.700 | 2.50 | 0.100 |
| **0.275** | **0.800** | **3.00** | **0.000** |
| 0.350 | 0.800 | 3.70 | 0.000 |

0.275 以上に緩めても正解は増えず無関係な結果だけが増える。0.275 未満では「該当なし」が出始める。

### L2 トラジェクトリ

17 ケース × 3 回。`p0` 7 件が 1 件でも 3/3 に満たなければ終了コード 1（デプロイゲートとして機能する）。

---

## 8. 記録すべき失敗（リランク採用の根拠）

**打者の質問に投手指標が 1 位で返った。**

「打球の質は良いのに結果が出ていない打者を見分ける指標は」に対し、ベクトル検索は投手指標 **Stuff+（球質指数）を 1 位**（distance 0.221）に返した。正解の xwOBA は圏外。

原因は 2 つ。

1. **表層語彙の一致**: 質問語「打球の質」は xwOBA のチャンクに一度も出現せず（当該チャンクは「打球内容」と表記）、投手チャンクの**見出し**に「球質指数」「被打球の質」があった
2. **識別力の低下**: 43 件すべてが同一ドメイン・同一テンプレート・同一文体のため、埋め込みの大部分が「野球指標の定義文である」という共通成分に占有され、識別成分が小さかった

対策の経過:

| 施策 | 結果 |
|---|---|
| メタデータをベクトル対象から除外 | **効果なし**。Stuff+ が 1 位のまま（0.185 とむしろ接近） |
| `category='batting'` で事前フィルタ | 投手ノイズは消えたが、xwOBA は batting 15 件中 **8 位**。距離レンジ 0.2381〜0.2919（幅 0.054）でほぼ無差別 |
| 距離分布を測定 | **最近傍の不正解 0.1684 < 最近傍の正解 0.1816**。閾値では原理的に分離不能と判明 |
| LLM リランク | hit@3 0.700 → 0.900、confusable 型は 0.500 → 1.000 |

**決定的だった事例**: 「空振り率で分母がスイング数の方は」に対しベクトル検索は SwStr% を 1 位にしたが、リランクは Whiff Rate に入れ替えた上で他 9 件を全て捨てた。分子が同じで分母だけ違うという差は、ベクトルでは捉えられない。

**学び**: 「精度が出ない → 閾値を調整する」と反射的に動く前に、**分布を測って打ち手が原理的に効くかを先に確かめる**。この測定がなければ、効かない閾値チューニングに時間を溶かしていた。

---

## 9. 既知の制約と今後の一手

現時点で解消できていない負債を、事実として記載する。

| 項目 | 現状 | 今後の一手 |
|---|---|---|
| CI 評価ゲートが無効 | `cloudbuild.yaml` の `llm-evaluation-gate` / `schema-validation-gate` / `ml-drift-check-gate` は全面コメントアウト中。レイヤー別デプロイ時の実行時間・課金を避けるための運用措置。**設計とスクリプトは存在するが CI で強制されていない** | 最大の負債。golden 拡充と併せて有効化する |
| GitHub Actions の対象漏れ | `pytest`（4 ファイルを名指し）+ `ruff` のみ。`test_glossary_rag_service.py` は**まだ対象に入っていない** | ファイル列挙方式のため追加漏れが起きる。ディレクトリ指定へ移行する |
| ゴールデンセットが小規模 | 14 / 17 / 13 件規模。誤発火率 0.000 は「現時点で問題が検出されなかった」以上の意味を持たない | HITL フライホイール（§5）で育てる |
| Judge の非決定性 | 同じ入力でスコアが揺れる。PASS 閾値 3.5 もヒューリスティック | Judge を唯一の判定にせず、ルールベース評価と併用。L2 は Judge を使わず決定的 assert に倒している |
| Judge のモデルバイアス | `gemini-3.6-flash` の偏り・誤判定リスクが残る。生成側と同一プロバイダのため、Gemini 特有の癖を Judge が見逃す可能性がある。プロンプト改訂も評価結果に影響する | Judge プロンプトのバージョン管理と、人手ラベルとの一致率測定。プロバイダをまたぐ Judge（他社モデル）には LLM Gateway のプロバイダ抽象化が前提となるため、そちらから着手する |
| LLM プロバイダが抽象化されていない | `llm_gateway_service` はコスト計上とログ記録の単一窓口であり、プロバイダの抽象化はしていない。窓口関数は `call_gemini()` 1 本、ツール宣言も `google.genai` の型で直書き。**モデル切替は可能だがプロバイダ切替は不可** | 意図的に未着手（単一プロバイダで要件を満たしているため）。着手する場合はツール宣言のプロバイダ中立化と `ChatOrchestrator` の tool_use ループが最大の工事 |
| リランクのレイテンシ | 実測 **2〜15 秒のばらつき**あり。原因未特定 | 追加計測が必要。用語集の質問に限定して発火するため全体影響は限定的 |
| 公式ルール PDF が未活用 | `rules` カテゴリは取り込み済みだが `EXCLUDED_CATEGORIES` で検索対象から除外中。条文を `(a)(1)` 単位で割り直しても hit@3 は 0.333 | チャンク境界が条文構造と噛み合っていない。Definitions of Terms が Rule 9.23 に吸収されている構造上の問題も残る |
| ブルートフォース検索の線形性 | 件数に対して線形。用語集 43 件 + ルール 897 チャンク。現規模では十分 | 数万件を超えたら `VECTOR_SEARCH` + インデックスを検討。ただし事前フィルタができなくなるトレードオフがある |

---

## 10. 実行方法と課金

> **原則**: 課金の発生するコマンドは、実行前に内容と回数を確認する。

| コマンド | 課金 |
|---|---|
| `pytest backend/tests/test_glossary_rag_service.py` | **なし**（BQ クライアントを完全モック） |
| `python -m backend.scripts.run_retrieval_eval --validate` | **なし**（BQ に接続しない） |
| `python -m backend.scripts.run_retrieval_eval --warm-cache` | 質問 1 件につき埋め込み API 1 コール（未登録分のみ） |
| `python -m backend.scripts.run_retrieval_eval` | **なし**（キャッシュ済み埋め込みを再利用） |
| `python -m backend.scripts.run_misfire_eval` | 質問 1 件につき Gemini 1〜3 コール + BigQuery クエリ |
| `python -m backend.scripts.run_trajectory_eval` | 17 ケース × 3 回の Gemini 呼び出し（BQ は固定データのため課金なし） |
| `python backend/scripts/evaluate_llm_accuracy.py` | golden 14 件分の LLM 呼び出し |
| `python backend/scripts/evaluate_with_llm_judge.py` | 上記 + Judge 分の LLM 呼び出し |

---

## 11. 参照

| 内容 | 場所 |
|---|---|
| LLM-as-a-Judge の決定 | `docs/adr/018-llm-as-a-judge-offline-evaluation.md` |
| Shadow Evaluation の決定 | `docs/adr/019-shadow-evaluation.md` |
| CI 評価ゲートの決定 | `docs/adr/020-ci-evaluation-gate.md` |
| データドリフト検知の決定 | `docs/adr/025-data-drift-detection.md` |
| RAG 再構築とリランクの決定 | `docs/adr/047-rag-chunking-multilingual-embeddings-reranking.md` |
| RAG 再構築の実施ログ | `docs/plan_docs/RAG_REBUILD_PLAN.md` |
| Shadow Evaluation の設計プラン | `docs/plan_docs/SHADOW_EVALUATION_PLAN.md` |
| 検索評価の生レポート | `docs/reports/retrieval_eval_*.md` |
| AI レイヤー全体像 | `README_ai_architecture.md` |

> `docs/` は `.gitignore` によりリポジトリ管理外のため、上記 ADR・プランはローカルにのみ存在する。
