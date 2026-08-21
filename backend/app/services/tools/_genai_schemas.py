"""
google-genai SDK 用の FunctionDeclaration スキーマ定義。
@tool デコレータ付きの本体関数はそのまま使い回し、SDK 渡し用のスキーマのみここで管理する。

設計判断:
- LangChain @tool は Pydantic 由来の docstring/型ヒントから自動でスキーマを作るが、
  google-genai は明示的な FunctionDeclaration が必要。
- 自動変換ライブラリ (langchain → genai) を入れると依存が増えるため、Phase 2 では手書きで割り切る。
- ツール本体の引数を変更したら、ここも同期で更新する責任を負う（Phase 3 で自動化検討）。
"""
from google.genai import types


GET_BATTER_STATS_DECL = types.FunctionDeclaration(
    name="get_batter_stats_tool",
    description=(
        "打撃成績を BigQuery から取得する。"
        "**呼び出し元の LLM (ChatOrchestrator) がユーザー質問を解析し、ここに構造化引数を直接渡すこと**。"
        "ツール内では NLU をスキップし、与えられた引数で動的 SQL を組み立てて結果を返す。"
        "output_format='data' (デフォルト) は生データを返す。応答文の生成は呼び出し元 LLM が行う。"
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "query_type": {
                "type": "STRING",
                "enum": ["season_batting", "batting_splits", "career_batting"],
                "description": "年指定+状況なし→season_batting / 年指定+状況あり→batting_splits / 通算→career_batting",
            },
            "metrics": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "取得指標 (例: ['homerun'], ['batting_average'], ['main_stats'])",
            },
            "name": {
                "type": "STRING",
                "description": "選手名 (英語フルネーム、例: 'Shohei Ohtani')",
            },
            "season": {
                "type": "INTEGER",
                "description": "対象シーズン (例: 2026)。通算/全シーズンの場合は省略。",
            },
            "split_type": {
                "type": "STRING",
                "enum": [
                    "risp", "bases_loaded", "runner_on_1b", "inning",
                    "pitcher_throws", "pitch_type", "game_score_situation", "monthly",
                ],
                "description": "状況別カット (query_type='batting_splits' 時に指定)",
            },
            "inning": {
                "type": "ARRAY",
                "items": {"type": "INTEGER"},
                "description": "split_type='inning' 用 (例: [1], [7,8,9])",
            },
            "strikes": {"type": "INTEGER"},
            "balls": {"type": "INTEGER"},
            "game_score": {
                "type": "STRING",
                "description": "例: 'one_run_lead', 'one_run_trail', 'four_plus_run_lead'",
            },
            "pitcher_throws": {
                "type": "STRING",
                "enum": ["LHP", "RHP"],
            },
            "pitch_type": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "order_by": {"type": "STRING"},
            "limit": {"type": "INTEGER"},
            "output_format": {
                "type": "STRING",
                "enum": ["data", "sentence", "table"],
                "description": "'data' (デフォルト): 生データ。'table': UI 表形式。'sentence': ツール内 LLM 文章化 (非推奨)",
            },
            "query": {
                "type": "STRING",
                "description": "[後方互換] 構造化引数を渡せない時のみ。指定すると tool 内で NLU LLM が走る (旧挙動)。",
            },
        },
        # query_type が無いと _build_dynamic_sql が (None, {}) を返しデータが取れない。
        # リーダーボード系の質問で LLM が省略する事象を trajectory eval (TJ-001) が検出したため必須化。
        "required": ["query_type"],
    },
)

GET_PITCHER_STATS_DECL = types.FunctionDeclaration(
    name="get_pitcher_stats_tool",
    description=(
        "投球成績を BigQuery から取得する。"
        "**呼び出し元の LLM がユーザー質問を解析し、ここに構造化引数を直接渡すこと**。"
        "ツール内では NLU をスキップする。"
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "query_type": {
                "type": "STRING",
                "enum": ["season_pitching", "pitching_splits", "career_pitching"],
            },
            "metrics": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "取得指標 (例: ['era'], ['strikeouts'], ['main_stats'])",
            },
            "name": {"type": "STRING", "description": "投手名 (英語フルネーム)"},
            "season": {"type": "INTEGER"},
            "split_type": {
                "type": "STRING",
                "enum": [
                    "risp", "bases_loaded", "runner_on_1b", "inning",
                    "game_score_situation", "monthly",
                ],
            },
            "inning": {"type": "ARRAY", "items": {"type": "INTEGER"}},
            "strikes": {"type": "INTEGER"},
            "balls": {"type": "INTEGER"},
            "game_score": {"type": "STRING"},
            "pitch_type": {"type": "ARRAY", "items": {"type": "STRING"}},
            "order_by": {"type": "STRING"},
            "limit": {"type": "INTEGER"},
            "output_format": {
                "type": "STRING",
                "enum": ["data", "sentence", "table"],
                "description": "'data' (デフォルト) / 'table' / 'sentence' (非推奨)",
            },
            "query": {
                "type": "STRING",
                "description": "[後方互換] 自然言語クエリ。指定すると tool 内で NLU LLM が走る。",
            },
        },
    },
)

MATCHUP_HISTORY_DECL = types.FunctionDeclaration(
    name="mlb_matchup_history_tool",
    description="特定の打者と投手の過去の全対決履歴を取得する。打席ごとの配球の流れ、結果、コース等を取得できる。",
    parameters={
        "type": "OBJECT",
        "properties": {
            "batter_name": {"type": "STRING", "description": "打者のフルネーム（例: 'Shohei Ohtani'）"},
            "pitcher_name": {"type": "STRING", "description": "投手のフルネーム（例: 'Yu Darvish'）"},
        },
        "required": ["batter_name", "pitcher_name"],
    },
)

