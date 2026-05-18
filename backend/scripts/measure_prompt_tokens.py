"""
Step 1-1: 候補プロンプトのトークン数を計測し、Context Caching 適用可否を判定する。
Run: python -m backend.scripts.measure_prompt_tokens
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# .env ロード（他スクリプトと同じパターン）
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY_V2"))
MODEL = "gemini-2.5-flash"
MIN_CACHE_TOKENS = 1024  # Gemini 2.5 Flash の最小要件

# 候補 1: ChatOrchestrator のインライン system prompt
from backend.app.services.chat_orchestrator import (
    _build_system_prompt_legacy,
    _build_system_prompt_semantic,
)

candidates = {
    "chat_orchestrator_system_legacy": _build_system_prompt_legacy(),
    "chat_orchestrator_system_semantic": _build_system_prompt_semantic(),
}

# 候補 2: prompts/ 配下のファイル
prompts_dir = Path(__file__).parent.parent / "app" / "prompts"
for txt_path in sorted(prompts_dir.glob("*.txt")):
    candidates[txt_path.stem] = txt_path.read_text(encoding="utf-8")

# 計測
print(f"{'prompt_name':<45} {'tokens':>8}  cacheable?")
print("-" * 72)
for name, content in candidates.items():
    resp = client.models.count_tokens(model=MODEL, contents=content)
    n = resp.total_tokens
    flag = "✅ YES" if n >= MIN_CACHE_TOKENS else f"❌ NO (< {MIN_CACHE_TOKENS})"
    print(f"{name:<45} {n:>8}  {flag}")
