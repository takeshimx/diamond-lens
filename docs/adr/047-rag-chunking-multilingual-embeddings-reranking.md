# ADR-047: 用語集 RAG を BigQuery ベースの Agentic RAG として再構築し、LLM リランクを採用する

> 索引で「RAG chunking + multilingual embeddings + reranking」として採番されていた枠を本文で埋めたもの。チャンク設計・多言語埋め込み・リランクの 3 点がいずれも本 ADR の決定に含まれる。

- Status: Accepted（`USE_GLOSSARY_RAG` / `USE_GLOSSARY_RERANK` の 2 フラグで制御）
- Date: 2026-08-21
- Deciders: プロジェクトオーナー

> **後日談（2026-09-04）**: 本 ADR の直後に Tier 2（公式ルール PDF）を取り込んだが、rule 型の命中@3 が 0.333 に留まったため `EXCLUDED_CATEGORIES` で検索対象から除外していた。その後、**この 0.333 がゴールデンセットの正解 chunk_id の誤り（中身のない見出しチャンクを正解に指定していた）による測定バグ**だったと判明し、是正のうえ復帰させた。経緯と対策（カテゴリ別閾値・HyDE）は [[054-cross-lingual-rag-hyde-category-thresholds]] を参照。
>
> 本 ADR の「クロスリンガル検索が 1 モデルで成立」という記述は **Tier 1（日本語の質問 × 日本語の用語集）での観測**であり、日英を跨ぐ Tier 2 には当てはまらなかった点も ADR-054 で訂正している。

## Context（背景・課題）

文書 RAG の実装は存在していたが、**無効化されたまま放置**されていた。

- `rag_service.py`（ChromaDB + sentence-transformers `all-MiniLM-L6-v2`）は `.gitignore` で Git 管理外
- `rag_endpoints.py` は `router.py` でコメントアウト（理由: **Cloud Run のイメージサイズ削減**）
- `requirements.txt` の `chromadb` / `sentence-transformers` / `pypdf2` も同様にコメントアウト

設計面の欠陥も大きく、**PDF 1 ファイルを丸ごと 1 ベクトルに圧縮**しており、チャンク分割が存在しなかった。192 ページの文書を 1 本のベクトルにすれば、どの質問に対しても同じ距離が返る。検索精度は実質ゼロである。

一方、チャット本経路（`ChatOrchestrator`）は BigQuery を直接叩く Tool Use 方式で完成しており、**数値集計に RAG は不要**だった。RAG が必要なのは「xwOBA とは何か」のような**非構造テキスト**に限られる。

課題は次の通り。

- 依存を増やさずに（＝イメージを肥大化させずに）文書 RAG を復活させたい
- 質問は日本語、文書は英語混じりというクロスリンガル検索が必要
- 用語定義のような補助機能の障害が、チャット本体を落としてはならない
- 何より **検索精度を測る手段が無かった**。「動いている」以上のことが言えない状態だった

## Decision（決定）

用語集 RAG を **BigQuery 上で完結する Agentic RAG** として再構築し、**LLM リランクを組み込んだ**。

### 検索基盤

- ベクトルストアを **BigQuery** に置く（`glossary_chunks` / `glossary_embeddings`）。ChromaDB と sentence-transformers を捨てることで、無効化の理由だったイメージ肥大化が構造的に解消する。新規ライブラリはゼロ
- 検索は **`ML.DISTANCE` のブルートフォース**。`VECTOR_SEARCH` は第 1 引数がテーブル固定でサブクエリを取れず、**`category` による事前フィルタができない**ため採用しなかった（後述の事故を構造的に防ぐにはフィルタが必須）
- 埋め込みモデルは **`text-multilingual-embedding-002`**。日本語の質問で英語混じりの文書を引くクロスリンガル検索を 1 モデルで吸収する
- **`task_type` を非対称に指定**する。文書側 `RETRIEVAL_DOCUMENT` / 質問側 `RETRIEVAL_QUERY`

### ナレッジソースとチャンク設計

- Tier 1 として **自前キュレーションの用語集 43 件**（`docs/knowledge/glossary_*.md`）を Git 管理下に置く。用語リストは `METRIC_MAP` と MetricFlow の `metrics/*.yml` から機械抽出し、定義文は LLM でドラフト生成 → 公式ソース（MLB.com Glossary / FanGraphs Library）と突合 → 人間レビュー、という半自動フローで作成
- **`## 見出し` 1 つ = 1 チャンク**。見出し語をチャンク先頭に含めることで、用語名そのものもベクトルに乗せる
- **メタデータをベクトル化対象から除外**する。カテゴリ・メトリクス名・検証ステータスは `category` / `metric_names` / `verified_source` の別カラムへ退避
- 冪等性は **`source`（ファイル）単位の DELETE→INSERT**。見出しの追加・削除・並べ替えで孤児行が残らない