MATCHUP_ANALYTICS_DECL = types.FunctionDeclaration(
    name="mlb_matchup_analytics_tool",
    description="特定の打者と投手の球種別対戦相性サマリー（打率・OPS・空振り率・球速等）を取得する。",
    parameters={
        "type": "OBJECT",
        "properties": {
            "batter_name": {"type": "STRING", "description": "打者のフルネーム"},
            "pitcher_name": {"type": "STRING", "description": "投手のフルネーム"},
        },
        "required": ["batter_name", "pitcher_name"],
    },
)

QUERY_SEMANTIC_METRICS_DECL = types.FunctionDeclaration(
    name="query_semantic_metrics_tool",
    description=(
        "dbt Semantic Layer (MetricFlow) から打撃・投手メトリクスを取得する。"
        "**USE_SEMANTIC_LAYER=true** 時の唯一のデータ取得経路。"
        "**呼び出し元の LLM が ユーザー質問を解析し、ここに構造化引数を直接渡すこと**。"
        "metrics 名は Semantic Layer 登録済みの正規名のみ使用可。"
        "選手フィルタは player_name (英語フルネーム文字列) を渡せば backend 側で Jinja に展開する。"
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "metrics": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": (
                    "取得するメトリクス名のリスト (Semantic Layer 登録済み正規名)。"
                    "例: ['batting_average', 'ops_metric', 'home_runs_total']。"
                    "短縮形 (avg, ops, hr) は禁止。"
                ),
            },
            "entity_type": {
                "type": "STRING",
                "enum": ["player", "pitcher"],
                "description": "'player' (打者用 batter_season) または 'pitcher' (投手用 pitcher_season)",
            },
            "mlbid": {
                "type": "INTEGER",
                "description": (
                    "MLB ID (整数)。確実に判っている場合のみ指定。"
                    "判らない場合は省略し、代わりに player_name (英語フルネーム) を渡すこと。"
                ),
            },
            "player_name": {
                "type": "STRING",
                "description": (
                    "選手名 (英語フルネーム、例: 'Shohei Ohtani', 'Mike Trout', 'Seiya Suzuki')。"
                    "mlbid が判らない場合はこちらで指定する。backend 側で Jinja templated where 句に展開する。"
                ),
            },
            "season": {
                "type": "INTEGER",
                "description": "対象シーズン (例: 2026)。「今年」「今シーズン」は現在年、省略時もデフォルト現在年。",
            },
            "team": {
                "type": "STRING",
                "description": "チーム略称 (例: 'LAD', 'NYY')",
            },
            "group_by": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "集計次元 (任意)",
            },
            "where": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": (
                    "追加 WHERE 句 (MetricFlow Jinja 構文)。"
                    "例: [\"{{ Dimension('player__season_year') }} >= 2023\"]。"
                    "選手名フィルタは player_name 引数を使うこと (raw SQL 形式は禁止)。"
                ),
            },
            "order_by": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "ソート対象メトリクス名",
            },
            "limit": {
                "type": "INTEGER",
                "description": "取得行数上限 (デフォルト 20)",
            },
            "output_format": {
                "type": "STRING",
                "enum": ["sentence", "table"],
                "description": "'sentence' (文章) または 'table' (UI 表形式)",
            },
        },
        "required": ["metrics"],
    },
)

GLOSSARY_SEARCH_DECL = types.FunctionDeclaration(
    name="glossary_search_tool",
    description=(
        "MLB の用語定義・指標の意味を知識ベースから検索する。"
        "『xwOBA とは何か』『FIP と ERA の違いは』のような "
        "**定義・意味・解釈を問う質問にのみ**使用すること。"
        "特定の選手の成績値を取得する用途には使用しないこと"
        "（それは get_batter_stats_tool / get_pitcher_stats_tool の役割）。"
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "検索内容。ユーザーの質問をそのまま渡してよい",
            },
            "category": {
                "type": "STRING",
                # "rules" は精度不足のため一時除外（glossary_rag_service.EXCLUDED_CATEGORIES）
                "enum": ["batting", "pitching", "statcast"],
                "description": (
                    "打撃指標なら batting、投球指標なら pitching、"
                    "打球計測・トラッキング用語なら statcast。"
                    "競技ルール（反則・判定・進塁の規定など）なら rules。"
                    "判断がつかない場合は省略すること（全カテゴリ横断で検索される）"
                ),
            },
            "top_k": {
                "type": "INTEGER",
                "description": "取得件数 (デフォルト 5)",
            },
        },
        "required": ["query"],
    }
)


# USE_SEMANTIC_LAYER=false 時の標準ツール (legacy METRIC_MAP 経路)
CHAT_TOOL_DECLARATIONS = [
    GET_BATTER_STATS_DECL,
    GET_PITCHER_STATS_DECL,
    MATCHUP_HISTORY_DECL,
    MATCHUP_ANALYTICS_DECL,
]

# USE_SEMANTIC_LAYER=true 時のツール (Semantic Layer 経路)
# matchup 系は Semantic Layer 化未着手のため legacy のまま維持
CHAT_TOOL_DECLARATIONS_SEMANTIC = [
    QUERY_SEMANTIC_METRICS_DECL,
    MATCHUP_HISTORY_DECL,
    MATCHUP_ANALYTICS_DECL,
]