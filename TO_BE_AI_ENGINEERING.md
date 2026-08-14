# DiamondLens — To-Be 提案書

**観点**: Andrew Ng が提唱する「すべてのソフトウェア開発者が持つべき 4 つの AI 工学スキル」を評価軸として、
本リポジトリの現状を診断し、あるべき状態（To-Be）を提案する。

**診断日**: 2026-08-14 / **対象**: `main` (e4e85ba)

---

## 0. 結論

このプロジェクトの問題は **「AI 工学の部品が足りない」ことではない**。むしろ部品は過剰なほど揃っている。
Judge が 5 種類、shadow eval、drift detection、golden dataset、failure taxonomy、token budget、
model registry — 大企業の ML プラットフォームに匹敵する語彙が実装されている。

問題は **それらのほぼ全てが本番の実行経路と接続されておらず、ループが閉じていない** ことである。

| 症状 | 証拠 |
|---|---|
| Judge 5 種 (1,303 行) がランタイムから**参照ゼロ** | `grep -rl judge app/` の結果、`app/` 内で judge を import するコードが存在しない。呼び出し元は `tests/` と `scripts/` のみ |
| 評価対象と本番対象が**別物** | `scripts/evaluate_llm_accuracy.py:26` は `ai_service._parse_query_with_llm` を評価。しかし本番は `use_legacy_chat_agent=False` (`settings.py:174`) により `ChatOrchestrator` 経路 |
| デプロイゲートが**コメントアウト** | `cloudbuild.yaml:37-49` の `llm-evaluation-gate` は全行コメント |
| CI が走らせるのは 20 ファイル中 **2 ファイル** | `.github/workflows/ci.yml` — しかも `test_llm_evaluation.py` は golden_dataset.json の**JSON 構造検証**であってモデル挙動の評価ではない |
| shadow eval が**恒久 OFF** かつ**旧経路にしか結線されていない** | `settings.py:127` `shadow_eval_enabled: False`。`shadow_logger` の呼び出し元は legacy の `ai_agent_service.py` のみ |
| データフライホイールが**手動スクリプトのまま** | feedback → `extract_golden_dataset.py` → 人手レビュー → `approve_to_golden.py` → golden。全て手動実行、スケジュール実行なし |

**つまり: 「制御可能なシステムに仕立て上げる」ための計器は作られたが、配線されていない。**
Ng の言う *disciplined evals とエラー分析ループ* が、コードとしては存在するが**プロセスとしては存在しない**。

以降、4 スキル軸ごとに現状と To-Be を示す。

---

## 1. スキル①「非決定性への対処」— 最大かつ致命的な欠落

### 1.1 現状: 評価が本番を測っていない

```
【評価している経路】                    【本番が使っている経路】
scripts/evaluate_llm_accuracy.py        POST /api/v1/qa/chat
  └─ ai_service._parse_query_with_llm     └─ ChatOrchestrator (675行)
       (単発 LLM で JSON パース)                └─ Gemini tool_use loop (MAX 6 iter)
                                                    └─ get_batter_stats_tool
                                                       get_pitcher_stats_tool
                                                       mlb_matchup_history_tool
                                                       mlb_matchup_analytics_tool
                                                       query_semantic_metrics_tool
```

この 2 つは**アーキテクチャが根本的に違う**。前者は「1 回の LLM 呼び出しで構造化パラメータを抽出」、
後者は「複数ターンのツール呼び出しループ」。前者の精度が 100% でも、後者の品質は一切保証されない。

さらに golden dataset は 14 件・`query_type` 4 種のみ (`season_batting`, `season_pitching`,
`batting_splits`, `career_batting`)。本番が扱う matchup 分析・semantic layer 経由の任意メトリクス・
戦略レポート (`/tactics`) は**評価カバレッジ 0%**。

### 1.2 To-Be: Eval Ladder（3 層の評価階層）

非決定性の統制は「1 つの精度指標」では不可能。**コスト・実行時間・確度が異なる 3 層**を分けて設計する。

