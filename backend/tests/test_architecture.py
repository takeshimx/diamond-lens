# backend/tests/test_architecture.py
"""
アーキテクチャ適合テスト（fitness functions）

ADR で決めた「構造上の不変条件」を、ソースコードの静的解析で検証する。
実行時の振る舞いではなく「どのモジュールが何に依存してよいか」が対象。

  ADR-011: langgraph を import してよいのは strategy_agent.py のみ

方式はいずれも許可リスト（allowlist）。現状を基準として固定し、
新しく増えたものだけを落とす。現状値ごと赤にすると、削除判断が
下りるまで直せず、恒常的に赤いゲートは無視されるようになるため。

grep ではなく ast を使う理由は _top_level_imports() の docstring を参照。
"""

import ast
from pathlib import Path

# このファイルは backend/tests/ にあるので、parents[1] が backend/
APP_DIR = Path(__file__).resolve().parents[1] / "app"
TOOLS_DIR = APP_DIR / "services" / "tools"


# ============================================================
# 共通ヘルパー
# ============================================================

def _python_files(root: Path) -> list[Path]:
    """root 配下の .py を再帰的に返す（__pycache__ は除外）。"""
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _rel(path: Path) -> str:
    """app/ からの相対パスを POSIX 形式で返す。

    as_posix() を挟むのは、Windows の `\\` と CI (Linux) の `/` で
    許可リストの文字列が一致しなくなるのを防ぐため。
    """
    return path.relative_to(APP_DIR).as_posix()


def _top_level_imports(path: Path) -> set[str]:
    """ファイルが import しているトップレベルモジュール名を集める。

    ast を使う理由は、関数内 import を取りこぼさないため。
    `def f(): from langgraph.graph import StateGraph` のような書き方は
    行頭を固定した grep では検出できない（実際 strategy_report_endpoints.py
    に関数内 import が 7 箇所ある）。ast.walk は入れ子を含む全ノードを辿る。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import langgraph.graph  ->  "langgraph"
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # from langgraph.graph import StateGraph  ->  "langgraph"
            # level > 0 は相対 import（from .foo import bar）なので対象外
            if node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
    return modules


# ============================================================
# ADR-011: langgraph の依存範囲
# ============================================================

LANGGRAPH_ALLOWLIST = {
    # ADR-011 が残すと決めた唯一の経路
    "services/agents/strategy_agent.py",
    # --- 以下は Phase 2-G の物理削除待ち（ADR-010 / 011 Consequences）---
    # 削除する際は、この行も一緒に消すこと。
    "services/agents/batter_agents.py",
    "services/agents/pitcher_agents.py",
    "services/agents/matchup_agent.py",
    "services/ai_agent_service.py",
}


def _langgraph_importers() -> set[str]:
    """app/ 配下で langgraph を import しているファイルの相対パス集合。"""
    return {
        _rel(p) for p in _python_files(APP_DIR)
        if "langgraph" in _top_level_imports(p)
    }


def test_langgraph_imports_do_not_spread():
    """ADR-011: langgraph の import 元が許可リストを超えて増えていない。"""
    unexpected = _langgraph_importers() - LANGGRAPH_ALLOWLIST
    assert not unexpected, (
        f"langgraph を新たに import したファイル: {sorted(unexpected)}\n"
        "ADR-011 により langgraph は strategy_agent.py に限定される。"
        "新しい経路が必要な場合は ADR-011 を supersede すること。"
    )


def test_langgraph_allowlist_has_no_stale_entries():
    """許可リストに、もう langgraph を使っていないファイルが残っていない。

    レガシー sub-agent を削除したとき、このテストが許可リストの掃除を促す。
    許可リストが実態より緩いまま放置されると、ゲートは徐々に意味を失う。
    """
    stale = LANGGRAPH_ALLOWLIST - _langgraph_importers()
    assert not stale, (
        f"許可リストに不要な項目が残っている: {sorted(stale)}\n"
        "該当ファイルは langgraph を使っていない。許可リストから削除すること。"
    )


# ============================================================
# ADR-013: Gemini SDK の呼び出し箇所
# ============================================================

GEMINI_CALL_ALLOWLIST = {
    # 正規の窓口。ここを通れば必ず llm_interaction_logs に 1 行残る。
    "services/llm_gateway_service.py",
    # ADR-010 / 013 に記録済みの唯一の例外。LangChain のコールバックが
    # 使えないため SDK を直接呼び、自前で LLMLogEntry を書く。
    # 書き込み先テーブルは同一であり、記録の欠落はない。
    "services/chat_orchestrator.py",
}


def _calls_gemini_sdk(path: Path) -> bool:
    """genai.Client(...) または *.generate_content(...) の呼び出しがあるか。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        # genai.Client(...) — レシーバ名まで見る。属性名だけで判定すると
        # bigquery.Client(...) や storage.Client(...) を巻き込むため。
        if (
            node.func.attr == "Client"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "genai"
        ):
            return True
        # client.models.generate_content(...) — レシーバの形が一定しないため
        # メソッド名のみで判定する。この名前は Gemini SDK 固有で誤検出は起きない。
        if node.func.attr == "generate_content":
            return True
    return False


