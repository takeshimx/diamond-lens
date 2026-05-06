"""
Phase 3-4 propagation tests: trace_id flows from ContextVar into
LLMLogEntry.to_dict(), ShadowComparisonEntry.to_dict(),
StructuredLogger JSON, and format_sse() payloads.
"""
import json

from backend.app.middleware.request_context import set_trace_id
from backend.app.utils.snowflake import generate_id_str


def test_llm_log_entry_picks_trace_id_from_contextvar():
    from backend.app.services.llm_logger_service import LLMLogEntry

    sf = generate_id_str()
    set_trace_id(sf)

    entry = LLMLogEntry()
    d = entry.to_dict()

    assert d.get("trace_id") == sf
    assert isinstance(d["trace_id"], str)


def test_llm_log_entry_explicit_override_wins():
    from backend.app.services.llm_logger_service import LLMLogEntry

    set_trace_id(generate_id_str())

    entry = LLMLogEntry()
    override = "111111111111111111"
    entry.trace_id = override
    d = entry.to_dict()

    assert d["trace_id"] == override


def test_shadow_entry_picks_trace_id_from_contextvar():
    from backend.app.services.shadow_logger_service import ShadowComparisonEntry

    sf = generate_id_str()
    set_trace_id(sf)

    entry = ShadowComparisonEntry()
    d = entry.to_dict()

    assert d.get("trace_id") == sf


def test_format_sse_auto_attaches_trace_id():
    from backend.app.utils.streaming import format_sse

    sf = generate_id_str()
    set_trace_id(sf)

    raw = format_sse({"type": "token", "content": "hello"}, event="token")
    # SSE 形式: "event: ...\ndata: {...}\n\n"
    payload_line = [l for l in raw.split("\n") if l.startswith("data: ")][0]
    payload = json.loads(payload_line[len("data: "):])

    assert payload["trace_id"] == sf
    assert payload["content"] == "hello"


def test_format_sse_does_not_overwrite_existing_trace_id():
    from backend.app.utils.streaming import format_sse

    set_trace_id(generate_id_str())  # この値を上書きしないことを確認

    raw = format_sse(
        {"type": "token", "content": "hello", "trace_id": "preset-123"},
        event="token",
    )
    payload_line = [l for l in raw.split("\n") if l.startswith("data: ")][0]
    payload = json.loads(payload_line[len("data: "):])

    assert payload["trace_id"] == "preset-123"


def test_structured_logger_emits_trace_id(capsys):
    from backend.app.utils.structured_logger import StructuredLogger

    sf = generate_id_str()
    set_trace_id(sf)

    log = StructuredLogger("test-trace-id")
    log.info("hello")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    record = json.loads(out)
    assert record["trace_id"] == sf
    assert record["message"] == "hello"