```
┌─────────────────────────────────────────────────────────────────┐
│ L1: Contract Eval        毎 PR / LLM 呼び出しゼロ / 数秒          │
│   ツール引数スキーマ・SQL 生成・ガードレールの決定的検証           │
│   → pytest。既存 test_build_dynamic_sql / test_security を CI 復帰│
├─────────────────────────────────────────────────────────────────┤
│ L2: Behavioral Eval      毎 PR (差分時) / LLM 呼び出しあり / 数分  │
│   「質問 → どのツールを何の引数で呼んだか」を golden と照合        │
│   ★ ここが完全に欠落。ChatOrchestrator の trajectory を測る層     │
├─────────────────────────────────────────────────────────────────┤
│ L3: Online Eval          本番トラフィックに対し継続 / サンプリング │
│   Judge をリクエスト経路に結線し、品質を時系列で観測               │
│   → 既存 Judge 5 種の再利用先。BQ に蓄積 → 回帰検知               │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 To-Be コード: L2 — Trajectory Eval Harness（最重要・新規）

**核心的な発想の転換**: tool-calling エージェントで測るべきは「最終文章の正しさ」ではなく
**「正しいツールを、正しい引数で呼んだか」**。文章は LLM ごとに揺れるが、ツール呼び出しは決定的に判定できる。
これが非決定性を統計的に扱うための最も費用対効果の高い切り口である。

golden dataset のスキーマを、パース結果ベースから **trajectory ベース**へ拡張する:

```jsonc
// backend/tests/golden/trajectories.jsonl  (1 行 1 ケース)
{
  "id": "TJ-001",
  "query": "2025年のホームラン王は誰？",
  "expect": {
    "tool_calls": [
      { "name": "get_batter_stats_tool",
        "args_contains": { "season": 2025, "order_by": "homerun" },
        "args_absent": ["player_name"] }
    ],
    "max_iterations": 2,          // ループ暴走の回帰検知
    "must_mention": ["2025"],     // 応答本文の最小限の事実チェック
    "must_not_mention": ["申し訳", "わかりません"]
  },
  "tags": ["leaderboard", "p0"]
}
```

ハーネス本体（新規 `backend/tests/eval/harness.py`）の設計:

```python
@dataclass(frozen=True)
class TrajectoryResult:
    case_id: str
    passed: bool
    tool_call_score: float      # 期待ツール列との一致率
    arg_score: float            # 引数の一致率
    iterations: int
    latency_ms: float
    cost_usd: float
    failures: list[str]         # failureCategories.js と同一の語彙を使う

async def run_case(orch: ChatOrchestrator, case: dict) -> TrajectoryResult:
    """ChatOrchestrator を本番と同一構成で駆動し、tool_call 列を捕捉する。

    重要: モックしない。実 LLM を叩く。ただし BigQuery ツールは
    録画済みフィクスチャ (VCR 方式) に差し替え、データ変動の影響を排除する。
    → 「LLM の非決定性」だけを分離して測定できる。
    """
```

**3 回実行して分散を測る**ことを必須とする。単発実行の pass/fail は非決定的システムでは無意味であり、
`pass@1` ではなく **`pass^3`（3 回とも通る率）と分散**を指標にする。これが Ng の言う
「統計的な手法を用いて制御可能なシステムに仕立てる」の実体である。

```
判定基準（提案）
  P0 ケース: pass^3 = 100%        (壊れたら即デプロイ停止)
  P1 ケース: pass@1 >= 90%
  全体:      平均 iterations が前回比 +20% でアラート（コスト回帰の検知）