### 呼び出し方式

- 常時検索する naive RAG ではなく、**LLM が必要と判断したときだけ引く Agentic RAG**。`glossary_search_tool` として `ChatOrchestrator` に登録（[[050-tools-return-raw-data-orchestrator-composes]] の責務分離に従う）
- ツール宣言の `description` に「**使ってはいけない場面**（選手の成績値取得）」を明記する。これが誤発火率を決める
- `category`（batting / pitching / statcast）を LLM に選ばせ、事前フィルタに使う

### リランク

- ベクトル検索で **候補を 10 件**取り、閾値で絞ってから **Gemini に並べ直させる**（`rerank_service.rerank_hits`）
- LLM には **候補番号の配列だけ**返させる。本文は先頭 300 字のみ渡す
- 範囲外・重複の番号は捨てる。LLM 出力は保証されないため
- 呼び出しは **`call_gemini`（gateway）経由**（[[013-centralized-llm-gateway]]）。直接 SDK を叩くとコスト計上が漏れる

### 応答生成と出典

- 用語集の結果は生データではなく文章のため、**ツール名で応答合成の要否を判定**する（`SYNTHESIS_REQUIRED_TOOLS`）。成績照会は従来通り機械整形
- **出典は LLM の裁量ではなく機械的に付加**する（`_append_sources`）

### 評価

- ゴールデンセット（`backend/tests/golden/retrieval_fixtures.json`）と評価ハーネス（`backend/scripts/run_retrieval_eval.py`）を整備し、**閾値・カテゴリフィルタ・リランクの効果をすべて実測で決めた**
- 質問側の埋め込みを BQ にキャッシュし、構成比較を何度回しても追加課金が出ないようにした

## Alternatives Considered（検討した代替案）

- **ChromaDB を維持して復活させる**: 無効化の直接原因（イメージサイズ）が再発する。ローカル依存が増え、Cloud Run のサーバレス構成とも噛み合わない。
- **`VECTOR_SEARCH` + ベクトルインデックス**: 本来はこちらが正道だが、第 1 引数がテーブル固定で `category` の事前フィルタができない。43 件〜数千件規模ではブルートフォースで十分。件数が増えたら再検討する。
- **各エントリに「想定質問」を手書きで追加して語彙ギャップを埋める**: 43 件だから成立するだけで、**文書数に比例して人手が増えスケールしない**。語彙ギャップは検索時（リランク・クエリ拡張）で解くべき。**却下**。
- **`synthesize_response=True` の全体有効化**: 成績照会は機械整形の方が正確かつ安価。全質問で LLM 呼び出しが 1 回増えるだけの損。
- **ツール内で LLM を呼んで要約させる**: LLM 呼び出しが 2 箇所に分散し、トークン計上が二重管理になる。
- **system prompt で「出典を明記せよ」と指示する**: 「だいたい守られる」に留まる。実際に要約の過程で出典が落ちる事象が発生しており、引用の担保にならない。
- **応答合成の要否をツール戻り値のキー（`sources` 等）で判定する**: 将来別のツールが同じキーを返した瞬間、黙って挙動が変わる。ツール名で明示的に判定する。

## Consequences（結果・トレードオフ）

### 実測結果

ゴールデンセット 12 問（うち `should_not_fire` 2 問は検索評価の対象外）。

| | 命中@3 | 命中@5 | MRR |
|---|---:|---:|---:|
| ベクトル検索のみ | 0.700 | 0.800 | 0.658 |
| **+ LLM リランク** | **0.900** | **1.000** | **0.925** |

型別では、用語名を含まない言い換え質問が 0.600 → 0.800（MRR 0.567 → 0.850）、紛らわしい対が 0.500 → **1.000**（MRR 0.375 → 1.000）。誤発火率は **0.000**（2/2 で正しく成績ツールを選択）。

### この設計で分かった、記録すべき失敗

**打者の質問に投手指標が 1 位で返った。** 「打球の質は良いのに結果が出ていない打者を見分ける指標は」に対し、ベクトル検索は投手指標 **Stuff+（球質指数）** を 1 位（distance 0.221）に返した。正解の xwOBA は圏外だった。

原因は 2 つ。

1. **表層語彙の一致**: 質問語「打球の質」は xwOBA のチャンクに一度も出現せず（当該チャンクは「打球内容」と表記）、投手チャンクの**見出し**に「球質指数」「被打球の質」が存在していた
2. **識別力の低下**: 43 件すべてが同一ドメイン・同一テンプレート・同一文体のため、埋め込みの大部分が「野球指標の定義文である」という共通成分に占有されていた

