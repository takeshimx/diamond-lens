# Architecture Decision Records (ADR)

Diamond Lens の重要なアーキテクチャ上の意思決定を記録するディレクトリです。
このファイルは **索引（候補一覧）** です。各 ADR の本文は別ファイル（`NNN-kebab-title.md`）として後日執筆します。

> 状態: 🟡 索引のみ生成済み（本文は未執筆）。
> 各行の「決定 vs 代替案」は執筆の出発点（seed）であり、確定文ではありません。

---

## ADR とは / なぜ書くか

ADR は「ある時点で、どの選択肢を、なぜ選んだか」を1ファイル1決定で残す軽量ドキュメントです。
コードからは「何をしたか（what）」は読めても「なぜそうしたか（why）／何を捨てたか（trade-off）」は失われます。ADR はその why を保全します。

このプロジェクトでは特に次の理由で価値があります。

- **面接・採用文脈**: 「BigQuery を選んだ理由は？Airflow ではなく Cloud Workflows にした理由は？」に、判断根拠と trade-off で即答できる素材になります（FDE は技術選定の justification が問われます）。
- **既に参照だけ存在**: `README_architecture.md` が ADR-001〜004 をリンク済みなのに**実ファイルが無い**（リンク切れ）。まずこの4本を backfill する必要があります。
- **意思決定の鮮度**: 2026-05-17 に chat 経路を大きく refactor（後述 ADR-010）したばかりで、「なぜ LangGraph を捨てたか」を今記録しないと忘れます。

---

## 命名・運用規約

- **ファイル名**: `NNN-kebab-case-title.md`（例: `001-use-bigquery.md`）。`README_architecture.md` の既存リンクに合わせる。
- **番号**: 連番。一度振ったら欠番にしても再利用しない。
- **状態 (Status)**: `Proposed` → `Accepted` → （必要なら）`Superseded by ADR-NNN` / `Deprecated`。
- **1 ADR = 1 決定**。複数決定を1ファイルに混ぜない。
- 決定を覆したら、古い ADR は消さず `Superseded` にして新 ADR から参照（履歴を残す）。

### テンプレート（Michael Nygard 形式 / コピーして使用）

```markdown
# ADR-NNN: <決定のタイトル>

- Status: Proposed | Accepted | Superseded by ADR-XXX
- Date: YYYY-MM-DD
- Deciders: <意思決定者>

## Context（背景・課題）
何が問題で、どんな制約（コスト/レイテンシ/運用/スキル/時間）があったか。

## Decision（決定）
何を採用したか。

## Alternatives Considered（検討した代替案）
- 案A: 採用しなかった理由
- 案B: 採用しなかった理由

## Consequences（結果・トレードオフ）
- 良くなったこと / 悪くなったこと / 新たに生じた運用負荷・技術的負債。

## JD Alignment（この募集要件との対応）
このプロジェクトを語る対象 JD（GenAI Forward Deployed Engineer, Google Cloud）の
どの要件に対応するか（下記 JD コード）。面接での話法に直結。

## References
関連 PR・plan_doc・README セクションへのリンク。
```

---

## JD 要件コード（マッピング凡例）

対象求人 **「Forward Deployed Engineer, Generative AI, Google Cloud」** の記載要素を 7 コードに整理しました。
各 ADR の **JD 列**にこのコードを付与します。**★ = JD 本文がその語を明示的に名指ししている**（最強マッチ）。

| コード | JD 記載要素（原文ベース） | JD 箇所 |
|-------|--------------------------|---------|
| **AG** | agentic workflows / multi-agent / **MCP servers** / **LangGraph・ReAct・self-reflection・hierarchical delegation** / tool orchestration | resp#1, preferred qual |
| **EV** | **evaluation pipelines & observability frameworks**（accuracy / **safety** / latency） | resp#3 |
| **LM** | **LLM-native metrics**（tokens/sec, **cost-per-request**）・**state management**・**granular tracing** | preferred qual |
| **GC** | architect・deploy・manage solutions on **Google Cloud Platform** | min-qual, resp#2 |
| **INT** | live infra 連携 / **legacy data silos** / **security perimeters** への統合 | resp#2 |
| **FM** | pretrained foundation model 周辺（**prompt engineering** / **RAG** / **fine-tuning** / orchestrating external tools） | min-qual |
| **BP** | Google-grade best practices / repeatable field patterns → reusable modules・feature requests | resp#4, resp#5 |
| **—** | JD と直接の対応は薄い（堅実だが本 JD の主眼ではない） | — |