```

### 1.4 To-Be: Judge をランタイムに結線する（死蔵の解消）

既存の 5 Judge は捨てるべきではない。**接続先を変える**。

| Judge | 現状 | To-Be の役割 |
|---|---|---|
| `routing_judge` | 死蔵 | L3 オンライン。ツール選択の妥当性をサンプリング判定 → BQ |
| `synthesizer_judge` | 死蔵 | L3 オンライン。最終応答が取得データと矛盾しないか（hallucination 検知） |
| `reflection_judge` | 死蔵 | **ランタイム自己修正**。ツール結果が空/異常時に 1 回だけリトライ判断 |
| `llm_judge` | offline script のみ | L2 ハーネスの補助スコアラ（文章品質） |
| `drift_alert_judge` | 死蔵 | drift 検知バッチのノイズ抑制フィルタ |

結線は**非同期・fire-and-forget・サンプリング**が原則。ユーザ応答のレイテンシに 1ms も足してはならない:

```python
# ChatOrchestrator の応答確定直後
if should_sample(settings.online_judge_sample_rate):
    asyncio.create_task(
        _judge_and_log(request_id, query, tool_calls, final_answer)
    )  # 失敗しても本流に伝播させない
```

`reflection_judge` のみ同期的に使うが、**発火条件を厳密に絞る**（ツール結果が空、または
`MAX_TOOL_ITERATIONS` 到達時のみ）。無条件 reflection はコストを 2 倍にして品質は数 % しか上がらない。

### 1.5 To-Be: エラー分析ループの自動化

現状、フライホイールの部品は全て揃っている。**回っていないだけ**:

```
【現状 — 全て手動、実行実績なし】
 ユーザ Bad 評価 → BQ llm_logs
   ↓ 手動実行
 extract_golden_dataset.py → pending_review.json
   ↓ 人間が correct_expected を手書き
 approve_to_golden.py → golden_dataset.json
   ↓ 誰も動かさない
 evaluate_llm_accuracy.py（しかも評価先が死んだコード）

【To-Be — 週次自動 + 人間は判断だけ】
 ユーザ Bad 評価 + Judge 低スコア（L3）→ BQ
   ↓ Cloud Scheduler 週次
 失敗ケース抽出 + failure_category で自動クラスタリング
   ↓ GitHub Issue を自動起票（カテゴリ別に集約、件数の多い順）
 人間はカテゴリ単位で原因を判断（1 件ずつ見ない）
   ↓ 修正 PR に trajectory ケースを必ず 1 件追加（PR テンプレで強制）
 L2 ハーネスが回帰を永久に防ぐ
```

**設計上の要点**: 人間に「1 件ずつラベル付けさせない」こと。`failureCategories.js` の 6 分類
（`unregistered_metric_key` / `entity_resolution_error` / `missing_context` / `schema_violation` /
`over_extraction` / `type_misclassification`）は既に優れた taxonomy であり、これで自動クラスタリングして
**「今週最も多い失敗カテゴリ 1 つ」だけに集中する**運用にする。エラー分析は網羅性ではなく優先順位付けが本質。

---

## 2. スキル②「SWE 基礎 — トレードオフの舵取り」

### 2.1 現状: 移行の残骸が本番コードに堆積している

`ai_service_backup_02102026.py` — ファイル名に日付を持つバックアップが**バージョン管理下**にある。
Git がある以上これは不要であり、さらに悪いことに `_parse_query_with_llm` が 3 箇所
（`ai_service.py` / `ai_service_backup_*.py` / `analytics/batter_services.py` / `analytics/pitcher_services.py`）
に重複定義されている。どれが正なのかコードからは判別できない。

| 対象 | 行数 | 状態 |
|---|---|---|
| `ai_service_backup_02102026.py` | 1,032 | 完全な死コード。削除対象 |
| `ai_service_refactored.py` | 440 | import 元がコメントアウト (`ai_analytics_endpoints.py:7`)。死コード |
| `ai_agent_service.py` + `agents/supervisor_agent.py` | ~1,900 | `use_legacy_chat_agent=False` により到達不能。フラグごと削除対象 |
| `backend/test_cache.py`, `test_routing.py`, `verify_refactor.py` | — | `tests/` 外に散らばった一時スクリプト |
| **合計** | **約 3,200 行** | 読む人・エージェントを確実に誤誘導する |

これは Ng の指摘する *vibe coding のリスク* が現実化した形である。動くものは増えたが、
**「何が正で何が廃なのか」の判断コストが全開発者（と AI エージェント）に転嫁されている**。

### 2.2 To-Be: フラグの墓場を作らない規律

```python
# settings.py:173 — 自分でこう書いている
use_legacy_chat_agent: bool = Field(
    default=False,
    description="Phase 2 移行期間中のみ使用する切替フラグ。Phase 2-G 完了で削除。",
)
```

宣言通り**削除する**。移行フラグには**作成時に削除期限を書き、期限切れを CI で検出する**規律を入れる:

```python
# settings.py
@dataclass(frozen=True)
class TransitionalFlag:
    name: str
    remove_by: date      # この日を過ぎたら CI が落ちる
    owner: str
