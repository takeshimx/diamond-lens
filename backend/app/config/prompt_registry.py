"""
Prompt Registry - プロンプトのバージョン管理
プロンプトを外部ファイルから読み込み、バージョンを管理します。
新しいバージョンを作成する場合は、ファイルを `_v2.txt` として保存し、
ACTIVE_VERSIONS の対応するキーを更新してください。
"""

import os
from pathlib import Path
from typing import Dict, Optional, Literal

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# ===================================
# アクティブなプロンプトバージョン管理 (active / shadow)
# ===================================
# active: 本番でユーザーに返却される版
# shadow: シャドー評価で並走させる候補版（None の場合シャドー無効）
# ここを変更するだけでプロンプトのバージョンを切り替えられます
ACTIVE_VERSIONS: Dict[str, str] = {
    "parse_query": "v1",
    "generate_response": "v1",
    "routing": "v2",
    "strategy_planner": "v1",
    "strategy_synthesizer": "v1",
    "oracle_semantic": "v1",  # Phase 3: Semantic Layer 用 Oracle プロンプト（Phase 4で実利用）
    "chat_orchestrator_system": "v1",  # Phase 2.5: ChatOrchestrator のシステムプロンプト (インライン定義)
}

SHADOW_VERSIONS: Dict[str, Optional[str]] = {
    "parse_query": None,        # 例: "v2" を入れるとシャドー評価が走る
    "generate_response": None,
    "routing": "v2",   # active も v2 なので現状は同一プロンプト。テスト用に有効化
    "strategy_planner": None,
    "strategy_synthesizer": None,
    "oracle_semantic": None,
    "chat_orchestrator_system": None,
}

PromptRole = Literal["active", "shadow"]

def get_prompt(prompt_name: str, role: PromptRole = "active", **kwargs) -> str:
    """
    指定されたプロンプトの active / shadow バージョンを読み込み、変数を埋め込んで返す。
    Args:
        prompt_name: プロンプト名 ("parse_query", "routing" 等)
        role: "active"（本番でユーザーに返す版）または "shadow"（評価用の候補版）。
              省略時は "active" のため、既存の呼び出しは互換が保たれます。
        **kwargs: プロンプト内のプレースホルダーに埋め込む値
        例: query="大谷のHR数は？", season=2024
        というように、「名前付きで渡された引数を、全部まとめて1つの辞書(dict)にして受け取る」という意味
    Returns:
        変数が埋め込まれたプロンプト文字列
    Usage:
        prompt = get_prompt("parse_query", query="大谷のHR数は？", season=2024)
        shadow_prompt = get_prompt("parse_query", role="shadow", query="大谷のHR数は？")
    """
    if role == "active":
        version = ACTIVE_VERSIONS.get(prompt_name)
    elif role == "shadow":
        version = SHADOW_VERSIONS.get(prompt_name)
    else:
        raise ValueError(f"Invalid role: {role}. Must be 'active' or 'shadow'.")

    if not version:
        raise ValueError(
            f"No {role} version configured for prompt: {prompt_name}"
        )

    file_path = PROMPTS_DIR / f"{prompt_name}_{version}.txt"

    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    template = file_path.read_text(encoding="utf-8")

    # JSON の波括弧を壊さないよう、明示的にプレースホルダーのみ置換
    for key, value in kwargs.items():
        template = template.replace(f"{{{key}}}", str(value))

    return template


def get_prompt_version(prompt_name: str, role: PromptRole = "active") -> Optional[str]:
    """
    指定された role の現在のバージョンを返す。

    Args:
        prompt_name: プロンプト名
        role: "active" または "shadow"

    Returns:
        バージョン文字列。未設定の場合は None。
    """
    if role == "active":
        return ACTIVE_VERSIONS.get(prompt_name)
    return SHADOW_VERSIONS.get(prompt_name)


def has_shadow(prompt_name: str) -> bool:
    """
    このプロンプトでシャドー評価が有効か判定する。

    Args:
        prompt_name: プロンプト名

    Returns:
        SHADOW_VERSIONS に非 None の値が設定されていれば True。
    """
    return SHADOW_VERSIONS.get(prompt_name) is not None


def get_all_versions() -> Dict[str, Dict[str, Optional[str]]]:
    """
    全プロンプトの active / shadow バージョンを返す。

    Returns:
        例: {"parse_query": {"active": "v1", "shadow": "v2"}, ...}
    """
    return {
        name: {
            "active": ACTIVE_VERSIONS.get(name),
            "shadow": SHADOW_VERSIONS.get(name),
        }
        for name in ACTIVE_VERSIONS.keys()
    }