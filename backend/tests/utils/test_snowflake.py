"""
Unit tests for backend/app/utils/snowflake.py
"""
import threading
import pytest

from backend.app.utils.snowflake import (
    SnowflakeGenerator,
    decode,
    CUSTOM_EPOCH_MS,
    SEQUENCE_MASK,
    INSTANCE_MASK,
    REGION_MASK,
)


def test_generate_returns_positive_int_under_int64():
    gen = SnowflakeGenerator(region=1, instance=7)
    sf = gen.generate()
    assert sf > 0
    assert sf < (1 << 63)  # 符号付き int64 に収まる


def test_generate_is_strictly_monotonic():
    gen = SnowflakeGenerator(region=1, instance=7)
    prev = gen.generate()
    for _ in range(10_000):
        curr = gen.generate()
        assert curr > prev, f"not monotonic: {prev} -> {curr}"
        prev = curr


def test_no_collision_single_thread_100k():
    gen = SnowflakeGenerator(region=1, instance=7)
    ids = {gen.generate() for _ in range(100_000)}
    assert len(ids) == 100_000


def test_no_collision_8_threads_each_10k():
    gen = SnowflakeGenerator(region=1, instance=7)
    ids: set[int] = set()
    lock = threading.Lock()

    def worker():
        local = [gen.generate() for _ in range(10_000)]
        with lock:
            ids.update(local)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ids) == 8 * 10_000


def test_decode_recovers_fields():
    gen = SnowflakeGenerator(region=3, instance=42)
    sf = gen.generate()
    d = decode(sf)
    assert d.region == 3
    assert d.instance == 42
    assert 0 <= d.sequence <= SEQUENCE_MASK
    assert d.timestamp_ms >= CUSTOM_EPOCH_MS


def test_region_out_of_range_raises():
    with pytest.raises(ValueError):
        SnowflakeGenerator(region=REGION_MASK + 1, instance=0)


def test_instance_out_of_range_raises():
    with pytest.raises(ValueError):
        SnowflakeGenerator(region=0, instance=INSTANCE_MASK + 1)


def test_sequence_overflow_advances_ms():
    """同一 ms 内で 4096 個発行 → 次 ms に繰り越されることを確認。"""
    gen = SnowflakeGenerator(region=1, instance=1)
    ids = [gen.generate() for _ in range(SEQUENCE_MASK + 2)]
    assert len(set(ids)) == len(ids)
