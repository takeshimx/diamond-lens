# ADR-009: dbt Semantic Layer (MetricFlow) を query_maps ベースの固定 SQL 構築に代えて採用する

> **注記**: 本 ADR は当初「two-stage text-to-SQL を置換する」と題していましたが、旧経路は LLM に SQL を生成させる text-to-SQL ではなく、`query_maps` 辞書から固定ロジックでパラメータ化 SQL を組む方式でした。タイトル・本文をこの史実に合わせて訂正済みです（hallucination は旧経路の課題ではありません。詳細は Context を参照）。ファイル名は参照リンク互換のため `009-dbt-semantic-layer-over-text-to-sql.md` のまま維持します。

- Status: Accepted（canary：`USE_SEMANTIC_LAYER` フラグで Cloud Run 環境のみ有効）
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

旧チャット経路は、メトリクスの定義（「OPS とは」「RBI はどのテーブルのどのカラムか」「SUM か AVG か」）を **`query_maps.py` の Python 辞書にハードコード**し、それを見て**アプリが固定ロジックでパラメータ化 SQL を構築して** BigQuery を叩いていました。

> **誤解の訂正（重要）**: この経路をかつて「two-stage text-to-SQL」「自由な SQL 生成による hallucination」と表現していましたが、これは**実装と異なる誤った特徴づけ**でした。実際には **LLM は SQL 文字列を一切生成していません**。LLM の役割は自然文から `{query_type, metrics, name, season...}` という構造化パラメータを抽出する NLU のみで、SQL は [QueryBuilder](../../backend/app/services/query_builder.py) がテーブル名・カラム名を `query_maps`／`METRIC_MAP` 辞書から引き、値を `@param` でバインドし、さらに `validate_query_params` でホワイトリスト検証（query_type / metrics / カラムは辞書にある値のみ）したうえで構築していました。**カラム名ミスや存在しない指標の捏造といった SQL 起因の hallucination は構造的に起こり得ず、この世代に hallucination は実在しません**。

旧経路の**実際の**弱点は次の通りで、いずれも「hallucination」ではありません。

- **メトリクス定義の二重化**: 同じ定義がアプリの `query_maps`（SQL 構築ロジック）と dbt モデルの双方に散らばり、片方を変えると静かにズレる（＝サイレントな誤集計のリスク）。
- **集約方法の所在が曖昧**: `query_maps` はカラム名までしか持てず、「HR は合計、AVG は平均」という集約ルールはアプリの SQL 構築ロジック側にあり、書き間違いの温床。
- **ハードコード**: CLAUDE.md の品質ルール「METRIC_MAP 等を直書きせず既存ソースから動的取得」に反する。
- **カバレッジの硬直性**: 辞書に定義済みの query_type しか扱えず、新カテゴリーの追加に辞書＋ビルダー改修が必要。

「メトリクスの真実源（Source of Truth）を 1 つに統一し、定義の二重化を解消したい」という課題です。

## Decision（決定）

メトリクスの定義を **dbt Semantic Layer（MetricFlow）の YAML に一本化（SSOT）** し、LLM は **1-pass の function calling** でメトリクス名を指定するだけにしました。

- メトリクス・次元・集約方法（`agg: sum` / `average`）を dbt の semantic models（`metricflow/dbt_project/models/semantic_models/*.yml`）に定義。例：[batter_season.yml](../../metricflow/dbt_project/models/semantic_models/batter_season.yml) が `home_runs = sum(hr)`、`ops = average(ops)` を定義。
- LLM（ChatOrchestrator）は **検証済みメトリクス名を引数に渡すだけ**で、SQL を自由生成しない。語彙は `semantic_layer_client` 経由で MetricFlow から動的取得し、prompt に注入（[[010-chat-orchestrator-replaces-langgraph]]）。
- MetricFlow は別の Cloud Run サービス（`mlb-metricflow-server`）として動かし、backend から **OIDC service-to-service 認証**で呼ぶ（[semantic_layer_client.py](../../backend/app/services/semantic_layer_client.py)）。
- `USE_SEMANTIC_LAYER` フラグで **Cloud Run 環境のみ canary 有効**。ローカル／未設定時は legacy（`query_maps`）経路にフォールバックする（[[035-feature-flag-canary-rollout]]）。

## Alternatives Considered（検討した代替案）

- **`query_maps` + 固定 SQL ビルダーの継続（旧経路の維持）**: メトリクス定義の二重化と集約方法の散在が解決しない。本 ADR が解消する対象（旧経路は LLM による SQL 生成ではなく辞書由来の固定構築であり、解消したいのは hallucination ではなく定義の二重化）。
- **`query_maps` を充実させて維持**: 定義のハードコードと二重化が残り、集約方法も持てない。SSOT にならない。
- **真の two-stage text-to-SQL（LLM に SQL を生成させる）へ移行**: カラム名ミス・存在しない指標の捏造という SQL 起因 hallucination を**新たに招き入れる**ことになり、旧経路が構造的に避けていた問題をわざわざ作り込むため不採用。
- **BI ツール（Looker 等）の semantic layer を採用**: 重く、LLM から直接メトリクスを引く用途には過剰。dbt（既存のデータ変換基盤）に semantic layer を載せる方が一貫する。

## Consequences（結果・トレードオフ）

**良くなったこと**

- **メトリクス定義が dbt に一本化（SSOT）**。ダッシュボード・LLM・BI が同じ定義を見る。サイレントな誤集計が消える。
- 集約方法まで定義側が持つため、「HR は合計、AVG は平均」を人間が SQL で書き間違える余地がない。
- LLM は SQL を自由生成せず、検証済みメトリクス名を指定するだけ＝この先 SQL 生成へ踏み込んでも hallucination を構造的に防げる設計を、Semantic Layer 側で恒久化（旧経路が固定ビルダーで担保していた「捏造の余地のなさ」を、定義の SSOT 化と両立させた形）。

**悪くなったこと / 新たな負荷**

- MetricFlow を別 Cloud Run サービスとして運用する分、インフラと認証（OIDC）の構成要素が増える。
- Semantic Layer のカバレッジが定義済みメトリクスに限られ、未定義の問い（対戦履歴・球種別等）は従来ツールで補う必要がある。
- canary 段階（`USE_SEMANTIC_LAYER`）で、legacy 経路と二重に保守する期間が生じる。

## JD Alignment（この募集要件との対応）

- **FM★（prompt engineering / RAG / 外部ツールのオーケストレーション）**: SQL を LLM に書かせず「検証済みメトリクス定義を LLM が呼ぶ」構成は、pretrained model を中心に周辺を作り込む JD の方針と一致（[[052-build-around-pretrained-no-fine-tuning]]）。
- **AG★（tool orchestration）**: Semantic Layer をツールとして LLM に渡す 1-pass function calling は agentic 設計の要。

## References

- 設計プラン: [dbt_semantic_layer_implementation_plan.md](../plan_docs/dbt_semantic_layer_implementation_plan.md)
- 実装: [backend/app/services/semantic_layer_client.py](../../backend/app/services/semantic_layer_client.py) / [metricflow/dbt_project/models/semantic_models/](../../metricflow/dbt_project/models/semantic_models/)
- 旧経路: [backend/app/config/query_maps.py](../../backend/app/config/query_maps.py)（ハードコード辞書）
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[050-tools-return-raw-data-orchestrator-composes]], [[052-build-around-pretrained-no-fine-tuning]], [[035-feature-flag-canary-rollout]]