---

## ADR 候補一覧（索引）

凡例 —
**Status**: ✅ Accepted（実装済み・未文書化／本文 backfill 対象） / 🟡 Proposed（未決定・レビュー後判断） /
**Tier**: ⭐P1（面接で語る価値が高い・最優先で執筆） / P2 / P3 /
**JD**: 上記 JD 要件コード（★ = 明示的に名指しされた語）

> **一次情報の所在**:
> - プロダクト全体 → `README.md` / `README_JP.md`
> - インフラ・GCP・データフロー → `README_architecture.md`
> - **AI / LLM レイヤー（C・D セクションおよび 013/015/016/032/049/050/051）→ `README_ai_architecture.md`** ← LLM 系 ADR を書くときの主たる根拠
> - 個別機能の設計判断 → `docs/plan_docs/*.md`

### A. データ & ストレージ

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 001 | Use BigQuery as Data Warehouse | サーバレス列指向DWH vs 自前 PostgreSQL/Snowflake。DWH 選定は table-stakes | ✅ | P2 | GC★ INT★ | `README_architecture.md` GCP Resources / 既存リンク |
| 005 | Star schema + dbt 4-layer medallion | staging→intermediate→core→marts vs フラットな手書きSQL。JD は次元モデリング非重視 | ✅ | P2 | INT★ | `README_architecture.md` Data Transformation Layers |
| 006 | Partition by `game_date` + cluster by player/pitcher/batter | 課金/スキャン削減の物理設計 vs 無パーティション | ✅ | P2 | — | `README_architecture.md` Key Tables |
| 007 | Incremental materialization for fact tables | 差分更新 vs 毎回フルリフレッシュ | ✅ | P2 | — | `README_architecture.md` Data Transformation Layers |
| 008 | fact→mart 移行と dual-key（idfg→mlbid, season≥2026 境界） | mlbid 統一サロゲートキー vs 旧 idfg 併存 | ✅ | P2 | — | `DATA_LAYER_REDESIGN_PROPOSAL_JP.md` |

### B. パイプライン & オーケストレーション

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 002 | Separate ETL / dbt / App repos + git submodule | ポリレポ + submodule vs モノレポ | ✅ | P2 | BP INT | 既存リンク / `README.md` dbt Submodule Workflow |
| 003 | Weekly Batch Processing Strategy | 週次バッチ vs ストリーミング/日次 | ✅ | P2 | GC★ | 既存リンク / `README_architecture.md` |
| 004 | Cloud Workflows over Airflow | マネージドサーバレス vs Composer/Airflow 常駐 | ✅ | P2 | GC★ | 既存リンク / Cost Breakdown |