```

CI に `test_no_expired_flags` を追加すれば、フラグの墓場は構造的に発生しなくなる。
`use_semantic_layer`（`settings.py:165` のカナリアフラグ）も同じ管理下に置く。

### 2.3 To-Be: 依存の向きを固定する

現状 `bigquery_service.py` が**モジュール読み込み時に `bigquery.Client()` を生成**しており、
そのせいで `test_security.py` と `test_build_dynamic_sql.py`（合計 998 行、最も価値の高いテスト）が
**CI から除外**されている。CI 設定のコメントに、その事実が本人によって明記されている:

```yaml
# NOTE: test_security.py / test_build_dynamic_sql.py は
#       bigquery_service.py がモジュール読み込み時に
#       bigquery.Client() を生成するため GCP 認証が必要。
#       クライアントを遅延初期化にしてから対象へ戻す。
```

**これは 1 時間で直る。そして最もリターンの大きい 1 時間である。** セキュリティテスト 546 行が
CI で回っていない状態は、SQL インジェクション対策を実装しているのに検証していないのと同義。

```python
# To-Be: 遅延初期化 + DI
@lru_cache(maxsize=1)
def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=settings.gcp_project_id)

# 呼び出し側は get_bq_client() を都度呼ぶ。テストでは cache_clear() + monkeypatch。
```

### 2.4 To-Be: コスト・性能のトレードオフを可視化する

`llm_logger_service.py` は `input_tokens` / `output_tokens` / `cached_tokens` /
`estimated_cost_usd` / `llm_latency_ms` / `bigquery_latency_ms` を既に記録している。**計器は完成している**。
欠けているのは**それを見て意思決定する仕組み**:

- **PR ごとのコスト差分表示**: L2 ハーネス実行時の合計 token を PR コメントに自動投稿。
  「この変更でプロンプトが 800 token 増え、月間 $XX 増」が PR 上で見える状態にする。
- **p50/p95 レイテンシの SLO 化**: `total_latency_ms` に対し「p95 < 8s」等の目標を明示し、逸脱で警告。
- **Context Caching の効果測定**: 直近コミットで導入済み。`cached_tokens / input_tokens` の比率を
  ダッシュボード化しないと、キャッシュが効いているのか誰も判断できない。

---

## 3. スキル③「コーディングエージェントの活用」

### 3.1 現状: エージェントに与える文脈が存在しない

`.claude/` には `settings.local.json`（permission 4 行）のみ。**`CLAUDE.md` が存在しない**。

23,000 行のバックエンド、3,200 行の死コード、2 つの並存する chat 経路、
フラグで切り替わる semantic layer — この状況で文脈ファイルなしにエージェントを走らせれば、
**高確率で死んだ `ai_service.py` を編集する**。実際、本リポジトリの eval スクリプト自身が
まさにその誤り（死んだ経路を参照し続ける）を犯している。

### 3.2 To-Be: エージェント向け「地図」と「検証器」

Ng の指摘する *verifiers（自動化ループを閉じさせるための検証機能）* が、エージェント活用の核心である。
エージェントは「自分の変更が正しいか」を自力で確認できて初めて自律的に働ける。

**(a) `CLAUDE.md` — 何が正で何が廃かを最初の 30 行で伝える**

```markdown
## 本番の実行経路（ここだけが生きている）
POST /api/v1/qa/chat → ChatOrchestrator → tools/*.py → BigQuery
POST /api/v1/tactics → StrategyAgent

## 触ってはいけない死コード（削除予定・編集禁止）
ai_service_backup_02102026.py / ai_service_refactored.py / ai_agent_service.py

## 変更前に必ず読む
app/services/chat_orchestrator.py（チャットの唯一の入口）
app/config/query_maps.py（メトリクス語彙の単一の正）

## 検証コマンド（変更後は必ず全て通すこと）
make verify      # ruff + pytest(L1) + schema validation
make eval        # L2 trajectory eval（LLM 課金あり。プロンプト変更時は必須）
```

**(b) `Makefile` — 検証を 1 コマンドに畳む**

現状、検証手順が CI YAML・cloudbuild YAML・各スクリプトに散在し、人間もエージェントも
「何を実行すれば正しいと言えるのか」を知らない。単一のエントリポイントを作る:

```makefile
verify: lint test-unit validate-schema   # LLM 課金なし・数十秒。エージェントが毎回回す
eval:   verify eval-trajectory           # LLM 課金あり・数分。プロンプト/ツール変更時
```

これが揃って初めて、エージェントに「直せ」と言って**自己検証ループが閉じる**。

**(c) プロンプト変更を「コード変更」として扱う**

`prompt_registry.py` にバージョン管理の枠はある（`"chat_orchestrator_system": "v1"`）が、
実体はコード内インライン定義。To-Be:

- プロンプトを `prompts/*.md` に外出しし、**変更時は L2 eval を必須 CI ゲートにする**
- PR に「プロンプト差分」と「eval スコア差分」を並べて表示

プロンプトは最も壊れやすく、最も検証されていないコードである。ここを型どおりのレビュー対象にすることが、
非決定性の統制とエージェント活用の両方に効く。

---

## 4. スキル④「ビルドの形成 — 何を作るべきか」

### 4.1 現状: 機能数に対して「効いているか」の指標がない

フロントエンドのコンポーネントは 40 個超（`PitcherWhiffPredictor`, `PlayerSegmentation`,
`StuffPlus`, `HotSlumpDashboard`, `LiveMonitorBoard`, `StrategyReportPage` …）。
バックエンドのエンドポイント群は 22 ファイル。技術的野心は非常に高い。

一方で、**どの機能が使われ、どの機能が価値を出しているかを測る仕組みがない**。
`usage_stats_service.py` と `UsageDashboard.jsx` はあるが、測っているのは
「LLM をどれだけ使ったか」（コスト側）であって「ユーザが何を得たか」（価値側）ではない。

これは Ng の言う *「実装者から構築者への転換」* が未達な状態である。
実装速度が上がった結果、**作る対象の取捨選択が追いついていない**。

### 4.2 To-Be: 「北極星指標」と機能の棚卸し

**提案する北極星指標**: *週あたり「回答に満足した分析セッション」数*
（= Good 評価、または Bad なしで 3 ターン以上継続したセッション）

これを定義すると、意思決定が自動的に決まる:

| 判断 | 現状（指標なし） | To-Be（指標あり） |
|---|---|---|
| 新機能を作るか | 技術的に面白いか | 北極星指標を動かすか |
| 既存機能を消すか | 消せない（愛着） | 3 ヶ月使用ゼロなら削除 |
| Judge を回すか | 判断不能 | 品質 → 満足度への寄与を測って決める |

**具体的なアクション**:

1. **機能ごとの利用率を 2 週間計測**し、下位を明示的に廃止候補にする。
   40 コンポーネントを維持するコストは、AI で実装速度が上がっても消えない（むしろレビュー負荷は増える）。
2. **`/tactics`（戦略レポート）を主役に据える仮説を検証する**。
   統計を引くだけなら Baseball Savant で足りる。このプロダクト固有の価値は
   「複数データを統合して**戦術的示唆**を出す」ことにあり、そこが差別化点になり得る。
   MVP として `/tactics` の満足度だけを 2 週間追い、伸びるなら他機能を削ってでも集中する。
3. **オンボーディングの欠落**: `QuickQuestions.jsx` はあるが、初回ユーザが
   「このアプリに何を聞けるのか」を理解する導線が弱い。tool-calling 型 AI プロダクトの
   最大の離脱要因は「何を聞けばいいか分からない」であり、ここは機能追加より投資対効果が高い。

---

## 5. 実行ロードマップ（優先度順）

コストと効果で並べた。**上から 3 つで、このプロジェクトの信頼性は質的に変わる。**

### Phase 0 — 出血を止める（1〜2 日）

| # | 作業 | 効果 |
|---|---|---|
| 1 | `bigquery.Client()` を遅延初期化にし、`test_security.py` / `test_build_dynamic_sql.py` を CI に復帰 | **998 行の最重要テストが回り始める。最大の費用対効果** |
| 2 | 死コード 3,200 行を削除（backup / refactored / legacy agent / 散在スクリプト） | 人間と AI エージェントの誤読を構造的に排除 |
| 3 | `use_legacy_chat_agent` フラグを削除、`CLAUDE.md` と `Makefile` を新設 | エージェントが正しい場所を編集できるようになる |

### Phase 1 — 評価を本番に合わせる（3〜5 日）

| # | 作業 | 効果 |
|---|---|---|
| 4 | trajectory golden dataset を新設（P0 20 件 / P1 30 件） | 本番経路を初めて測れるようになる |
| 5 | L2 ハーネス実装（BQ は VCR 固定、LLM は実呼び出し、3 回実行で分散測定） | 非決定性を**数値として**扱える |
| 6 | `cloudbuild.yaml` の eval gate を L2 に差し替えて**復活** | デプロイが品質で守られる |

### Phase 2 — ループを回す（1〜2 週）

| # | 作業 | 効果 |
|---|---|---|
| 7 | Judge をオンライン結線（非同期・サンプリング）→ BQ 蓄積 | 死蔵 1,303 行が価値を生み始める |
| 8 | 週次エラー分析ジョブ（自動クラスタリング → GitHub Issue 起票） | 改善が属人的な思いつきでなくなる |
| 9 | コスト/レイテンシの PR 差分表示、Context Caching 効果の可視化 | トレードオフを見て判断できる |

### Phase 3 — 何を作るかを決める（継続）

| # | 作業 |
|---|---|
| 10 | 北極星指標の定義と計測、機能利用率の棚卸し、下位機能の廃止 |
| 11 | `/tactics` に絞った MVP 検証、オンボーディング導線の改善 |

---

## 6. 意図的に提案しなかったこと

過剰設計を避けるため、以下は**今は不要**と判断した。理由も残す。

- **LangGraph / エージェントフレームワークへの再移行** — 一度 `ChatOrchestrator` へ単純化した判断は正しい。
  素の SDK + tool loop で足りている。フレームワークは評価基盤が整ってから検討すべきで、順序が逆になる。
- **RAG の高度化（re-ranking 等）** — `rag_service.py` は存在するが、まず L2 で
  「RAG が実際に効いているか」を測るのが先。測らずに高度化するのは典型的な浪費。
- **マルチエージェント・オーケストレーション** — 現状の単一 tool loop で品質問題が測定できていない段階で
  エージェントを増やせば、非決定性が乗算的に増えるだけ。Phase 2 完了後に再評価。
- **マイクロサービス分割** — 単一 Cloud Run で捌けている。分割はコストのみ増える。

---

## 7. 総括

このプロジェクトの技術的野心と実装量は際立っている。Judge、drift detection、shadow eval、
semantic layer、model registry — これらを実装できる開発者は多くない。

しかし Ng の 4 スキルの観点で見たとき、**最も本質的なもの（非決定性を統計的に統制するループ）だけが
唯一「部品はあるが動いていない」状態**にある。評価は死んだコードを測り、Judge は誰にも呼ばれず、
ゲートはコメントアウトされている。

したがって To-Be の中心は **新機能でも新技術でもなく、「既に書いたものを本番に配線し、ループを閉じること」** である。
Phase 0 の 3 項目（テスト復帰・死コード削除・エージェント文脈整備）は合計 2 日程度で完了し、
それだけでこのリポジトリは「作られたもの」から「制御されているもの」へ変わる。
