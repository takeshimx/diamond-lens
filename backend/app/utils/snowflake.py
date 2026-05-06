"""
Snowflake-style 64-bit Trace ID generator.

Layout (MSB → LSB):
  sign(1) | timestamp_ms(41) | region(4) | instance(6) | sequence(12)
"""
import os
import time
import hashlib
import threading
from typing import NamedTuple, Optional

# ──────────────────────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────────────────────

# カスタムエポック: 2026-01-01T00:00:00Z (UTC)
# datetime(2026,1,1,tzinfo=timezone.utc).timestamp() * 1000
CUSTOM_EPOCH_MS = 1767225600000

# 各フィールドのビット幅
TIMESTAMP_BITS = 41
REGION_BITS = 4
INSTANCE_BITS = 6
SEQUENCE_BITS = 12

# 各フィールドのシフト量（LSB からの位置）
SEQUENCE_SHIFT = 0
INSTANCE_SHIFT = SEQUENCE_BITS                                   # 12
REGION_SHIFT = SEQUENCE_BITS + INSTANCE_BITS                     # 18
TIMESTAMP_SHIFT = SEQUENCE_BITS + INSTANCE_BITS + REGION_BITS    # 22

# 各フィールドのマスク（n bit ぶんすべて 1）
SEQUENCE_MASK = (1 << SEQUENCE_BITS) - 1   # 0xFFF (4095)
INSTANCE_MASK = (1 << INSTANCE_BITS) - 1   # 0x3F  (63)
REGION_MASK = (1 << REGION_BITS) - 1       # 0xF   (15)
TIMESTAMP_MASK = (1 << TIMESTAMP_BITS) - 1

# GCP リージョンの番号マッピング（4bit に収まる範囲）
REGION_MAP = {
    "asia-northeast1": 1,
    "us-central1": 2,
    "europe-west1": 3,
    "asia-southeast1": 4,
}


class DecodedSnowflake(NamedTuple):
    """decode() の戻り値"""
    timestamp_ms: int
    region: int
    instance: int
    sequence: int


# ──────────────────────────────────────────────────────────────
# Generator
# ──────────────────────────────────────────────────────────────

class SnowflakeGenerator:
    """スレッドセーフな Snowflake ID 発行器。"""

    def __init__(self, region: int, instance: int):
        if not 0 <= region <= REGION_MASK:
            raise ValueError(f"region must be 0..{REGION_MASK}, got {region}")
        if not 0 <= instance <= INSTANCE_MASK:
            raise ValueError(f"instance must be 0..{INSTANCE_MASK}, got {instance}")
        self.region = region
        self.instance = instance
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def generate(self) -> int:
        with self._lock:
            now = self._current_ms()

            # クロック後退検知: NTP 補正等で時計が戻ったら、追いつくまで待機
            if now < self._last_timestamp:
                while now < self._last_timestamp:
                    time.sleep(0.001)
                    now = self._current_ms()

            if now == self._last_timestamp:
                # 同一 ms 内: シーケンスをインクリメント
                self._sequence = (self._sequence + 1) & SEQUENCE_MASK
                if self._sequence == 0:
                    # 4096 個使い切ったので次の ms までスピンウェイト
                    while now <= self._last_timestamp:
                        now = self._current_ms()
            else:
                # 新しい ms: シーケンスを 0 にリセット
                self._sequence = 0

            self._last_timestamp = now
            elapsed = now - CUSTOM_EPOCH_MS

            return (
                (elapsed << TIMESTAMP_SHIFT)
                | (self.region << REGION_SHIFT)
                | (self.instance << INSTANCE_SHIFT)
                | self._sequence
            )

    @staticmethod
    def _current_ms() -> int:
        return int(time.time() * 1000)


# ──────────────────────────────────────────────────────────────
# decoder（デバッグ・運用用）
# ──────────────────────────────────────────────────────────────

def decode(snowflake_id: int) -> DecodedSnowflake:
    """ID を 4 つのフィールドに分解する。BQ クエリでも同等のロジックを再現可能。"""
    sequence = snowflake_id & SEQUENCE_MASK
    instance = (snowflake_id >> INSTANCE_SHIFT) & INSTANCE_MASK
    region = (snowflake_id >> REGION_SHIFT) & REGION_MASK
    timestamp = ((snowflake_id >> TIMESTAMP_SHIFT) & TIMESTAMP_MASK) + CUSTOM_EPOCH_MS
    return DecodedSnowflake(timestamp, region, instance, sequence)


# ──────────────────────────────────────────────────────────────
# プロセス全体で共有するシングルトン
# ──────────────────────────────────────────────────────────────

_generator: Optional[SnowflakeGenerator] = None
_generator_lock = threading.Lock()


def _resolve_region() -> int:
    """環境変数 GCP_REGION から region 番号を解決。未マップは 0。"""
    name = os.getenv("GCP_REGION", "asia-northeast1")
    return REGION_MAP.get(name, 0)


def _resolve_instance() -> int:
    """Cloud Run の K_REVISION（or hostname）の SHA-256 下位 6bit。"""
    revision = os.getenv("K_REVISION") or os.getenv("HOSTNAME") or "local"
    digest = hashlib.sha256(revision.encode()).digest()
    return digest[-1] & INSTANCE_MASK


def get_generator() -> SnowflakeGenerator:
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                _generator = SnowflakeGenerator(
                    region=_resolve_region(),
                    instance=_resolve_instance(),
                )
    return _generator


def generate_id() -> int:
    """64bit 整数の Snowflake ID を発行する。"""
    return get_generator().generate()


def generate_id_str() -> str:
    """JS 53bit 精度問題を避けるため、外に出すときの文字列形式。"""
    return str(generate_id())