### C. LLM / エージェント

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 009 | dbt Semantic Layer (MetricFlow) over query_maps ベースの固定 SQL 構築 | メトリクス定義の SSOT 化（dbt 一本化）vs query_maps とアプリ側 SQL 構築の二重化 | ✅(canary) | ⭐P1 | AG★ FM★ | `dbt_semantic_layer_implementation_plan.md` / README #22 |
| 010 | ChatOrchestrator (function calling, 1 LLM call) replaces Supervisor + 4 LangGraph sub-agents | raw google-genai + function calling ループ vs LangGraph 4エージェント（4→1 call）。NLU を orchestrator の LLM に移管 | ✅(2026-05-17) | ⭐P1 | AG★ | `README_ai_architecture.md` §1,§9 / `CHAT_ORCHESTRATOR_REFACTOR_PLAN.md` |
| 011 | Retain LangGraph only for StrategyAgent (Plan-and-Execute + parallel fan-out) | 横断分析だけ多段グラフ維持 vs 全廃 | ✅ | ⭐P1 | AG★ | `MATCHUP_STRATEGY_REPORT_PLAN.md` |
| 012 | Reflection loop with classified, bounded retries | リトライ可/不可をエラー分類 + 上限2 vs 無制限自己修正 | ✅ | ⭐P1 | AG★ | README #4 / `test_reflection_loop.py` |
| 013 | Centralized LLM Gateway + cost/token telemetry | 全呼び出しを `llm_gateway_service` 集約 vs 各所で直叩き | ✅ | ⭐P1 | LM★ EV | README #24 LLM Usage Cost Dashboard |
| 015 | Gemini context caching | 固定prefixをcache（〜1/10課金）vs 毎回フル課金。sha256キー / TTL自動再作成 / fail-open | ✅ | ⭐P1 | LM★ | `README_ai_architecture.md` §2.5 / `prompt_cache_service.py` |
| 016 | Token budget pool separation (chat / report / shared) | プール分離で report が chat を枯渇させない vs 単一プール | ✅ | ⭐P1 | LM★ | `README_ai_architecture.md` §9.5 / `token_budget_service.py` |
| 052 | Build around pretrained models — no fine-tuning | prompt-eng + Semantic Layer + context caching で対応 vs SFT/LoRA。"あえて FT しない判断" を trade-off で語れる | ✅ | ⭐P1 | FM★ | 全体方針 / AI Eng レビュー #25 |
| 014 | Prompt-as-config (external txt + prompt_registry + versioning) | プロンプト外部化・版管理 vs コード直書き | ✅ | P2 | FM★ | README #5 |
| 050 | Tools return raw data; orchestrator owns response composition | `output_format='data'` でツールは生データ返却に専念、応答合成は orchestrator vs ツール内で応答生成LLMも呼ぶ（旧2段） | ✅ | P2 | AG★ | `README_ai_architecture.md` §1 設計の要 |
| 017 | Default model = Gemini 2.5 Flash (single-tier) | 単一モデル固定 vs 難易度別 cascade（→ ADR-045 で再検討） | ✅/再検討 | P3 | LM | README Technical Stack |

### D. 評価 & 品質

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 018 | LLM-as-a-Judge (5-panel) offline evaluation | 多次元 Judge で自動採点 vs 人手のみ | ✅ | ⭐P1 | EV★ | README #10 |
| 019 | Shadow evaluation (champion / challenger) | 本番並走でサンプリング比較 vs オフラインのみ | ✅ | ⭐P1 | EV★ | `SHADOW_EVALUATION_PLAN.md` |
| 020 | CI evaluation gate (golden dataset ≥80% parse accuracy) | デプロイをブロックする品質ゲート vs 手動確認。**※現状 cloudbuild で全ゲート comment-out＝無効。golden は14ケース** | ✅(無効化中) | ⭐P1 | EV★ BP | `README_ai_architecture.md` §10 / README CI/CD STEP 1.5 |
| 021 | HITL feedback → golden dataset flywheel | 👎抽出→人手レビュー→golden昇格 vs 静的テストセット | ✅ | P2 | EV FM | `README_ai_architecture.md` §6 / README #6 |
| 022 | Schema validation gate (query_maps vs live BigQuery) | 実スキーマ突合をCIで強制 vs 実行時に発覚（※同上 comment-out 中） | ✅(無効化中) | P2 | EV BP | README CI/CD STEP 1 |

### E. ML / MLOps

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 025 | Data drift detection (KS/PSI/mean-shift) + CI drift gate | 統計的ドリフト検知でデプロイ判定 vs 監視なし | ✅ | ⭐P1 | EV★ | README #8 / CI/CD STEP 1.6 |
| 026 | Embedding quality-warning + semantic drift via BQ VECTOR_SEARCH | サーバレス vector search vs 専用 vector DB 常駐 | ✅ | ⭐P1 | FM★ LM | README #11, #12 |
| 024 | Model Registry (GCS + BQ metadata) + promotion | バージョン管理 + active昇格 vs その場fit | ✅ | P2 | — | README #8 |
| 028 | XGBoost for Stuff+ / Pitching+ / Pitching++ | 勾配ブースティング回帰 vs 線形/DL | ✅ | P2 | — | README #9 |
| 023 | 3-layer ML separation, no PyTorch in prod | 学習/推論/応用を分離・本番軽量 vs モノリシック(3.9GB)。JD は *pretrained model 中心* ゆえ弱関連 | ✅ | P3 | — | README ML Model Architecture |
| 027 | FT-Transformer encoder + K-means for segmentation | 自己教師あり表現学習 vs 素の K-means | ✅(実験) | P3 | — | README #3 / `test_ft_transformer.py` |

