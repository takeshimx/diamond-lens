"""
Prompt Registry - プロンプトのバージョン管理
プロンプトを外部ファイルから読み込み、バージョンを管理します。
新しいバージョンを作成する場合は、ファイルを `_v2.txt` として保存し、
ACTIVE_VERSIONS の対応するキーを更新してください。
"""

import os
from pathlib import Path
from typing import Dict

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# ===================================
# アクティブなプロンプトバージョン管理
# ===================================
# ここを変更するだけでプロンプトのバージョンを切り替えられます
ACTIVE_VERSIONS: Dict[str, str] = {
    "parse_query": "v1",
    "generate_response": "v1",
    "routing": "v1",
}

def get_prompt(prompt_name: str, **kwargs) -> str:
    """
    指定されたプロンプトの現在のアクティブバージョンを読み込み、変数を埋め込んで返す。
    Args:
        prompt_name: プロンプト名 ("parse_query", "routing" 等)
        **kwargs: プロンプト内のプレースホルダーに埋め込む値
        例: query="大谷のHR数は？", season=2024
        というように、「名前付きで渡された引数を、全部まとめて1つの辞書(dict)にして受け取る」という意味
    Returns:
        変数が埋め込まれたプロンプト文字列
    Usage:
        prompt = get_prompt("parse_query", query="大谷のHR数は？", season=2024)
    """
    version = ACTIVE_VERSIONS.get(prompt_name)
    if not version:
        raise ValueError(f"Unknow prompt name: {prompt_name}")
    
    file_path = PROMPTS_DIR / f"{prompt_name}_{version}.txt"

    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    template = file_path.read_text(encoding="utf-8")

    # JSON の波括弧を壊さないよう、明示的にプレースホルダーのみ置換
    for key, value in kwargs.items():
        template = template.replace(f"{{{key}}}", str(value))
    
    return template

def get_prompt_version(prompt_name: str) -> str:
    """現在のアクティブバージョンを返す"""
    return ACTIVE_VERSIONS.get(prompt_name, "unknown")


def get_all_versions() -> Dict[str, str]:
    """全プロンプトの現在のアクティブバージョンを返す"""
    return ACTIVE_VERSIONS.copy()