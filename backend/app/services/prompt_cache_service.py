"""
Prompt Cache Service
Gemini Context Caching の lifecycle 管理。
固定プレフィックスを `client.caches.create()` で登録し、
generate_content 時に `cached_content` として参照することで、
input トークンの再計算課金を ~1/10 に削減する。

設計:
- in-memory dict (prompt_name, version, content_hash) → cache name
- TTL 切れ近接時は再作成
- 失敗時 None を返し caller が非キャッシュ経路にフォールバック
"""
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from google.genai import types

from backend.app.services.llm_gateway_service import get_genai_client

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600
MIN_REMAINING_SECONDS = 300  # 残り 5 分を切ったら再作成


@dataclass
class _CacheEntry:
    name: str
    created_at: float
    ttl_seconds: int


_registry: Dict[str, _CacheEntry] = {}
_lock = threading.Lock()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_or_create_cache(
    *,
    prompt_name: str,
    prompt_version: Optional[str],
    prefix_text: str,
    model: str = "gemini-2.5-flash",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    as_system_instruction: bool = False,
) -> Optional[str]:
    """プレフィックスに対応する CachedContent name を返す。失敗時 None。

    Args:
        as_system_instruction: True なら system_instruction として登録 (oracle_semantic 等の
                               system prompt 用途)。False (デフォルト) なら user contents として登録
                               (parse_query 等のインライン prompt 用途)。
    """
    mode_tag = "sys" if as_system_instruction else "usr"
    key = f"{prompt_name}|{prompt_version or 'none'}|{model}|{mode_tag}|{_hash(prefix_text)}"

    with _lock:
        entry = _registry.get(key)
        if entry is not None:
            elapsed = time.time() - entry.created_at
            if elapsed < entry.ttl_seconds - MIN_REMAINING_SECONDS:
                return entry.name

        try:
            client = get_genai_client()
            config_kwargs = {
                "display_name": f"{prompt_name}_{prompt_version or 'unknown'}",
                "ttl": f"{ttl_seconds}s",
            }
            if as_system_instruction:
                config_kwargs["system_instruction"] = prefix_text
            else:
                config_kwargs["contents"] = [types.Content(
                    role="user",
                    parts=[types.Part(text=prefix_text)],
                )]
            cache = client.caches.create(
                model=model,
                config=types.CreateCachedContentConfig(**config_kwargs),
            )
            _registry[key] = _CacheEntry(
                name=cache.name,
                created_at=time.time(),
                ttl_seconds=ttl_seconds,
            )
            logger.info(
                f"Created cache {cache.name} for {prompt_name}_{prompt_version} (mode={mode_tag})"
            )
            return cache.name
        except Exception as e:
            logger.warning(
                f"Cache creation failed for {prompt_name}_{prompt_version}: {e}. "
                f"Will fall back to non-cached path."
            )
            return None