### F. アプリ / インフラ / セキュリティ

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 029 | Cloud Run (scale-to-zero) over GKE | サーバレスコンテナ vs Kubernetes 運用 | ✅ | ⭐P1 | GC★ | README Infrastructure / Cost |
| 031 | Firebase Auth (public) + service-to-service OIDC (internal) | 二経路認証 vs 単一認証 | ✅ | ⭐P1 | INT★ | README Security / #22 |
| 032 | Snowflake trace_id + structured JSON logging (ContextVar 伝搬) | 相関ID付き構造化ログ vs 素のprint | ✅ | ⭐P1 | LM★ EV | `SNOWFLAKE_TRACE_ID_PLAN.md` / `README_ai_architecture.md` §9 |
| 037 | Terraform brownfield import + Cloud Build multi-gate CI/CD | 既存リソースimport + 多段ゲート vs 新規構築/手動 | ✅ | ⭐P1 | GC★ BP | `TERRAFORM_INTEGRATION_GUIDE.md` |
| 040 | MCP server exposure (Claude Desktop / Cursor) | Model Context Protocol で外部AIから利用 vs 自前APIのみ | ✅ | ⭐P1 | AG★ | README Technical Features |
| 049 | Security Guardrail: 3-layer pre-LLM input defense | injection / off-topic / 長さ・構造異常 を LLM 到達前に検査 vs 素通し・出力後フィルタのみ | ✅ | ⭐P1 | EV★ | `README_ai_architecture.md` §7 / `security_guardrail.py` |
| 030 | In-memory rate limit + token budget (single-container) | Redis不要の割り切り vs 分散カウンタ（→ ADR-048 で再検討） | ✅/再検討 | P2 | LM | README #7 |
| 033 | SSE streaming for agent reasoning | Server-Sent Events で推論逐次表示 vs 一括返却 | ✅ | P2 | EV | README Streaming API |
| 034 | In-memory Trie autocomplete over BigQuery `LIKE` | 起動時Trie常駐 + 人気度順 vs 毎打鍵 `LIKE '%q%'`。latency 最適化だが機能単位 | ✅ | P2 | — | `SEARCH_AUTOCOMPLETE_PLAN_VOL1.md` / README #23 |
| 035 | Feature-flag canary rollout convention | env-var で新旧経路切替・即ロールバック vs 一斉切替 | ✅ | P2 | BP | README #22, #23 |
| 036 | Live data via MLB Stats API, no DB persistence | リクエスト毎ライブ取得 vs キャッシュ/DB保存 | ✅ | P3 | — | README #14, #17 |
| 038 | Trivy security scan gate | HIGH/CRITICAL CVE でデプロイ阻止 vs スキャンなし | ✅ | P3 | BP | README CI/CD STEP 4,8 |
| 039 | Secrets outside Terraform (Secret Manager + GitHub PAT) | Secret を IaC 外で管理 vs tfstate に格納 | ✅ | P3 | BP | README Infrastructure |

### G. 観測性 / 運用

| ADR | タイトル | 決定 vs 代替案（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|----------------------|--------|------|----|---------|
| 041 | SLO + error budget policy | SLO定義とエラーバジェット運用 vs 無定義 | ✅ | P2 | EV BP | `docs/SLO.md` |
| 043 | Cloud Monitoring custom metrics over Prometheus | マネージド監視 vs Prometheus 自前運用 | ✅ | P2 | EV GC★ | `docs/MONITORING.md` / README Monitoring |
| 042 | Incident response runbook | 障害対応手順の明文化 vs 都度対応 | ✅ | P3 | BP | `docs/INCIDENT_RESPONSE.md` |
| 051 | Append-only LLM logging (daemon thread) + feedback via placeholder INSERT | 非同期 fire-and-forget 書込・UPDATE回避 vs 同期書込/直接UPDATE（BQ streaming buffer 制約対応。※プロセス即死でログ欠落リスクは残る） | ✅/再検討 | P3 | EV LM | `README_ai_architecture.md` §3 |

### H. 今後の意思決定（Proposed — DDIA / AI Engineering レビュー由来、未決定）