メタデータ除去では改善せず、カテゴリフィルタで投手ノイズは消えたが **xwOBA は batting 15 件中 8 位**のままだった。batting の距離レンジは **0.2381〜0.2919（幅 0.054）**しかなく、ほぼ無差別だった。

**さらに、距離では正解と不正解を分離できないことが判明した。**

| 対象 | min | p50 | max |
|---|---:|---:|---:|
| 正解チャンク | 0.1816 | 0.2261 | 0.2542 |
| 最上位の不正解 | **0.1684** | 0.2363 | - |

最近傍の不正解（0.1684）が最近傍の正解（0.1816）より近い。**閾値をどこに引いても分離できない**。閾値は「明らかな無関係を切る」役割に留まり、精度改善には順位付け自体の変更が必要——という結論を、推測ではなく実測が示した。これがリランク採用の直接の根拠である。

閾値は実測に基づき **0.275** に確定した。0.275 以上に緩めても正解保持率は 0.800 のまま増えず、無関係な結果だけが増える（0.275 で 3.00 件/問、0.35 で 3.70 件/問）。0.275 未満では「該当なし」が発生し始める。

### 良くなったこと

- **依存ゼロで文書 RAG が復活した**。ChromaDB / sentence-transformers を使わないため、無効化の理由だったイメージ肥大化が起きない
- **サーバレス・Pay-as-you-go**。常時稼働インスタンスなし。検索 1 回につき Vertex AI 1 コール
- **クロスリンガル検索が 1 モデルで成立**。「打球の質は良いのに結果が出ていない打者を見分ける指標は」という日本語の言い換え質問で、英語混じりの xwOBA チャンクが 1 位に返る
- **数値で語れる**。「RAG を作った」ではなく「RAG を測った」と言える。閾値・カテゴリフィルタ・リランクのすべてが実測に基づく
- **fail-open が全経路に入っている**。BQ 障害・リランク失敗のいずれもチャット本体を落とさない

### 悪くなったこと / 新たな負荷

- **用語集の質問 1 件につき Gemini 呼び出しが 1 回増える**（リランク）。レイテンシは実測で 2〜15 秒のばらつきがあり、追加計測が必要
- **ブルートフォース検索は件数に対して線形**。Tier 2（公式ルール PDF、約 192 ページ）を取り込むと再評価が必要
- **ゴールデンセットが 12 問と小さい**。誤発火率 0.000 は「現時点で問題が検出されなかった」以上の意味を持たない
- **旧 ChromaDB 実装が残置されている**（`rag_service.py` / `rag_endpoints.py` / `document_loader.py` / `index_knowledge_base.py`）。CLAUDE.md の「削除しない」方針に従い、新実装は別ファイルで並走させた

## JD Alignment（この募集要件との対応）

- **検索・RAG の設計**: 「なぜ全部 RAG にしないのか」に対し、構造化数値は SQL、非構造テキストのみ RAG という棲み分けを、実装と数値の両方で説明できる
- **評価**: Recall / MRR / 誤発火率の定義と、複数正解時の hit@k と recall@k の違いまで踏み込んで測定している。「RAG を測った」経験として提示できる
- **失敗の分析**: 表層語彙一致による誤検索と、距離分布の重なりによる分離不能を数値で示し、それを根拠にリランクを採用した——という因果を語れる

## References

- 計画・実施ログ: [docs/plan_docs/RAG_REBUILD_PLAN.md](../plan_docs/RAG_REBUILD_PLAN.md)
- 検索サービス: [backend/app/services/glossary_rag_service.py](../../backend/app/services/glossary_rag_service.py)
- リランク: [backend/app/services/rerank_service.py](../../backend/app/services/rerank_service.py)
- ツール: [backend/app/services/tools/glossary_search_tool.py](../../backend/app/services/tools/glossary_search_tool.py)
- 取り込み: [backend/scripts/ingest_glossary.py](../../backend/scripts/ingest_glossary.py)
- 評価: [backend/scripts/run_retrieval_eval.py](../../backend/scripts/run_retrieval_eval.py) / [run_misfire_eval.py](../../backend/scripts/run_misfire_eval.py)
- ゴールデンセット: [backend/tests/golden/retrieval_fixtures.json](../../backend/tests/golden/retrieval_fixtures.json)
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]] / [[013-centralized-llm-gateway]] / [[050-tools-return-raw-data-orchestrator-composes]] / [[018-llm-as-a-judge-offline-evaluation]]