def _gemini_callers() -> set[str]:
    """app/ 配下で Gemini SDK を直接呼んでいるファイルの相対パス集合。"""
    return {_rel(p) for p in _python_files(APP_DIR) if _calls_gemini_sdk(p)}


def test_gemini_sdk_calls_stay_behind_the_gateway():
    """ADR-013: Gemini を直接呼ぶのは Gateway と記録済み例外のみ。

    窓口を迂回した呼び出しは、課金が発生するのにログが残らない。
    動かして気付ける類の欠陥ではないため、静的に止める。
    """
    unexpected = _gemini_callers() - GEMINI_CALL_ALLOWLIST
    assert not unexpected, (
        f"Gateway を経由せず Gemini を呼んでいるファイル: {sorted(unexpected)}\n"
        "ADR-013 により LLM 呼び出しは llm_gateway_service を通すこと。"
        "例外を増やす場合は ADR-013 に記録したうえで許可リストへ追加する。"
    )


def test_gemini_call_allowlist_has_no_stale_entries():
    """許可リストに、もう Gemini を直接呼んでいないファイルが残っていない。"""
    stale = GEMINI_CALL_ALLOWLIST - _gemini_callers()
    assert not stale, (
        f"許可リストに不要な項目が残っている: {sorted(stale)}\n"
        "該当ファイルは Gemini を直接呼んでいない。許可リストから削除すること。"
    )


# ============================================================
# ADR-050: ツールは生データを返し、応答文を書かない
# ============================================================

def _calls_llm_gateway(path: Path) -> bool:
    """call_gemini(...) の呼び出しがあるか（Gateway 経由の LLM 呼び出し）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "call_gemini":
            return True
    return False


def test_tools_never_call_an_llm():
    """ADR-050: tools/ 配下はデータ取得に徹し、LLM を呼ばない。

    ツール内で応答文を生成すると、1 質問で LLM が二重に走り、
    ADR-010 で解消した伝言ゲームが復活する。

    検出できるのは直接呼び出しのみである点に注意。glossary_search_tool は
    呼び出し先の rerank_service が Gemini を使うが、ツール自身が応答文を
    書いているわけではないため ADR-050 の違反ではない。
    """
    offenders = sorted(
        _rel(p) for p in _python_files(TOOLS_DIR)
        if _calls_gemini_sdk(p) or _calls_llm_gateway(p)
    )
    assert not offenders, (
        f"tools/ 配下で LLM を呼んでいるファイル: {offenders}\n"
        "ADR-050 によりツールは生データを返し、応答の組み立ては "
        "Orchestrator の LLM が担う。"
    )


def _default_of(func_node: ast.FunctionDef | ast.AsyncFunctionDef, name: str):
    """関数定義から引数 name の既定値ノードを返す（無ければ None）。"""
    a = func_node.args
    # 位置引数: defaults は引数リストの末尾から対応する
    if a.defaults:
        for arg, default in zip(a.args[len(a.args) - len(a.defaults):], a.defaults):
            if arg.arg == name:
                return default
    # キーワード専用引数: kw_defaults は 1 対 1 対応、既定値なしは None
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        if arg.arg == name and default is not None:
            return default
    return None


def test_tool_output_format_defaults_to_data():
    """ADR-050: output_format の既定値が 'data' のままである。

    この ADR で最も壊れやすいのは LLM 呼び出しの追加ではなく、既定値が
    非推奨の 'sentence'（ツール内 LLM が応答文を書く旧モード）へ
    差し替えられること。ツール内に LLM 呼び出しは現れないため、
    test_tools_never_call_an_llm では捕捉できない。
    """
    checked: list[str] = []
    for path in _python_files(TOOLS_DIR):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            default = _default_of(node, "output_format")
            if default is None:
                continue
            where = f"{_rel(path)}::{node.name}"
            checked.append(where)
            assert isinstance(default, ast.Constant) and default.value == "data", (
                f"{where} の output_format 既定値が 'data' ではない: "
                f"{ast.dump(default)}\n"
                "ADR-050 によりツールの既定出力は生データである。"
            )

    assert checked, (
        "output_format 引数を持つツール関数が 1 つも見つからなかった。"
        "引数名の変更かディレクトリ構成の変更が疑われる。"
    )