| ADR | タイトル | 論点（seed） | Status | Tier | JD | 主な出典 |
|-----|---------|-------------|--------|------|----|---------|
| 044 | Idempotency keys for POST / LLM calls | 二重課金・二重記録の防止をどう入れるか | 🟡 | P2 | BP | DDIA レビュー Ch.7 |
| 045 | Model cascade (Flash → Pro escalation) | 低信頼時のみ上位モデルへ昇格するか | 🟡 | P2 | LM | AI Eng レビュー Ch.7 |
| 047 | RAG chunking + multilingual embeddings + reranking | BQ ベクトル検索 + カテゴリ事前フィルタ + LLM リランク vs ChromaDB 復活 / 想定質問の手書き / 閾値調整のみ（命中@5 0.800→1.000, MRR 0.658→0.925 を実測） | ✅ | P2 | FM★ | AI Eng レビュー Ch.7 |
| 046 | Semantic response cache | 既存 embedding 基盤を応答キャッシュに転用するか | 🟡 | P3 | LM | AI Eng レビュー Ch.7 |
| 048 | Distributed rate limit / circuit breaker standardization | 多インスタンス整合とリトライ/CB の共通化 | 🟡 | P3 | BP GC | DDIA Ch.1 / ADR-030 再検討 |

---

## JD 要件 × ADR 逆引きマトリクス

各 JD 要件を、対応 ADR（★ = 明示的に名指しされた語に対応する ADR）で引けるようにした逆引き表です。
面接で「この要件、満たしてます」と言うときに、**どの ADR を語ればいいか**を即引きできます。

| JD コード | JD 要件（要約） | 対応 ADR（★ = 直名指し） |
|----------|----------------|------------------------|
| **AG** | agentic / multi-agent / MCP / LangGraph・self-reflection・tool orchestration | **010★, 011★, 012★, 040★(MCP), 009★, 050★** |
| **EV** | evaluation pipelines & observability（accuracy/safety/latency） | **018★, 019★, 020★, 049★(safety), 025★, 013, 032, 033, 041, 043, 051** |
| **LM** | LLM-native metrics（cost-per-request）・state management・granular tracing | **013★, 015★, 016★(cost+state), 032★(tracing), 017, 026, 030, 045, 046, 051** |
| **GC** | architect・deploy・manage on GCP | **029★, 037★, 003★, 004★, 043★, 001★, 048** |
| **INT** | live infra / legacy data silos / security perimeters | **031★(perimeter), 001★, 005★, 002** |
| **FM** | prompt-eng / RAG / fine-tuning / tool orchestration（pretrained 中心） | **009★, 014★(prompt), 052★(no-FT), 026★(RAG), 047★(RAG), 021** |
| **BP** | Google-grade best practices / repeatable patterns | **037, 020, 022, 002, 035, 038, 039, 041, 042, 044, 048** |

---

## 推奨執筆順（面接準備の優先度）

Tier は **この JD（GenAI Forward Deployed Engineer）の重み付けに合わせて再校正済み**。執筆順も JD 直結度の高い順に並べます。

1. **エージェント中核（AG / JD 最重視）**: **010** ChatOrchestrator → **011** StrategyAgent(LangGraph) / **012** Reflection(self-reflection) / **040** MCP server / **050** tool/合成分離 / **052** あえて FT しない判断
2. **評価・観測・安全性（EV）**: **018** Judge / **019** shadow / **020** CI gate / **049** Guardrail(safety) / **025** drift / **032** granular tracing
3. **LLM-native コスト/レイテンシ/状態（LM）**: **013** Gateway(cost-per-request) / **015** context caching / **016** token budget pools
4. **GCP 構築・統合（GC / INT）**: **029** Cloud Run / **037** Terraform+CI/CD / **031** OIDC(security perimeter) / **009** Semantic Layer / **026** serverless vector search
5. **リンク切れ backfill（優先度は下げたが必須）**: **001–004**（`README_architecture.md` の切れリンク解消。headline ではなく整備タスク）

> 逆に **001/005/006/007/008（DWH・次元モデル）, 023/024/027/028（自前 ML 学習）** は技術的には堅実だが、本 JD は *pretrained foundation model を中心に構築* する役割のため **意図的に Tier を下げた**（JD 列が「—」または非★）。

---

## メンテナンス指針

- 重要な技術判断をしたら、その PR と同じタイミングで ADR を1本追加する（`README_architecture.md` Contributing にも明記済み）。
- `README_architecture.md` の「Architecture Decisions」節は、本ファイルと番号・タイトルを同期させる。
- 索引（このファイル）と本文ファイルの粒度がズレたら、索引を正として本文側を更新する。
- 対象 JD が変わったら、**JD 要件コード**と各行の **JD 列**を貼り替える（Tier もそれに追従させる）。
